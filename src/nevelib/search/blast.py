"""BLAST execution interfaces for homology search workflows.

This module defines standardized BLASTN/BLASTX wrappers used by the search
module and validation stages.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BlastRunConfig:
    """Configuration for BLAST query execution.

    Attributes:
        blastn_exec: `blastn` executable path or binary name.
        blastx_exec: `blastx` executable path or binary name.
        threads: Number of BLAST threads.
        outfmt: BLAST outfmt string or field list.
        max_target_seqs: Maximum targets per query.
        evalue: E-value threshold.
        extra_params: Additional BLAST CLI arguments.
    """

    blastn_exec: str = "blastn"
    blastx_exec: str = "blastx"
    threads: int = 8
    outfmt: str = "6"
    max_target_seqs: int = 10
    evalue: float = 1e-6
    extra_params: list[str] = field(default_factory=list)


def run_blastn(
    query: Path,
    db_prefix: Path,
    output: Path,
    cfg: BlastRunConfig,
) -> Path:
    """Run BLASTN for a nucleotide query FASTA against a BLAST database.

    Args:
        query: Query FASTA file.
        db_prefix: BLAST database prefix path.
        output: Output path for tabular BLAST results.
        cfg: BLASTN execution settings.

    Returns:
        Path to the BLASTN output file.

    Side Effects:
        Writes BLAST result files and optional logs.
    """
    raise NotImplementedError


def run_blastx(
    query: Path,
    db_prefix: Path,
    output: Path,
    cfg: BlastRunConfig,
) -> Path:
    """Run BLASTX for a nucleotide query FASTA against a protein database.

    Args:
        query: Query FASTA file.
        db_prefix: BLAST database prefix path.
        output: Output path for tabular BLAST results.
        cfg: BLASTX execution settings.

    Returns:
        Path to the BLASTX output file.

    Side Effects:
        Writes BLAST result files and optional logs.
    """
    raise NotImplementedError
