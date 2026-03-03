"""Coverage-based filtering for assembled contigs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
import subprocess

from nevelib._common.fasta import iter_fasta_records, validate_fasta, write_fasta
from nevelib._common.fastq import validate_fastq
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class CoverageFilterConfig:
    """Configuration for coverage-based contig filtering.

    Attributes:
        samtools_exec: samtools binary.
        minimap2_exec: minimap2 binary.
        mosdepth_exec: mosdepth binary.
        threads: Number of threads.
        min_mean_coverage: Minimum mean coverage to retain a contig.
        minimap2_preset: minimap2 preset for read-to-contig mapping.
        mosdepth_window: mosdepth window size (0 = per-base summary).
    """

    samtools_exec: str = "samtools"
    minimap2_exec: str = "minimap2"
    mosdepth_exec: str = "mosdepth"
    threads: int = 8
    min_mean_coverage: float = 5.0
    minimap2_preset: str = "sr"
    mosdepth_window: int = 0


@dataclass
class CoverageFilterResult:
    """Result of coverage filtering.

    Attributes:
        output_fasta: Path to filtered FASTA.
        n_input: Number of input contigs.
        n_passing: Number of contigs passing filter.
        n_removed: Number of contigs removed.
        coverage_tsv: Path to per-contig coverage TSV.
    """

    output_fasta: Path
    n_input: int = 0
    n_passing: int = 0
    n_removed: int = 0
    coverage_tsv: Path | None = None


def _validate_fastq_input(path: Path, label: str, *, min_reads: int = 1) -> None:
    """Validate a FASTQ input path."""
    result = validate_fastq(path, check_gzip=True, check_nonempty=True, min_reads=min_reads)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTQ: " + "; ".join(result.errors))


def _validate_contig_fasta(path: Path) -> None:
    """Validate contig FASTA input path."""
    result = validate_fasta(path, check_nonempty=True, min_records=1)
    if not result.valid:
        raise ValueError("Invalid contig FASTA: " + "; ".join(result.errors))


def _extract_stderr(exc: subprocess.CalledProcessError) -> str:
    """Extract stderr text from CalledProcessError."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return (stderr or "").strip()


def _parse_mosdepth_summary(summary_path: Path) -> dict[str, tuple[int, int, float]]:
    """Parse mosdepth summary table into contig coverage statistics."""
    if not summary_path.exists():
        raise RuntimeError(f"mosdepth summary file not found: {summary_path}")

    parsed: dict[str, tuple[int, int, float]] = {}
    with summary_path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 4:
                continue
            contig = parts[0]
            if contig.lower() == "total":
                continue
            try:
                length = int(float(parts[1]))
                bases = int(float(parts[2]))
                mean = float(parts[3])
            except ValueError:
                continue
            parsed[contig] = (length, bases, mean)
    return parsed


def _run_mapping_pipeline(
    contigs: Path,
    r1: Path,
    r2: Path,
    singleton: Path | None,
    workdir: Path,
    cfg: CoverageFilterConfig,
    *,
    out_log: Path | None,
    err_log: Path | None,
) -> Path:
    """Map reads to contigs and return sorted BAM path."""
    threads = str(max(1, int(cfg.threads)))
    paired_bam = workdir / "coverage.paired.sorted.bam"
    single_bam = workdir / "coverage.singleton.sorted.bam"
    merged_bam = workdir / "coverage.sorted.bam"

    cmd_pairs = (
        f"{shlex.join([cfg.minimap2_exec, '-a', '-x', cfg.minimap2_preset, '-t', threads, str(contigs), str(r1), str(r2)])} "
        f"| {shlex.join([cfg.samtools_exec, 'sort', '-@', threads, '-o', str(paired_bam), '-'])}"
    )
    run_tool(cmd_pairs, out_log=out_log, err_log=err_log, check=True)

    use_singletons = False
    if singleton is not None and singleton.exists():
        singleton_check = validate_fastq(
            singleton,
            check_gzip=True,
            check_nonempty=False,
            min_reads=0,
        )
        use_singletons = bool(singleton_check.read_count)

    if use_singletons and singleton is not None:
        cmd_single = (
            f"{shlex.join([cfg.minimap2_exec, '-a', '-x', cfg.minimap2_preset, '-t', threads, str(contigs), str(singleton)])} "
            f"| {shlex.join([cfg.samtools_exec, 'sort', '-@', threads, '-o', str(single_bam), '-'])}"
        )
        run_tool(cmd_single, out_log=out_log, err_log=err_log, check=True)

        run_tool(
            [
                cfg.samtools_exec,
                "merge",
                "-f",
                "-@",
                threads,
                str(merged_bam),
                str(paired_bam),
                str(single_bam),
            ],
            out_log=out_log,
            err_log=err_log,
            check=True,
        )
    else:
        merged_bam = paired_bam

    run_tool(
        [cfg.samtools_exec, "index", str(merged_bam)],
        out_log=out_log,
        err_log=err_log,
        check=True,
    )

    return merged_bam


def filter_by_coverage(
    contigs: Path,
    r1: Path,
    r2: Path,
    singleton: Path | None,
    output_fasta: Path,
    workdir: Path,
    cfg: CoverageFilterConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> CoverageFilterResult:
    """Filter contigs by mean read depth computed with mosdepth.

    Args:
        contigs: Input contig FASTA.
        r1: Read-1 FASTQ used for remapping.
        r2: Read-2 FASTQ used for remapping.
        singleton: Optional singleton FASTQ.
        output_fasta: Destination FASTA for passing contigs.
        workdir: Working directory for intermediate files.
        cfg: Coverage filter configuration.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        CoverageFilterResult summary.

    Raises:
        ValueError: If inputs are invalid.
        RuntimeError: If required tools are unavailable or commands fail.
    """
    _validate_contig_fasta(contigs)
    _validate_fastq_input(r1, "r1")
    _validate_fastq_input(r2, "r2")

    for name, exec_name in (
        ("minimap2", cfg.minimap2_exec),
        ("samtools", cfg.samtools_exec),
        ("mosdepth", cfg.mosdepth_exec),
    ):
        info = check_tool(exec_name)
        if not info.available:
            raise RuntimeError(f"{name} executable not available: {exec_name}")

    workdir.mkdir(parents=True, exist_ok=True)
    output_fasta.parent.mkdir(parents=True, exist_ok=True)

    try:
        sorted_bam = _run_mapping_pipeline(
            contigs,
            r1,
            r2,
            singleton,
            workdir,
            cfg,
            out_log=out_log,
            err_log=err_log,
        )

        prefix = workdir / "coverage"
        mosdepth_cmd: list[str] = [
            cfg.mosdepth_exec,
            "--threads",
            str(max(1, int(cfg.threads))),
        ]
        if int(cfg.mosdepth_window) > 0:
            mosdepth_cmd.extend(["--by", str(int(cfg.mosdepth_window))])
        else:
            mosdepth_cmd.append("--no-per-base")
        mosdepth_cmd.extend([str(prefix), str(sorted_bam)])

        run_tool(mosdepth_cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        detail = _extract_stderr(exc)
        msg = f"Coverage filtering command failed with exit code {exc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg) from exc

    summary_path = Path(f"{prefix}.mosdepth.summary.txt")
    coverage = _parse_mosdepth_summary(summary_path)

    all_records = list(iter_fasta_records(contigs))
    passing_records = [
        (rec_id, seq)
        for rec_id, seq in all_records
        if coverage.get(rec_id, (0, 0, 0.0))[2] >= float(cfg.min_mean_coverage)
    ]

    write_fasta(iter(passing_records), output_fasta)

    coverage_tsv = workdir / "contig_mean_coverage.tsv"
    with coverage_tsv.open("w", encoding="utf-8") as handle:
        handle.write("contig_id\tlength\tbases\tmean_coverage\tpass\n")
        for rec_id, _ in all_records:
            length, bases, mean_cov = coverage.get(rec_id, (0, 0, 0.0))
            passed = mean_cov >= float(cfg.min_mean_coverage)
            handle.write(
                f"{rec_id}\t{length}\t{bases}\t{mean_cov:.6f}\t{str(passed).lower()}\n"
            )

    n_input = len(all_records)
    n_passing = len(passing_records)

    return CoverageFilterResult(
        output_fasta=output_fasta,
        n_input=n_input,
        n_passing=n_passing,
        n_removed=n_input - n_passing,
        coverage_tsv=coverage_tsv,
    )
