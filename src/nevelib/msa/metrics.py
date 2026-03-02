"""Alignment parsing and quality metric computation for MSA outputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from nevelib._common.fasta import iter_fasta_records


@dataclass
class AlignmentMetrics:
    """Quality metrics for a multiple sequence alignment.

    Attributes:
        n_sequences: Number of sequences in the alignment.
        alignment_length: Total alignment length (including gaps).
        occupied_columns: Number of columns meeting the occupancy threshold.
        mean_pairwise_identity: Mean fraction of identical residue pairs
            across occupied columns (0.0-1.0). None if no occupied columns.
        mean_coverage: Mean fraction of each sequence's original length
            that is covered (non-gap) in the alignment. None if no
            original lengths were provided.
        n_coverage_pass: Number of sequences meeting the minimum coverage.
        n_coverage_fail: Number of sequences below minimum coverage.
        passing: Whether the alignment meets all quality thresholds.
    """

    n_sequences: int = 0
    alignment_length: int = 0
    occupied_columns: int = 0
    mean_pairwise_identity: float | None = None
    mean_coverage: float | None = None
    n_coverage_pass: int = 0
    n_coverage_fail: int = 0
    passing: bool = False


@dataclass
class MetricsConfig:
    """Configuration for alignment quality metrics computation.

    Attributes:
        occupancy_threshold: Minimum fraction of non-gap characters for a
            column to be considered occupied.
        min_identity: Minimum mean pairwise identity to pass.
        min_coverage: Minimum mean coverage to pass.
        min_seq_length: Minimum original sequence length included in
            coverage statistics.
    """

    occupancy_threshold: float = 0.5
    min_identity: float = 0.7
    min_coverage: float = 0.5
    min_seq_length: int = 0


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


def _mean(values: Iterable[float]) -> float | None:
    """Compute arithmetic mean, returning None for empty iterables."""
    vals = list(values)
    if not vals:
        return None
    return float(sum(vals) / len(vals))


def compute_alignment_metrics(
    aligned: dict[str, str],
    cfg: MetricsConfig,
    *,
    original_lengths: dict[str, int] | None = None,
) -> AlignmentMetrics:
    """Compute occupancy, identity, and coverage metrics for an alignment.

    Args:
        aligned: Mapping of sequence IDs to aligned sequence strings.
        cfg: Metric threshold configuration.
        original_lengths: Optional unaligned lengths for coverage statistics.

    Returns:
        AlignmentMetrics summary object.

    Raises:
        ValueError: If aligned sequences have inconsistent lengths.
    """
    if not aligned:
        return AlignmentMetrics()

    seq_ids = list(aligned.keys())
    seqs = [aligned[sid] for sid in seq_ids]
    aln_len = len(seqs[0])

    if any(len(seq) != aln_len for seq in seqs):
        raise ValueError("Alignment sequences have inconsistent lengths.")

    occupied_columns: list[int] = []
    n_sequences = len(seqs)
    for col_idx in range(aln_len):
        non_gap = sum(1 for seq in seqs if seq[col_idx] != "-")
        if (non_gap / max(1, n_sequences)) >= float(cfg.occupancy_threshold):
            occupied_columns.append(col_idx)

    identity_values: list[float] = []
    for col_idx in occupied_columns:
        residues = [seq[col_idx].upper() for seq in seqs if seq[col_idx] != "-"]
        n = len(residues)
        if n < 2:
            continue

        total_pairs = n * (n - 1) // 2
        counts: dict[str, int] = {}
        for residue in residues:
            counts[residue] = counts.get(residue, 0) + 1
        matching_pairs = sum(count * (count - 1) // 2 for count in counts.values())
        identity_values.append(float(matching_pairs / total_pairs))

    mean_pairwise_identity = _mean(identity_values)

    mean_coverage: float | None = None
    n_coverage_pass = 0
    n_coverage_fail = 0

    if original_lengths:
        coverage_values: list[float] = []
        for seq_id, aligned_seq in aligned.items():
            orig_len = int(original_lengths.get(seq_id, 0) or 0)
            if orig_len < int(cfg.min_seq_length) or orig_len <= 0:
                continue
            non_gap = sum(1 for char in aligned_seq if char != "-")
            coverage = float(non_gap / orig_len)
            coverage_values.append(coverage)
            if coverage >= float(cfg.min_coverage):
                n_coverage_pass += 1
            else:
                n_coverage_fail += 1

        mean_coverage = _mean(coverage_values)

    identity_pass = mean_pairwise_identity is not None and mean_pairwise_identity >= float(cfg.min_identity)
    coverage_pass = mean_coverage is None or mean_coverage >= float(cfg.min_coverage)

    return AlignmentMetrics(
        n_sequences=n_sequences,
        alignment_length=aln_len,
        occupied_columns=len(occupied_columns),
        mean_pairwise_identity=mean_pairwise_identity,
        mean_coverage=mean_coverage,
        n_coverage_pass=n_coverage_pass,
        n_coverage_fail=n_coverage_fail,
        passing=bool(identity_pass and coverage_pass),
    )
