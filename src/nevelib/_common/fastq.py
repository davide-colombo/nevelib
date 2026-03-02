"""FASTQ file validation and quality control.

Called by any module that reads or writes FASTQ files.
Provides both validation (pass/fail checks) and QC reporting
(summary statistics).
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FastqValidationResult:
    """Result of FASTQ validation.

    Attributes:
        valid: Whether the file passed all checks.
        path: Path to the validated file.
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected (empty if valid is True).
        read_count: Number of reads detected (None if not counted).
        encoding: Detected quality encoding ('phred33', 'phred64', or None).
    """

    valid: bool
    path: Path
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    read_count: int | None = None
    encoding: str | None = None


@dataclass
class FastqQCReport:
    """Quality control summary for a FASTQ file.

    Attributes:
        path: Path to the FASTQ file.
        total_reads: Total number of reads.
        total_bases: Total number of bases.
        mean_read_length: Mean read length in bases.
        q20_fraction: Fraction of bases with quality >= 20.
        q30_fraction: Fraction of bases with quality >= 30.
        gc_fraction: GC content as a fraction.
        adapter_fraction: Fraction of reads with detected adapters (None if not checked).
        report_path: Path to the full QC report file (e.g., fastp JSON).
    """

    path: Path
    total_reads: int = 0
    total_bases: int = 0
    mean_read_length: float = 0.0
    q20_fraction: float = 0.0
    q30_fraction: float = 0.0
    gc_fraction: float = 0.0
    adapter_fraction: float | None = None
    report_path: Path | None = None


def validate_fastq(
    path: Path,
    *,
    check_gzip: bool = True,
    check_nonempty: bool = True,
    min_reads: int = 1,
    check_encoding: bool = False,
) -> FastqValidationResult:
    """Validate a single FASTQ file.

    Args:
        path: Path to the FASTQ file (may be gzip-compressed).
        check_gzip: Verify gzip integrity if file is compressed.
        check_nonempty: Verify the file contains at least min_reads reads.
        min_reads: Minimum number of reads required.
        check_encoding: Detect Phred encoding variant.

    Returns:
        FastqValidationResult with validation outcome.

    Raises:
        FileNotFoundError: If path does not exist.
    """
    raise NotImplementedError


def validate_paired_fastq(
    r1: Path,
    r2: Path,
    *,
    check_sync: bool = True,
    **kwargs,
) -> tuple[FastqValidationResult, FastqValidationResult]:
    """Validate a pair of FASTQ files and check paired-end synchronization.

    Args:
        r1: Path to the R1 (forward) FASTQ file.
        r2: Path to the R2 (reverse) FASTQ file.
        check_sync: Verify that R1 and R2 have matching read headers.
        **kwargs: Additional arguments passed to validate_fastq for each file.

    Returns:
        Tuple of (R1 result, R2 result). Sync errors are appended to both.
    """
    raise NotImplementedError


def run_fastq_qc(
    r1: Path,
    r2: Path | None = None,
    *,
    output_dir: Path | None = None,
    tool: str = "fastp",
    threads: int = 4,
) -> FastqQCReport:
    """Run quality control reporting on FASTQ file(s).

    Args:
        r1: Path to the R1 (or single-end) FASTQ file.
        r2: Path to the R2 FASTQ file (None for single-end).
        output_dir: Directory to write QC reports. Uses temp dir if None.
        tool: QC tool to use ('fastp' or 'fastqc').
        threads: Number of threads for the QC tool.

    Returns:
        FastqQCReport summarizing the results.
    """
    raise NotImplementedError
