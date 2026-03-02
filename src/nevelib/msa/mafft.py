"""MAFFT alignment interfaces for viral-core and cluster sequences.

This module defines wrapper APIs for direct MAFFT alignments and
seed-and-add workflows.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MafftConfig:
    """Configuration for MAFFT execution.

    Attributes:
        mafft_exec: MAFFT executable path or binary name.
        threads: Number of MAFFT worker threads.
        extra_args: Additional MAFFT CLI arguments.
    """

    mafft_exec: str = "mafft"
    threads: int = 4
    extra_args: list[str] = field(default_factory=list)


def run_mafft(
    input_fasta: Path,
    output_alignment: Path,
    cfg: MafftConfig,
) -> Path:
    """Run MAFFT alignment on an input FASTA file.

    Args:
        input_fasta: Input FASTA file to align.
        output_alignment: Output alignment FASTA path.
        cfg: MAFFT tool settings.

    Returns:
        Path to the alignment FASTA output.

    Side Effects:
        Writes MAFFT alignment output to disk.
    """
    raise NotImplementedError


def run_mafft_seed_and_add(
    seed: Path,
    add: Path | None,
    output: Path,
    cfg: MafftConfig,
) -> Path:
    """Run MAFFT seed alignment and optional add-fragments extension.

    Args:
        seed: FASTA file used to build the seed alignment.
        add: Optional FASTA file of additional fragments.
        output: Output alignment FASTA path.
        cfg: MAFFT tool settings.

    Returns:
        Path to the final alignment FASTA output.

    Side Effects:
        Writes seed/add alignment intermediates and final alignment output.
    """
    raise NotImplementedError
