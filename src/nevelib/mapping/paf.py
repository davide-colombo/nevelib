"""PAF parsing and filtering interfaces for mapping results.

This module defines common PAF record structures and helper operations used
by mapping-centric workflows.
"""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class PafHit:
    """One parsed PAF alignment record.

    Attributes:
        qname: Query sequence name.
        qlen: Query sequence length.
        qstart: Query alignment start (0-based).
        qend: Query alignment end (0-based, half-open).
        strand: Alignment strand (`+` or `-`).
        tname: Target sequence name.
        tlen: Target sequence length.
        tstart: Target alignment start (0-based).
        tend: Target alignment end (0-based, half-open).
        nmatch: Number of residue matches.
        alen: Alignment block length.
        mapq: Mapping quality.
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
    alen: int
    mapq: int


@dataclass
class PafFilterConfig:
    """Configuration for filtering parsed PAF records.

    Attributes:
        min_mapq: Minimum MAPQ threshold.
        min_aln_len: Minimum alignment length threshold.
        min_nmatch: Minimum match count threshold.
    """

    min_mapq: int = 0
    min_aln_len: int = 0
    min_nmatch: int = 0


def parse_paf(path: Path) -> list[PafHit]:
    """Parse a PAF file into a list of alignment records.

    Args:
        path: Input PAF file path.

    Returns:
        List of parsed `PafHit` entries.
    """
    raise NotImplementedError


def filter_paf_hits(hits: list[PafHit], cfg: PafFilterConfig) -> list[PafHit]:
    """Filter PAF hits by configurable alignment thresholds.

    Args:
        hits: Parsed PAF records.
        cfg: Filtering thresholds.

    Returns:
        List of PAF hits passing all configured thresholds.
    """
    raise NotImplementedError


def best_hit_per_query(hits: list[PafHit]) -> dict[str, PafHit]:
    """Select one best alignment per query using deterministic tie-breaking.

    Args:
        hits: Parsed PAF records.

    Returns:
        Mapping from query ID to its best-scoring `PafHit`.
    """
    raise NotImplementedError
