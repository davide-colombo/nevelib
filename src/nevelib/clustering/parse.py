"""Cluster parsing and deterministic cluster ID assignment utilities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class ClusterAssignment:
    """A single sequence's cluster assignment.

    Attributes:
        sequence_id: The original sequence identifier.
        cluster_id: Integer cluster ID (deterministically assigned).
        is_representative: Whether this sequence is the cluster representative.
        representative_id: Sequence ID of the cluster representative.
    """

    sequence_id: str
    cluster_id: int
    is_representative: bool
    representative_id: str


def _read_cluster_pairs(cluster_tsv: Path) -> list[tuple[str, str]]:
    """Read representative/member rows from a MMseqs cluster TSV."""
    if not cluster_tsv.exists():
        raise FileNotFoundError(cluster_tsv)

    pairs: list[tuple[str, str]] = []
    with cluster_tsv.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 2:
                raise ValueError(
                    f"Malformed MMseqs cluster TSV at {cluster_tsv}:{line_no}: expected two tab-separated columns."
                )
            representative_id = parts[0].strip()
            member_id = parts[1].strip()
            if not representative_id or not member_id:
                raise ValueError(
                    f"Malformed MMseqs cluster TSV at {cluster_tsv}:{line_no}: empty representative/member token."
                )
            pairs.append((representative_id, member_id))
    return pairs


def parse_mmseqs_clusters(
    cluster_tsv: Path,
    all_sequence_ids: list[str],
) -> list[ClusterAssignment]:
    """Parse MMseqs cluster TSV and build deterministic assignments.

    Cluster IDs are assigned by sorting clusters by:
    1) cluster size descending
    2) representative ID ascending

    IDs from `all_sequence_ids` missing in the cluster TSV are added as
    singleton clusters with unique IDs.

    Args:
        cluster_tsv: Path to MMseqs cluster TSV (`representative<TAB>member`).
        all_sequence_ids: Complete set of sequence IDs expected in output.

    Returns:
        List of `ClusterAssignment` entries covering every ID in
        `all_sequence_ids`.
    """
    all_ids = list(dict.fromkeys(all_sequence_ids))
    all_id_set = set(all_ids)

    rep_to_members: dict[str, set[str]] = defaultdict(set)
    member_to_rep: dict[str, str] = {}

    for representative_id, member_id in _read_cluster_pairs(cluster_tsv):
        rep_to_members[representative_id].add(member_id)
        rep_to_members[representative_id].add(representative_id)

    assignments: list[ClusterAssignment] = []
    assigned_ids: set[str] = set()

    clusters: list[tuple[str, list[str]]] = []
    for representative_id, members in rep_to_members.items():
        filtered_members = sorted(member for member in members if member in all_id_set)
        if not filtered_members:
            continue
        clusters.append((representative_id, filtered_members))

    clusters.sort(key=lambda item: (-len(item[1]), item[0]))

    next_cluster_id = 1
    for representative_id, members in clusters:
        for sequence_id in members:
            existing_rep = member_to_rep.get(sequence_id)
            if existing_rep is not None and existing_rep != representative_id:
                raise ValueError(
                    f"Sequence ID '{sequence_id}' appears in multiple clusters: "
                    f"'{existing_rep}' and '{representative_id}'."
                )
            member_to_rep[sequence_id] = representative_id

        for sequence_id in members:
            assignments.append(
                ClusterAssignment(
                    sequence_id=sequence_id,
                    cluster_id=next_cluster_id,
                    is_representative=(sequence_id == representative_id),
                    representative_id=representative_id,
                )
            )
            assigned_ids.add(sequence_id)
        next_cluster_id += 1

    for sequence_id in sorted(all_id_set - assigned_ids):
        assignments.append(
            ClusterAssignment(
                sequence_id=sequence_id,
                cluster_id=next_cluster_id,
                is_representative=True,
                representative_id=sequence_id,
            )
        )
        next_cluster_id += 1

    assignments.sort(key=lambda a: (a.cluster_id, a.sequence_id))
    return assignments


def validate_existing_clusters(cluster_tsv: Path, all_sequence_ids: list[str]) -> tuple[bool, str]:
    """Validate that a pre-existing MMseqs cluster TSV covers all IDs.

    Args:
        cluster_tsv: Path to existing cluster TSV.
        all_sequence_ids: IDs that must be represented by the TSV.

    Returns:
        `(True, "")` when valid, otherwise `(False, reason)`.
    """
    if not cluster_tsv.exists():
        return False, "file does not exist"
    if cluster_tsv.stat().st_size == 0:
        return False, "file is missing or empty"

    all_ids = set(all_sequence_ids)
    seen: set[str] = set()

    with cluster_tsv.open("r", encoding="utf-8") as handle:
        has_data = False
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            has_data = True
            parts = line.split("\t")
            if len(parts) < 2:
                return False, f"line {line_no} is malformed"

            representative_id = parts[0].strip()
            member_id = parts[1].strip()
            if not representative_id or not member_id:
                return False, f"line {line_no} has empty representative/member"
            if representative_id not in all_ids or member_id not in all_ids:
                return False, (
                    "line "
                    f"{line_no} contains IDs not present in current sequence set: "
                    f"rep={representative_id!r} member={member_id!r}"
                )
            seen.add(representative_id)
            seen.add(member_id)

    if not has_data:
        return False, "no valid data lines were found"

    missing = sorted(all_ids - seen)
    if missing:
        return False, f"{len(missing)} ID(s) are missing from cluster TSV coverage"

    return True, ""


def cluster_assignments_to_dataframe(assignments: list[ClusterAssignment]) -> pd.DataFrame:
    """Convert assignment objects to a sorted pandas DataFrame.

    Args:
        assignments: Cluster assignments for each sequence.

    Returns:
        DataFrame with columns:
        `sequence_id`, `cluster_id`, `is_representative`, `representative_id`.
    """
    rows = [
        {
            "sequence_id": assignment.sequence_id,
            "cluster_id": int(assignment.cluster_id),
            "is_representative": bool(assignment.is_representative),
            "representative_id": assignment.representative_id,
        }
        for assignment in assignments
    ]

    df = pd.DataFrame(
        rows,
        columns=["sequence_id", "cluster_id", "is_representative", "representative_id"],
    )
    if df.empty:
        return df

    df["cluster_id"] = pd.to_numeric(df["cluster_id"], errors="raise").astype("int64")
    df["is_representative"] = df["is_representative"].astype(bool)
    df = df.sort_values(by=["cluster_id", "sequence_id"], kind="mergesort").reset_index(drop=True)
    return df
