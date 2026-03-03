"""Alignment parsing and quality metric computation for MSA outputs."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from pathlib import Path

from nevelib._common.fasta import iter_fasta_records


@dataclass
class AlignmentMetrics:
    """Alignment coherence metrics aligned with NextEVE Stage_06 outputs."""

    n_total: int = 0
    n_aligned: int = 0
    shared_span_bp: int = 0
    shared_span_frac: float = 0.0
    median_identity: float | None = None
    p10_identity: float | None = None
    median_sequence_length: float | None = None
    frac_length_ge_min: float | None = None


@dataclass
class MetricsConfig:
    """Configuration for alignment coherence computation."""

    occupancy_threshold: float = 0.60
    min_seq_length: int = 80


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


def compute_alignment_metrics(
    aligned: dict[str, str],
    cfg: MetricsConfig,
    *,
    core_lengths: dict[str, int] | None = None,
    original_lengths: dict[str, int] | None = None,
) -> AlignmentMetrics:
    """Compute Stage_06-compatible alignment coherence metrics.

    Args:
        aligned: Mapping of sequence IDs to aligned sequence strings.
        cfg: Coherence metric configuration.
        core_lengths: Optional unaligned sequence-length mapping.
        original_lengths: Deprecated alias for `core_lengths`.

    Returns:
        AlignmentMetrics summary object.

    Raises:
        ValueError: If aligned sequences have inconsistent lengths.
    """
    lengths_map = (
        core_lengths
        if core_lengths is not None
        else (
            original_lengths
            if original_lengths is not None
            else {sid: sum(1 for ch in seq if ch != "-") for sid, seq in aligned.items()}
        )
    )

    if not aligned:
        return AlignmentMetrics(
            n_total=len(lengths_map),
            n_aligned=0,
            shared_span_bp=0,
            shared_span_frac=0.0,
            median_identity=None,
            p10_identity=None,
            median_sequence_length=None,
            frac_length_ge_min=None,
        )

    seq_ids = sorted(aligned.keys())
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

    consensus: list[str] = []
    for col_idx in occupied_columns:
        residues = [seq[col_idx].upper() for seq in seqs]
        counts = Counter(residue for residue in residues if residue in {"A", "C", "G", "T"})
        consensus.append(counts.most_common(1)[0][0] if counts else "N")

    identities: list[float] = []
    for seq in seqs:
        matches = 0
        denom = 0
        for idx, col_idx in enumerate(occupied_columns):
            char = seq[col_idx].upper()
            if char == "-":
                continue
            denom += 1
            if char == consensus[idx]:
                matches += 1
        identities.append((matches / denom) if denom > 0 else 0.0)

    identities_sorted = sorted(identities)
    median_identity: float | None = None
    p10_identity: float | None = None
    if identities_sorted:
        mid = len(identities_sorted) // 2
        if len(identities_sorted) % 2 == 1:
            median_identity = float(identities_sorted[mid])
        else:
            median_identity = 0.5 * (identities_sorted[mid - 1] + identities_sorted[mid])
        p10_idx = max(0, int(math.floor(0.10 * (len(identities_sorted) - 1))))
        p10_identity = float(identities_sorted[p10_idx])

    lengths = [int(lengths_map.get(seq_id, 0) or 0) for seq_id in seq_ids]
    lengths_sorted = sorted(lengths)
    median_sequence_length: float | None = None
    if lengths_sorted:
        mid = len(lengths_sorted) // 2
        if len(lengths_sorted) % 2 == 1:
            median_sequence_length = float(lengths_sorted[mid])
        else:
            median_sequence_length = 0.5 * (lengths_sorted[mid - 1] + lengths_sorted[mid])

    frac_length_ge_min: float | None = None
    if lengths:
        frac_length_ge_min = sum(1 for x in lengths if x >= int(cfg.min_seq_length)) / max(1, len(lengths))

    return AlignmentMetrics(
        n_total=len(lengths_map),
        n_aligned=len(seq_ids),
        shared_span_bp=len(occupied_columns),
        shared_span_frac=float(len(occupied_columns) / max(1, aln_len)),
        median_identity=median_identity,
        p10_identity=p10_identity,
        median_sequence_length=median_sequence_length,
        frac_length_ge_min=frac_length_ge_min,
    )
