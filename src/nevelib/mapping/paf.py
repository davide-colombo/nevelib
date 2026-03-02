"""PAF parsing and filtering utilities for minimap2 alignment output."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
import logging
from pathlib import Path


LOGGER = logging.getLogger(__name__)


@dataclass
class PafRecord:
    """A single record from a PAF (Pairwise mApping Format) file.

    The 12 mandatory PAF columns are parsed into strongly typed fields.
    Optional tag fields are stored in `tags`.

    Attributes:
        qname: Query sequence name.
        qlen: Query sequence length.
        qstart: Query start (0-based).
        qend: Query end (0-based, exclusive).
        strand: Relative strand ('+' or '-').
        tname: Target sequence name.
        tlen: Target sequence length.
        tstart: Target start (0-based).
        tend: Target end (0-based, exclusive).
        nmatch: Number of matching bases.
        aln_len: Alignment block length.
        mapq: Mapping quality.
        tags: Optional PAF tags as key-value pairs.
    """

    qname: str
    qlen: int
    qstart: int
    qend: int
    strand: str
    tname: str
    tlen: int
    tstart: int
    tend: int
    nmatch: int
    aln_len: int
    mapq: int
    tags: dict[str, str] = field(default_factory=dict)


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


def alignment_identity(record: PafRecord) -> float:
    """Return alignment identity as nmatch / aln_len with zero-safe handling."""
    if int(record.aln_len) <= 0:
        return 0.0
    return float(record.nmatch) / float(record.aln_len)


def query_coverage(record: PafRecord) -> float:
    """Return covered fraction of query sequence for one record."""
    if int(record.qlen) <= 0:
        return 0.0
    return float(int(record.qend) - int(record.qstart)) / float(record.qlen)


def target_coverage(record: PafRecord) -> float:
    """Return covered fraction of target sequence for one record."""
    if int(record.tlen) <= 0:
        return 0.0
    return float(int(record.tend) - int(record.tstart)) / float(record.tlen)


def filter_paf_records(
    records: list[PafRecord],
    *,
    min_mapq: int | None = None,
    min_aln_len: int | None = None,
    min_nmatch: int | None = None,
    min_identity: float | None = None,
) -> list[PafRecord]:
    """Filter PAF records by optional numeric thresholds.

    Args:
        records: PAF records to filter.
        min_mapq: Minimum mapping quality.
        min_aln_len: Minimum alignment block length.
        min_nmatch: Minimum number of matching bases.
        min_identity: Minimum identity threshold (nmatch / aln_len).

    Returns:
        Records passing all enabled thresholds.
    """
    filtered: list[PafRecord] = []

    for record in records:
        if min_mapq is not None and int(record.mapq) < int(min_mapq):
            continue
        if min_aln_len is not None and int(record.aln_len) < int(min_aln_len):
            continue
        if min_nmatch is not None and int(record.nmatch) < int(min_nmatch):
            continue
        if min_identity is not None and alignment_identity(record) < float(min_identity):
            continue
        filtered.append(record)

    return filtered


def best_hit_per_query(
    records: list[PafRecord],
    *,
    metric: str = "nmatch",
    ascending: bool = False,
) -> dict[str, PafRecord]:
    """Select the best PAF record per query with deterministic tie-breaking.

    Selection order:
    1) requested metric
    2) mapq descending
    3) aln_len descending
    4) nmatch descending
    5) target coordinates/name deterministic ordering

    Args:
        records: Candidate records.
        metric: PafRecord numeric field used for primary ranking.
        ascending: If True, lower metric values are preferred.

    Returns:
        Mapping from qname to selected best record.
    """
    if metric not in PafRecord.__dataclass_fields__:
        raise ValueError(f"Unsupported metric for PafRecord: {metric}")

    grouped: dict[str, list[PafRecord]] = defaultdict(list)
    for record in records:
        grouped[record.qname].append(record)

    selected: dict[str, PafRecord] = {}

    for qname, group in grouped.items():
        def _rank_key(record: PafRecord) -> tuple[float, int, int, int, str, int, int, str, str]:
            value = getattr(record, metric)
            primary = float(value)
            primary_key = primary if ascending else -primary
            return (
                primary_key,
                -int(record.mapq),
                -int(record.aln_len),
                -int(record.nmatch),
                str(record.tname),
                int(record.tstart),
                int(record.tend),
                str(record.strand),
                str(record.qname),
            )

        selected[qname] = sorted(group, key=_rank_key)[0]

    return selected
