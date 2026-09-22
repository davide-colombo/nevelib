"""In-memory identity, coverage and selection for half-open PAF records."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field


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
    metric: str = "mapq",
    ascending: bool = False,
) -> dict[str, PafRecord]:
    """Select the best PAF record per query with deterministic tie-breaking.

    Selection order:
    1) requested metric
    2) aln_len descending for `metric='mapq'`, otherwise mapq descending
    3) nmatch descending
    4) target coordinates/name deterministic ordering

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
            if metric == "mapq":
                secondary_1 = -int(record.aln_len)
                secondary_2 = -int(record.nmatch)
                secondary_3 = 0
            else:
                secondary_1 = -int(record.mapq)
                secondary_2 = -int(record.aln_len)
                secondary_3 = -int(record.nmatch)
            return (
                primary_key,
                secondary_1,
                secondary_2,
                secondary_3,
                str(record.tname),
                int(record.tstart),
                int(record.tend),
                str(record.strand),
                str(record.qname),
            )

        selected[qname] = sorted(group, key=_rank_key)[0]

    return selected



PafRecord.__module__ = "nevelib.mapping.paf"
alignment_identity.__module__ = "nevelib.mapping.paf"
query_coverage.__module__ = "nevelib.mapping.paf"
target_coverage.__module__ = "nevelib.mapping.paf"
filter_paf_records.__module__ = "nevelib.mapping.paf"
best_hit_per_query.__module__ = "nevelib.mapping.paf"
