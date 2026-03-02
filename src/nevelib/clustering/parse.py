"""Cluster parsing and deterministic cluster ID assignment interfaces.

This module provides API stubs for interpreting MMseqs cluster TSV output and
assigning stable integer identifiers.
"""

from pathlib import Path


def parse_mmseqs_clusters(
    cluster_tsv: Path,
    all_ids: list[str],
) -> dict[str, list[str]]:
    """Parse MMseqs cluster assignments from a representative/member TSV.

    Args:
        cluster_tsv: Path to MMseqs cluster TSV (`representative<TAB>member`).
        all_ids: All expected sequence IDs from the input FASTA.

    Returns:
        Mapping from representative ID to ordered member ID list.

    Side Effects:
        None; this function parses cluster TSV content only.
    """
    raise NotImplementedError


def assign_cluster_ids(clusters: dict[str, list[str]]) -> dict[str, int]:
    """Assign deterministic integer IDs to parsed clusters.

    Args:
        clusters: Mapping of representative IDs to member ID lists.

    Returns:
        Mapping from member sequence ID to deterministic cluster ID.
    """
    raise NotImplementedError
