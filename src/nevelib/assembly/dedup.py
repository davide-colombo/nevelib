"""BLAST-based scaffold deduplication interfaces.

This module defines the API for self-BLAST containment deduplication of
assembled scaffolds.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class DedupConfig:
    """Configuration for scaffold deduplication.

    Attributes:
        makeblastdb_exec: `makeblastdb` executable.
        blastn_exec: `blastn` executable.
        threads: Number of BLAST threads.
        evalue: E-value cutoff for containment hits.
        max_target_seqs: Maximum target sequences per query.
        extra_params: Additional BLAST arguments.
        qc_enabled: Whether scaffold QC hooks are enabled.
    """

    makeblastdb_exec: str = "makeblastdb"
    blastn_exec: str = "blastn"
    threads: int = 8
    evalue: float = 1e-20
    max_target_seqs: int = 100
    extra_params: list[str] = field(default_factory=list)
    qc_enabled: bool = True


def deduplicate_scaffolds(
    input_fasta: Path,
    output_fasta: Path,
    cfg: DedupConfig,
) -> None:
    """Remove fully contained scaffolds using self-BLAST comparison.

    Args:
        input_fasta: Input scaffold FASTA to deduplicate.
        output_fasta: Output FASTA containing non-redundant scaffolds.
        cfg: BLAST tool and deduplication thresholds.

    Side Effects:
        Creates BLAST database/intermediate files and writes deduplicated FASTA.
    """
    raise NotImplementedError
