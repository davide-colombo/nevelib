"""MMseqs2 clustering interfaces.

This module provides the public API for running `mmseqs easy-linclust`
with reproducible clustering settings.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class MmseqsConfig:
    """Configuration for MMseqs2 clustering runs.

    Attributes:
        mmseqs_exec: MMseqs2 executable path or binary name.
        min_seq_id: Minimum sequence identity threshold.
        min_aln_len: Minimum alignment length threshold.
        coverage: Coverage fraction threshold.
        cov_mode: MMseqs coverage mode.
        alignment_mode: MMseqs alignment mode.
        threads: Number of MMseqs threads.
        split_memory_limit: Optional memory split limit (e.g., `260G`).
    """

    mmseqs_exec: str = "mmseqs"
    min_seq_id: float = 0.9
    min_aln_len: int = 80
    coverage: float = 0.8
    cov_mode: int = 5
    alignment_mode: int = 3
    threads: int = 8
    split_memory_limit: str | None = None


def run_mmseqs_linclust(
    input_fasta: Path,
    output_prefix: Path,
    tmp_dir: Path,
    cfg: MmseqsConfig,
) -> Path:
    """Run MMseqs2 easy-linclust for nucleotide sequence clustering.

    Args:
        input_fasta: Input FASTA containing sequences to cluster.
        output_prefix: Output prefix used by MMseqs2.
        tmp_dir: Temporary working directory for MMseqs2 internals.
        cfg: MMseqs2 execution and threshold parameters.

    Returns:
        Path to the generated cluster TSV file.

    Side Effects:
        Writes MMseqs2 output files and temporary working artifacts.
    """
    raise NotImplementedError
