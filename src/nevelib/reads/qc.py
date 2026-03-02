"""Read-level QC and filtering interfaces for the reads module.

This module defines wrappers for FASTP filtering and FastQC reporting.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FastpConfig:
    """Configuration for FASTP read filtering and trimming.

    Attributes:
        executable: FASTP executable path or binary name.
        threads: Number of worker threads.
        enabled: Whether filtering is enabled.
        detect_adapter_for_pe: Enable paired-end adapter autodetection.
        overrepresentation_analysis: Enable overrepresentation report section.
        remove_duplicates: Enable duplicate-read removal.
        extra_args: Additional FASTP CLI flags.
    """

    executable: str = "fastp"
    threads: int = 8
    enabled: bool = True
    detect_adapter_for_pe: bool = True
    overrepresentation_analysis: bool = True
    remove_duplicates: bool = False
    extra_args: list[str] = field(default_factory=list)


@dataclass
class FastqcConfig:
    """Configuration for FastQC reporting.

    Attributes:
        executable: FastQC executable path or binary name.
        threads: Number of worker threads.
    """

    executable: str = "fastqc"
    threads: int = 4


def run_fastp(
    r1: Path,
    r2: Path,
    out_r1: Path,
    out_r2: Path,
    cfg: FastpConfig,
) -> tuple[Path, Path]:
    """Run FASTP on paired FASTQ files.

    Args:
        r1: Input R1 FASTQ(.gz).
        r2: Input R2 FASTQ(.gz).
        out_r1: Output R1 FASTQ(.gz) after filtering.
        out_r2: Output R2 FASTQ(.gz) after filtering.
        cfg: FASTP execution and filtering parameters.

    Returns:
        Tuple of output FASTQ paths `(out_r1, out_r2)`.

    Side Effects:
        Writes filtered FASTQs and FASTP report artifacts.
    """
    raise NotImplementedError


def run_fastqc(
    fastq_files: list[Path],
    outdir: Path,
    cfg: FastqcConfig,
) -> list[Path]:
    """Run FastQC on one or more FASTQ files.

    Args:
        fastq_files: Input FASTQ(.gz) files to profile.
        outdir: Directory where FastQC report artifacts are written.
        cfg: FastQC execution settings.

    Returns:
        Paths to generated FastQC report files.

    Side Effects:
        Creates `outdir` and writes FastQC report files.
    """
    raise NotImplementedError
