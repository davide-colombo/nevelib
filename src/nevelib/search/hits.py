"""BLAST hit parsing, filtering, and interval pruning utilities."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .hit_calculations import (
    BlastHit,
    _hit_field_value,
    normalize_blast_strand,
    _coverage_from_hit,
    filter_hits,
    select_best_hit_per_query,
    _contained_unique_intervals,
    prune_contained_intervals,
    merge_blast_hits_to_regions,
    filter_hits_by_bitscore_fraction,
)


LOGGER = logging.getLogger(__name__)


DEFAULT_FIELDS: list[str] = [
    "qseqid",
    "sseqid",
    "pident",
    "length",
    "mismatch",
    "gapopen",
    "qstart",
    "qend",
    "sstart",
    "send",
    "evalue",
    "bitscore",
    "qlen",
    "slen",
]


def _parse_int(raw: str | None, default: int = 0) -> int:
    """Parse an integer from text with a fallback default."""
    if raw is None:
        return default
    try:
        return int(float(str(raw).strip()))
    except Exception:
        return default


def _parse_opt_int(raw: str | None) -> int | None:
    """Parse an optional integer from text."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except Exception:
        return None


def _parse_float(raw: str | None, default: float = 0.0) -> float:
    """Parse a float from text with a fallback default."""
    if raw is None:
        return default
    try:
        return float(str(raw).strip())
    except Exception:
        return default


def parse_blast_tabular(
    path: Path,
    *,
    fields: list[str] | None = None,
    delimiter: str = "\t",
) -> list[BlastHit]:
    """Parse tabular BLAST output into BlastHit objects.

    Args:
        path: Path to BLAST output.
        fields: Column names expected in each row. Defaults to 14 standard fields.
        delimiter: Field delimiter (tab for outfmt 6, comma for outfmt 10).

    Returns:
        Parsed list of BlastHit entries.
    """
    if not path.exists():
        raise FileNotFoundError(path)

    active_fields = fields or DEFAULT_FIELDS
    hits: list[BlastHit] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            parts = line.split(delimiter)
            if len(parts) < len(active_fields):
                LOGGER.warning(
                    "Skipping truncated BLAST row at %s:%d (got %d columns, expected %d).",
                    path,
                    line_no,
                    len(parts),
                    len(active_fields),
                )
                continue

            row_map = {name: parts[idx] for idx, name in enumerate(active_fields)}
            extra: dict[str, str] = {}

            # Preserve unknown mapped columns in `extra`.
            for key in active_fields:
                if key not in {
                    "qseqid",
                    "sseqid",
                    "pident",
                    "length",
                    "mismatch",
                    "gapopen",
                    "qstart",
                    "qend",
                    "sstart",
                    "send",
                    "evalue",
                    "bitscore",
                    "qlen",
                    "slen",
                }:
                    extra[key] = row_map[key]

            # Preserve additional trailing columns when present.
            if len(parts) > len(active_fields):
                for idx in range(len(active_fields), len(parts)):
                    extra[f"col_{idx + 1}"] = parts[idx]

            try:
                hit = BlastHit(
                    qseqid=str(row_map.get("qseqid", "")).strip(),
                    sseqid=str(row_map.get("sseqid", "")).strip(),
                    pident=_parse_float(row_map.get("pident")),
                    length=_parse_int(row_map.get("length")),
                    mismatch=_parse_int(row_map.get("mismatch")),
                    gapopen=_parse_int(row_map.get("gapopen")),
                    qstart=_parse_int(row_map.get("qstart")),
                    qend=_parse_int(row_map.get("qend")),
                    sstart=_parse_int(row_map.get("sstart")),
                    send=_parse_int(row_map.get("send")),
                    evalue=_parse_float(row_map.get("evalue")),
                    bitscore=_parse_float(row_map.get("bitscore")),
                    qlen=_parse_opt_int(row_map.get("qlen")),
                    slen=_parse_opt_int(row_map.get("slen")),
                    extra=extra,
                )
            except Exception:
                LOGGER.warning(
                    "Skipping malformed BLAST row at %s:%d due to parse error.",
                    path,
                    line_no,
                )
                continue

            if not hit.qseqid:
                LOGGER.warning("Skipping BLAST row at %s:%d with empty qseqid.", path, line_no)
                continue
            hits.append(hit)

    return hits


def parse_blast_to_dataframe(
    path: Path,
    *,
    fields: list[str] | None = None,
    delimiter: str = "\t",
) -> pd.DataFrame:
    """Parse BLAST tabular output and return a DataFrame."""
    active_fields = fields or DEFAULT_FIELDS
    hits = parse_blast_tabular(path, fields=active_fields, delimiter=delimiter)

    rows: list[dict[str, object]] = []
    for hit in hits:
        rows.append({field_name: _hit_field_value(hit, field_name) for field_name in active_fields})

    return pd.DataFrame(rows, columns=active_fields)
