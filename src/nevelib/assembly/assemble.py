"""De novo assembly interfaces for normalized reads.

This module defines the public API for SPAdes-based contig/scaffold assembly.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AssemblyConfig:
    """Configuration for de novo assembly.

    Attributes:
        spades_exec: SPAdes executable path or binary name.
        threads: Number of SPAdes worker threads.
        memory_gb: Optional memory limit in GB.
        k: Optional comma-separated k-mer list.
        resume: Resume an existing assembly directory.
        min_contig_len: Minimum contig length cutoff.
        qc_enabled: Whether downstream scaffold QC hooks are enabled.
        extra_args: Additional SPAdes arguments.
        tmp_dir: Optional temporary directory.
    """

    spades_exec: str = "spades.py"
    threads: int = 16
    memory_gb: int | None = None
    k: str | None = None
    resume: bool = False
    min_contig_len: int = 0
    qc_enabled: bool = True
    extra_args: list[str] = field(default_factory=list)
    tmp_dir: Path | None = None


def assemble_reads(
    r1: Path,
    r2: Path,
    singleton: Path | None,
    outdir: Path,
    cfg: AssemblyConfig,
) -> Path:
    """Assemble paired/singleton reads into scaffolds.

    Args:
        r1: Input R1 FASTQ(.gz).
        r2: Input R2 FASTQ(.gz).
        singleton: Optional singleton FASTQ(.gz).
        outdir: Assembly output directory.
        cfg: Assembly runtime and filtering settings.

    Returns:
        Path to the canonical scaffold FASTA output.

    Side Effects:
        Creates `outdir`, runs the assembler, and writes assembly artifacts.
    """
    raise NotImplementedError
