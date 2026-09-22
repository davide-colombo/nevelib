"""Cluster parsing and deterministic cluster ID assignment utilities."""

from __future__ import annotations

from pathlib import Path

from .assignments import ClusterAssignment, assign_cluster_pairs, cluster_assignments_to_dataframe


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

    Cluster IDs are assigned by representative ID (ascending lexicographic),
    matching NextEVE Stage_03/Stage_05 behavior.

    IDs from `all_sequence_ids` missing in the cluster TSV are added as
    singleton clusters with unique IDs.

    Args:
        cluster_tsv: Path to MMseqs cluster TSV (`representative<TAB>member`).
        all_sequence_ids: Complete set of sequence IDs expected in output.

    Returns:
        List of `ClusterAssignment` entries covering every ID in
        `all_sequence_ids`.
    """
    # Preserve expected-ID normalization before attempting to read the file.
    all_ids = list(dict.fromkeys(all_sequence_ids))
    return assign_cluster_pairs(_read_cluster_pairs(cluster_tsv), all_ids)


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
