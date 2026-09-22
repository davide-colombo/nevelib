"""PAF parsing and filtering utilities for minimap2 alignment output."""

from __future__ import annotations

from collections import defaultdict
import logging
from pathlib import Path

from .alignment_selection import (
    PafRecord,
    alignment_identity,
    query_coverage,
    target_coverage,
    filter_paf_records,
    best_hit_per_query,
)


LOGGER = logging.getLogger(__name__)


def _to_int(raw: str) -> int:
    """Convert text field to integer for mandatory PAF numeric columns."""
    return int(raw)


def parse_paf(path: Path) -> list[PafRecord]:
    """Parse a PAF file into a list of PafRecord entries.

    Malformed rows with fewer than 12 fields are skipped with a warning.

    Args:
        path: Input PAF path.

    Returns:
        Parsed PAF records.
    """
    if not path.exists() or path.stat().st_size == 0:
        return []

    records: list[PafRecord] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            parts = line.split("\t")
            if len(parts) < 12:
                LOGGER.warning(
                    "Skipping malformed PAF line %d in %s: expected >=12 fields, got %d.",
                    line_no,
                    path,
                    len(parts),
                )
                continue

            try:
                qname = parts[0]
                qlen = _to_int(parts[1])
                qstart = _to_int(parts[2])
                qend = _to_int(parts[3])
                strand = parts[4]
                tname = parts[5]
                tlen = _to_int(parts[6])
                tstart = _to_int(parts[7])
                tend = _to_int(parts[8])
                nmatch = _to_int(parts[9])
                aln_len = _to_int(parts[10])
                mapq = _to_int(parts[11])
            except Exception:
                LOGGER.warning("Skipping malformed numeric PAF line %d in %s.", line_no, path)
                continue

            tags: dict[str, str] = {}
            for tag_field in parts[12:]:
                tag_bits = tag_field.split(":", 2)
                if len(tag_bits) == 3:
                    tag_name, _tag_type, tag_value = tag_bits
                    tags[tag_name] = tag_value
                elif len(tag_bits) >= 1 and tag_bits[0]:
                    tags[tag_bits[0]] = tag_field

            records.append(
                PafRecord(
                    qname=qname,
                    qlen=qlen,
                    qstart=qstart,
                    qend=qend,
                    strand=strand,
                    tname=tname,
                    tlen=tlen,
                    tstart=tstart,
                    tend=tend,
                    nmatch=nmatch,
                    aln_len=aln_len,
                    mapq=mapq,
                    tags=tags,
                )
            )

    return records


def parse_paf_by_query(path: Path) -> dict[str, list[PafRecord]]:
    """Parse PAF and return records grouped by query name."""
    grouped: dict[str, list[PafRecord]] = defaultdict(list)
    for record in parse_paf(path):
        grouped[record.qname].append(record)
    return dict(grouped)
