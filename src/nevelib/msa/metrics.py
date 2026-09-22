"""Alignment parsing and quality metric computation for MSA outputs."""

from __future__ import annotations

from pathlib import Path

from .alignment_metrics import AlignmentMetrics, MetricsConfig, compute_alignment_metrics

from nevelib._common.fasta import iter_fasta_records


def parse_fasta_alignment(path: Path) -> dict[str, str]:
    """Parse an aligned FASTA file into a mapping of ID to aligned sequence.

    Args:
        path: Alignment FASTA path.

    Returns:
        Mapping `{record_id: aligned_sequence}`.

    Raises:
        ValueError: If parsed aligned sequences have inconsistent lengths.
    """
    aligned: dict[str, str] = {}
    for record_id, sequence in iter_fasta_records(path):
        aligned[record_id] = sequence

    lengths = {len(seq) for seq in aligned.values()}
    if len(lengths) > 1:
        raise ValueError("Alignment sequences have inconsistent lengths.")

    return aligned
