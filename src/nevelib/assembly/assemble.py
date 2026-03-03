"""SPAdes-based de novo assembly helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from nevelib._common.fasta import iter_fasta_records
from nevelib._common.fastq import validate_fastq
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class AssemblyConfig:
    """Configuration for de novo assembly via SPAdes.

    Attributes:
        spades_exec: Name or path of the spades.py binary.
        kmers: List of k-mer sizes for assembly.
        threads: Number of threads.
        memory: Memory limit in GB.
        careful: Enable SPAdes careful mode (mismatch correction).
        only_assembler: Skip error correction step.
        extra_args: Additional SPAdes CLI arguments.
    """

    spades_exec: str = "spades.py"
    kmers: list[int] | None = None
    threads: int = 8
    memory: int = 16
    careful: bool = True
    only_assembler: bool = False
    extra_args: list[str] | None = None


@dataclass
class AssemblyResult:
    """Result of de novo assembly.

    Attributes:
        contigs: Path to assembled contigs FASTA.
        scaffolds: Path to assembled scaffolds FASTA (may be same as contigs).
        output_dir: SPAdes output directory.
        n_contigs: Number of contigs produced.
        n_scaffolds: Number of scaffolds produced.
    """

    contigs: Path
    scaffolds: Path
    output_dir: Path
    n_contigs: int = 0
    n_scaffolds: int = 0


def _validate_fastq_input(path: Path, label: str, *, min_reads: int = 1) -> None:
    """Validate a FASTQ input and raise on invalid content."""
    result = validate_fastq(path, check_gzip=True, check_nonempty=True, min_reads=min_reads)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTQ: " + "; ".join(result.errors))


def _count_fasta_records(path: Path) -> int:
    """Count FASTA records using the common FASTA iterator."""
    if not path.exists():
        return 0
    return sum(1 for _ in iter_fasta_records(path))


def _extract_stderr(exc: subprocess.CalledProcessError) -> str:
    """Extract stderr text from CalledProcessError."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return (stderr or "").strip()


def _resolve_primary_assembly(contigs: Path, scaffolds: Path) -> Path:
    """Resolve canonical assembly output, preferring scaffolds then contigs."""
    scaffold_ok = scaffolds.exists() and scaffolds.stat().st_size > 0
    contig_ok = contigs.exists() and contigs.stat().st_size > 0

    if scaffold_ok:
        return scaffolds
    if contig_ok:
        shutil.copyfile(contigs, scaffolds)
        return scaffolds

    raise RuntimeError(
        "SPAdes did not produce a non-empty assembly output "
        f"({contigs} / {scaffolds})."
    )


def assemble_reads(
    r1: Path,
    r2: Path,
    singleton: Path | None,
    output_dir: Path,
    cfg: AssemblyConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> AssemblyResult:
    """Run SPAdes de novo assembly from paired FASTQ inputs.

    Args:
        r1: Input read-1 FASTQ path.
        r2: Input read-2 FASTQ path.
        singleton: Optional singleton FASTQ path.
        output_dir: SPAdes output directory.
        cfg: Assembly runtime configuration.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        AssemblyResult with output paths and sequence counts.

    Raises:
        ValueError: If FASTQ input validation fails.
        RuntimeError: If SPAdes is unavailable, fails, or produces no output.
    """
    _validate_fastq_input(r1, "r1")
    _validate_fastq_input(r2, "r2")

    if singleton is not None and singleton.exists():
        singleton_result = validate_fastq(
            singleton,
            check_gzip=True,
            check_nonempty=False,
            min_reads=0,
        )
        if not singleton_result.valid:
            raise ValueError("Invalid singleton FASTQ: " + "; ".join(singleton_result.errors))

    tool = check_tool(cfg.spades_exec)
    if not tool.available:
        raise RuntimeError(f"SPAdes executable not available: {cfg.spades_exec}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        cfg.spades_exec,
        "-1",
        str(r1),
        "-2",
        str(r2),
        "-o",
        str(output_dir),
        "-t",
        str(max(1, int(cfg.threads))),
        "-m",
        str(max(1, int(cfg.memory))),
    ]
    if singleton is not None:
        cmd.extend(["-s", str(singleton)])
    if cfg.kmers:
        kmer_str = ",".join(str(int(k)) for k in cfg.kmers)
        cmd.extend(["-k", kmer_str])
    if cfg.careful:
        cmd.append("--careful")
    if cfg.only_assembler:
        cmd.append("--only-assembler")
    if cfg.extra_args:
        cmd.extend(str(arg) for arg in cfg.extra_args)

    try:
        run_tool(cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        detail = _extract_stderr(exc)
        msg = f"SPAdes failed with exit code {exc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg) from exc

    contigs = output_dir / "contigs.fasta"
    scaffolds = output_dir / "scaffolds.fasta"
    _resolve_primary_assembly(contigs, scaffolds)

    n_contigs = _count_fasta_records(contigs)
    n_scaffolds = _count_fasta_records(scaffolds)

    return AssemblyResult(
        contigs=contigs,
        scaffolds=scaffolds,
        output_dir=output_dir,
        n_contigs=n_contigs,
        n_scaffolds=n_scaffolds,
    )
