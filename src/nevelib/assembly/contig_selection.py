"""Generic in-memory containment selection for self-search hits."""

from __future__ import annotations


def _select_contigs_to_remove(
    blast_rows: list[tuple[str, int, str, int]],
    *,
    known_ids: set[str],
) -> set[str]:
    """Select contigs to remove based on NextEVE containment relationships."""
    removed: set[str] = set()

    for qseqid, qlen, sseqid, slen in blast_rows:
        if qseqid == sseqid:
            continue
        if qseqid not in known_ids or sseqid not in known_ids:
            continue
        if slen < qlen:
            continue
        removed.add(qseqid)

    return removed



_select_contigs_to_remove.__module__ = "nevelib.assembly.dedup"
