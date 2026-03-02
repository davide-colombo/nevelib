"""Minimap2 mapping interfaces for pairwise/reference alignment.

This module exposes the public API for running minimap2 and producing
PAF output for downstream parsing.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Minimap2Config:
    """Configuration for minimap2 execution.

    Attributes:
        minimap2_exec: Minimap2 executable path or binary name.
        threads: Number of minimap2 threads.
        preset: Minimap2 preset passed with `-x`.
        extra_args: Additional minimap2 CLI args.
        include_secondary: Whether to emit secondary alignments.
    """

    minimap2_exec: str = "minimap2"
    threads: int = 4
    preset: str = "sr"
    extra_args: list[str] = field(default_factory=list)
    include_secondary: bool = True


def run_minimap2(
    query: Path,
    reference: Path,
    output: Path,
    cfg: Minimap2Config,
) -> Path:
    """Run minimap2 and write mappings in PAF format.

    Args:
        query: Query FASTA/FASTQ file.
        reference: Reference FASTA file.
        output: Output PAF file path.
        cfg: Minimap2 execution settings.

    Returns:
        Path to the output PAF file.

    Side Effects:
        Writes PAF alignment output and optional log artifacts.
    """
    raise NotImplementedError
