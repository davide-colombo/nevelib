"""Deterministic cluster assignment from decoded representative/member pairs."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

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



def assign_cluster_pairs(
    pairs: list[tuple[str, str]],
    all_sequence_ids: list[str],
) -> list[ClusterAssignment]:
    """Assign lexical cluster IDs and append missing expected IDs as singletons."""
    all_ids = list(dict.fromkeys(all_sequence_ids))
    all_id_set = set(all_ids)

    rep_to_members: dict[str, set[str]] = defaultdict(set)
    member_to_rep: dict[str, str] = {}

    for representative_id, member_id in pairs:
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

    clusters.sort(key=lambda item: item[0])

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



ClusterAssignment.__module__ = "nevelib.clustering.parse"
cluster_assignments_to_dataframe.__module__ = "nevelib.clustering.parse"
