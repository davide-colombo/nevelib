"""Alignment parsing and quality metric interfaces.

This module defines API stubs for parsing aligned FASTA files and computing
shared-span/identity metrics used for downstream evidence scoring.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class AlignmentMetricConfig:
    """Configuration for alignment metric computation.

    Attributes:
        min_core_len: Minimum core length threshold for summary metrics.
        occupancy_p: Minimum non-gap occupancy threshold per alignment column.
    """

    min_core_len: int = 80
    occupancy_p: float = 0.6


@dataclass
class AlignmentMetrics:
    """Summary metrics describing alignment coherence.

    Attributes:
        n_total: Total number of candidate sequences.
        n_aligned: Number of sequences present in the alignment.
        shared_span_bp: Number of columns passing occupancy threshold.
        shared_span_frac: Fraction of alignment columns in shared span.
        median_identity_to_consensus: Median identity to consensus over shared span.
        p10_identity_to_consensus: 10th percentile identity to consensus.
        median_core_len: Median input core length.
        frac_core_len_ge_min: Fraction of members with core length >= min_core_len.
    """

    n_total: int
    n_aligned: int
    shared_span_bp: int
    shared_span_frac: float
    median_identity_to_consensus: float | None
    p10_identity_to_consensus: float | None
    median_core_len: float | None
    frac_core_len_ge_min: float | None


def parse_fasta_alignment(path: Path) -> dict[str, str]:
    """Parse an alignment FASTA into an in-memory ID-to-sequence mapping.

    Args:
        path: Alignment FASTA path.

    Returns:
        Dictionary mapping sequence IDs to aligned sequence strings.
    """
    raise NotImplementedError


def compute_alignment_metrics(
    aligned_records: dict[str, str],
    cfg: AlignmentMetricConfig,
) -> AlignmentMetrics:
    """Compute coherence metrics from aligned sequence records.

    Args:
        aligned_records: Mapping of sequence ID to aligned sequence.
        cfg: Metric thresholds for occupancy and minimum core length.

    Returns:
        AlignmentMetrics summary dataclass.
    """
    raise NotImplementedError
