"""BAM-to-FASTQ read extraction utilities."""

from __future__ import annotations

from dataclasses import dataclass
import gzip
from pathlib import Path
import shlex
import shutil
import subprocess

from nevelib._common.bam import validate_bam
from nevelib._common.compression import CompressionConfig, recompress_if_bgzf, validate_gzip
from nevelib._common.fastq import validate_fastq
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class ExtractionConfig:
    """Configuration for BAM read extraction.

    Attributes:
        samtools_exec: samtools executable name/path.
        threads: Number of worker threads.
        extract_unmapped: Restrict extraction to unmapped reads.
        extract_supplementary: Include supplementary alignments.
        include_secondary: Include secondary alignments.
        mapq_min: Minimum MAPQ threshold (applied in samtools view).
    """

    samtools_exec: str = "samtools"
    threads: int = 8
    extract_unmapped: bool = True
    extract_supplementary: bool = False
    include_secondary: bool = False
    mapq_min: int = 0


@dataclass
class ExtractionResult:
    """Output paths and basic counts from read extraction."""

    r1: Path
    r2: Path
    singleton: Path | None = None
    total_extracted: int = 0
    paired_count: int = 0
    singleton_count: int = 0


def _write_empty_gzip(path: Path) -> None:
    """Write a valid empty gzip file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wb"):
        pass


def _ensure_fastq_outputs(r1: Path, r2: Path, singleton: Path) -> None:
    """Ensure expected FASTQ outputs exist after extraction command."""
    for path in (r1, r2, singleton):
        if path.exists():
            continue
        if path.suffix.lower() == ".gz":
            _write_empty_gzip(path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("", encoding="utf-8")


def _count_fastq_reads(path: Path) -> int:
    """Count FASTQ records using common validator parsing."""
    result = validate_fastq(path, check_gzip=True, check_nonempty=False, check_encoding=False)
    if not result.valid:
        raise RuntimeError(f"Extracted FASTQ failed validation ({path}): {'; '.join(result.errors)}")
    return int(result.read_count or 0)


def _normalize_bgzf_outputs(
    paths: list[Path],
    compression_cfg: CompressionConfig,
) -> None:
    """Recompress BGZF outputs to canonical gzip when detected."""
    for path in paths:
        if path.suffix.lower() != ".gz" or not path.exists():
            continue
        variant = validate_gzip(path)
        if variant != "bgzf":
            continue
        fixed = path.with_suffix(path.suffix + ".fixed")
        recompress_if_bgzf(path, fixed, compression_cfg)
        shutil.move(str(fixed), str(path))


def _build_view_filters(cfg: ExtractionConfig) -> tuple[list[str], list[str]]:
    """Return samtools view include/exclude flag arguments."""
    include_args: list[str] = []
    if cfg.extract_unmapped:
        include_args.extend(["-f", "4"])

    exclude_flag = 0
    if not cfg.include_secondary:
        exclude_flag |= 0x100
    if not cfg.extract_supplementary:
        exclude_flag |= 0x800

    # Keep behavior close to NextEVE extraction by excluding QC-fail and duplicates.
    exclude_flag |= 0x600

    exclude_args: list[str] = []
    if exclude_flag:
        exclude_args.extend(["-F", str(exclude_flag)])

    return include_args, exclude_args


def _run_extraction_pipeline(
    bam: Path,
    r1_out: Path,
    r2_out: Path,
    singleton_out: Path,
    cfg: ExtractionConfig,
) -> None:
    """Run samtools view | samtools fastq pipeline."""
    include_args, exclude_args = _build_view_filters(cfg)

    view_cmd = [
        cfg.samtools_exec,
        "view",
        "-h",
        "-@",
        str(max(1, int(cfg.threads))),
        *include_args,
        *exclude_args,
    ]
    if int(cfg.mapq_min) > 0:
        view_cmd.extend(["-q", str(int(cfg.mapq_min))])
    view_cmd.append(str(bam))

    fastq_cmd = [
        cfg.samtools_exec,
        "fastq",
        "-@",
        str(max(1, int(cfg.threads))),
        "-1",
        str(r1_out),
        "-2",
        str(r2_out),
        "-s",
        str(singleton_out),
        "-0",
        "/dev/null",
        "-N",
        "-",
    ]

    cmd = f"{shlex.join(view_cmd)} | {shlex.join(fastq_cmd)}"
    run_tool(cmd, check=True)


def extract_reads_from_bam(
    bam: Path,
    output_dir: Path,
    cfg: ExtractionConfig,
    *,
    compression_cfg: CompressionConfig | None = None,
) -> ExtractionResult:
    """Extract paired and singleton reads from a BAM file.

    Args:
        bam: Input BAM path.
        output_dir: Destination directory for extracted FASTQ files.
        cfg: Extraction runtime settings.
        compression_cfg: Compression settings used for BGZF-to-gzip normalization.

    Returns:
        ExtractionResult with output paths and basic read counts.
    """
    bam_validation = validate_bam(bam, require_sorted=True, require_index=True, run_quickcheck=True)
    if not bam_validation.valid:
        raise ValueError("Invalid BAM input: " + "; ".join(bam_validation.errors))

    tool = check_tool(cfg.samtools_exec, version_args=["--version"])
    if not tool.available:
        raise RuntimeError(f"samtools executable not available: {cfg.samtools_exec}")

    output_dir.mkdir(parents=True, exist_ok=True)
    r1_out = output_dir / "reads_R1.fq.gz"
    r2_out = output_dir / "reads_R2.fq.gz"
    singleton_out = output_dir / "reads_singletons.fq.gz"

    try:
        _run_extraction_pipeline(bam, r1_out, r2_out, singleton_out, cfg)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        raise RuntimeError(f"samtools extraction failed (exit code {exc.returncode}): {stderr.strip()}") from exc

    _ensure_fastq_outputs(r1_out, r2_out, singleton_out)

    _normalize_bgzf_outputs(
        [r1_out, r2_out, singleton_out],
        compression_cfg or CompressionConfig(),
    )

    r1_count = _count_fastq_reads(r1_out)
    r2_count = _count_fastq_reads(r2_out)
    singleton_count = _count_fastq_reads(singleton_out)
    paired_count = min(r1_count, r2_count)

    return ExtractionResult(
        r1=r1_out,
        r2=r2_out,
        singleton=singleton_out,
        total_extracted=(paired_count * 2) + singleton_count,
        paired_count=paired_count,
        singleton_count=singleton_count,
    )


def extract_unmapped_reads(
    bam: Path,
    r1_out: Path,
    r2_out: Path,
    singleton_out: Path,
    cfg: ExtractionConfig,
) -> ExtractionResult:
    """Backward-compatible extraction API with explicit output paths."""
    result = extract_reads_from_bam(
        bam=bam,
        output_dir=r1_out.parent,
        cfg=cfg,
        compression_cfg=CompressionConfig(),
    )

    # If caller-provided paths differ from default output names, move outputs.
    for src, dst in (
        (result.r1, r1_out),
        (result.r2, r2_out),
        (result.singleton, singleton_out),
    ):
        if src is None:
            continue
        if src.resolve() == dst.resolve():
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dst))

    return ExtractionResult(
        r1=r1_out,
        r2=r2_out,
        singleton=singleton_out,
        total_extracted=result.total_extracted,
        paired_count=result.paired_count,
        singleton_count=result.singleton_count,
    )
