"""BLAST hit parsing, filtering, and interval pruning utilities."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field, replace
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd


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


@dataclass
class BlastHit:
    """A single parsed BLAST hit from tabular output.

    Field names correspond to standard BLAST outfmt 6 fields.
    Additional fields are stored in the `extra` dictionary.
    """

    qseqid: str
    sseqid: str
    pident: float
    length: int
    mismatch: int
    gapopen: int
    qstart: int
    qend: int
    sstart: int
    send: int
    evalue: float
    bitscore: float
    qlen: int | None = None
    slen: int | None = None
    strand: str = "+"
    extra: dict[str, str] = field(default_factory=dict)


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


def _hit_field_value(hit: BlastHit, field_name: str) -> object:
    """Return field value from BlastHit across core and extra columns."""
    if hasattr(hit, field_name):
        return getattr(hit, field_name)
    return hit.extra.get(field_name)


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


def normalize_blast_strand(
    hits: list[BlastHit] | pd.DataFrame,
) -> list[BlastHit] | pd.DataFrame:
    """Normalize subject coordinates and derive strand from sstart/send.

    For hits where `sstart > send`, coordinates are swapped and strand is `-`.
    Otherwise strand is `+`.

    Returns the same container type as the input.
    """
    if isinstance(hits, list):
        normalized: list[BlastHit] = []
        for hit in hits:
            sstart_i = int(hit.sstart)
            send_i = int(hit.send)
            if sstart_i <= send_i:
                normalized.append(replace(hit, strand="+"))
            else:
                normalized.append(replace(hit, sstart=send_i, send=sstart_i, strand="-"))
        return normalized

    if "sstart" not in hits.columns or "send" not in hits.columns:
        raise ValueError("Input DataFrame must contain 'sstart' and 'send' columns.")

    work = hits.copy()
    sstart_num = pd.to_numeric(work["sstart"], errors="coerce")
    send_num = pd.to_numeric(work["send"], errors="coerce")
    comparable = sstart_num.notna() & send_num.notna()
    minus_mask = comparable & (sstart_num > send_num)

    start_norm = np.minimum(sstart_num, send_num)
    end_norm = np.maximum(sstart_num, send_num)

    work["strand"] = "+"
    work.loc[minus_mask, "strand"] = "-"
    work.loc[comparable, "sstart"] = start_norm[comparable].astype("int64")
    work.loc[comparable, "send"] = end_norm[comparable].astype("int64")
    return work


def _coverage_from_hit(hit: BlastHit, kind: str) -> float | None:
    """Extract optional coverage fields from a hit."""
    keys = ["qcov", "qcovhsp", "qcovs"] if kind == "q" else ["scov", "scovhsp", "scovs"]
    for key in keys:
        if key in hit.extra:
            try:
                return float(hit.extra[key])
            except Exception:
                continue
    return None


def filter_hits(
    hits_or_df: list[BlastHit] | pd.DataFrame,
    *,
    min_pident: float | None = None,
    min_length: int | None = None,
    max_evalue: float | None = None,
    min_bitscore: float | None = None,
    min_qcov: float | None = None,
    min_scov: float | None = None,
) -> list[BlastHit] | pd.DataFrame:
    """Filter hits using optional numeric thresholds.

    The returned type matches the input type.
    """
    if isinstance(hits_or_df, list):
        filtered: list[BlastHit] = []
        for hit in hits_or_df:
            if min_pident is not None and hit.pident < min_pident:
                continue
            if min_length is not None and hit.length < min_length:
                continue
            if max_evalue is not None and hit.evalue > max_evalue:
                continue
            if min_bitscore is not None and hit.bitscore < min_bitscore:
                continue

            qcov = _coverage_from_hit(hit, "q")
            if min_qcov is not None and (qcov is None or qcov < min_qcov):
                continue

            scov = _coverage_from_hit(hit, "s")
            if min_scov is not None and (scov is None or scov < min_scov):
                continue

            filtered.append(hit)
        return filtered

    df = hits_or_df.copy()

    if min_pident is not None and "pident" in df.columns:
        df = df[pd.to_numeric(df["pident"], errors="coerce") >= float(min_pident)]
    if min_length is not None and "length" in df.columns:
        df = df[pd.to_numeric(df["length"], errors="coerce") >= int(min_length)]
    if max_evalue is not None and "evalue" in df.columns:
        df = df[pd.to_numeric(df["evalue"], errors="coerce") <= float(max_evalue)]
    if min_bitscore is not None and "bitscore" in df.columns:
        df = df[pd.to_numeric(df["bitscore"], errors="coerce") >= float(min_bitscore)]

    if min_qcov is not None:
        candidates = ("qcov", "qcovhsp", "qcovs")
        candidate = next((name for name in candidates if name in df.columns), None)
        if candidate is None:
            raise ValueError(
                "min_qcov requires one of DataFrame columns: " + ", ".join(candidates)
            )
        df = df[pd.to_numeric(df[candidate], errors="coerce") >= float(min_qcov)]

    if min_scov is not None:
        candidates = ("scov", "scovhsp", "scovs")
        candidate = next((name for name in candidates if name in df.columns), None)
        if candidate is None:
            raise ValueError(
                "min_scov requires one of DataFrame columns: " + ", ".join(candidates)
            )
        df = df[pd.to_numeric(df[candidate], errors="coerce") >= float(min_scov)]

    return df


def select_best_hit_per_query(
    hits_or_df: list[BlastHit] | pd.DataFrame,
    *,
    metric: str = "bitscore",
    ascending: bool = False,
) -> list[BlastHit] | pd.DataFrame:
    """Select one best hit per query based on a metric column.

    Args:
        hits_or_df: Input list or DataFrame of hits.
        metric: Numeric field used for ranking within each query group.
        ascending: Whether lower values are better.

    Returns:
        One hit per query in the same container type as input.
    """
    if isinstance(hits_or_df, list):
        grouped: dict[str, list[BlastHit]] = defaultdict(list)
        for hit in hits_or_df:
            grouped[hit.qseqid].append(hit)

        selected: list[BlastHit] = []
        for query_id in sorted(grouped):
            hits = grouped[query_id]
            ranked = sorted(
                hits,
                key=lambda h: float(_hit_field_value(h, metric) or 0.0),
                reverse=not ascending,
            )
            selected.append(ranked[0])
        return selected

    df = hits_or_df.copy()
    if "qseqid" not in df.columns:
        raise ValueError("Input DataFrame must contain 'qseqid' column.")
    if metric not in df.columns:
        raise ValueError(f"Input DataFrame must contain metric column '{metric}'.")

    ranked = df.copy()
    ranked["__metric"] = pd.to_numeric(ranked[metric], errors="coerce")
    ranked = ranked.sort_values(
        by=["qseqid", "__metric"],
        ascending=[True, ascending],
        kind="mergesort",
    )
    best = ranked.drop_duplicates(subset=["qseqid"], keep="first").drop(columns=["__metric"])
    return best


def _contained_unique_intervals(starts: np.ndarray, ends: np.ndarray) -> set[tuple[int, int]]:
    """Compute unique intervals contained within a larger interval."""
    if len(starts) <= 1:
        return set()

    order = np.lexsort((-ends, starts))
    s = starts[order]
    e = ends[order]

    prune = np.zeros(len(s), dtype=bool)
    max_end = -np.inf
    max_start = -1

    for idx in range(len(s)):
        if e[idx] < max_end:
            prune[idx] = True
        elif e[idx] == max_end:
            # Preserve identical intervals; prune only strict containment.
            if s[idx] > max_start:
                prune[idx] = True
        else:
            max_end = e[idx]
            max_start = s[idx]

    return set(zip(s[prune].tolist(), e[prune].tolist()))


def prune_contained_intervals(
    df: pd.DataFrame,
    *,
    group_col: str = "qseqid",
    start_col: str = "qstart",
    end_col: str = "qend",
) -> tuple[pd.DataFrame, dict[str, int]]:
    """Remove contained intervals inside each query group.

    Args:
        df: Input DataFrame.
        group_col: Column used for grouping independent interval sets.
        start_col: Interval start column.
        end_col: Interval end column.

    Returns:
        Tuple of `(pruned_dataframe, removed_counts_by_group)`.
    """
    if df.empty:
        return df.copy(), {}

    required = {group_col, start_col, end_col}
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    work = df.copy()
    start_num = pd.to_numeric(work[start_col], errors="coerce")
    end_num = pd.to_numeric(work[end_col], errors="coerce")

    work["__start"] = np.minimum(start_num, end_num)
    work["__end"] = np.maximum(start_num, end_num)
    work["__has_coords"] = work["__start"].notna() & work["__end"].notna()

    keep_mask = pd.Series(False, index=work.index)
    removed_by_group: dict[str, int] = {}

    for group_value, group in work.groupby(group_col, sort=False):
        with_coords = group[group["__has_coords"]]
        without_coords = group[~group["__has_coords"]]

        keep_mask.loc[without_coords.index] = True
        if with_coords.empty:
            removed_by_group[str(group_value)] = 0
            continue

        uniq = with_coords[["__start", "__end"]].drop_duplicates()
        starts = uniq["__start"].to_numpy(dtype=np.int64)
        ends = uniq["__end"].to_numpy(dtype=np.int64)
        prune_set = _contained_unique_intervals(starts, ends)

        kept_indices: list[int] = []
        removed_count = 0

        for idx, row in with_coords.iterrows():
            interval = (int(row["__start"]), int(row["__end"]))
            if interval in prune_set:
                removed_count += 1
                continue
            kept_indices.append(idx)

        keep_mask.loc[kept_indices] = True
        removed_by_group[str(group_value)] = removed_count

    pruned = work.loc[keep_mask].drop(columns=["__start", "__end", "__has_coords"])
    pruned = pruned.sort_index()
    return pruned, removed_by_group


def merge_blast_hits_to_regions(
    df: pd.DataFrame,
    *,
    group_col: str = "qseqid",
    start_col: str = "qstart",
    end_col: str = "qend",
    max_gap_bp: int = 0,
    representative_by: str = "bitscore",
    representative_tiebreak: str = "evalue",
    payload_cols: list[str] | None = None,
) -> tuple[pd.DataFrame, pd.Series]:
    """Collapse BLAST hits into merged regions within each query group.

    Args:
        df: Input DataFrame of BLAST hits.
        group_col: Column used for grouping independent interval sets.
        start_col: Interval start column.
        end_col: Interval end column.
        max_gap_bp: Maximum uncovered gap allowed between neighboring hits.
        representative_by: Column used to select the representative hit by maximum value.
        representative_tiebreak: Column used to break representative ties by minimum value.
        payload_cols: Additional representative-hit columns copied to the region output.
            When `None`, all non-coordinate columns are carried.

    Returns:
        Tuple of `(regions_df, hit_to_region_id)`, where `regions_df` contains one
        row per merged region and `hit_to_region_id` maps each input hit index to
        its assigned region identifier.

    Raises:
        KeyError: If a required input column is missing.
        ValueError: If `max_gap_bp` is negative or any row has `start_col > end_col`.

    Example:
        >>> df = pd.DataFrame(
        ...     [
        ...         {"qseqid": "host_scaffold_1", "qstart": 100, "qend": 250, "bitscore": 80.0, "evalue": 1e-8},
        ...         {"qseqid": "host_scaffold_1", "qstart": 401, "qend": 520, "bitscore": 95.0, "evalue": 1e-12},
        ...     ]
        ... )
        >>> regions, hit_to_region = merge_blast_hits_to_regions(df, max_gap_bp=200)
        >>> regions[["region_start", "region_end", "n_collapsed_hits"]].to_dict("records")
        [{'region_start': 100, 'region_end': 520, 'n_collapsed_hits': 2}]
    """
    if max_gap_bp < 0:
        raise ValueError("max_gap_bp must be >= 0.")

    required = [group_col, start_col, end_col, representative_by, representative_tiebreak]
    for col in required:
        if col not in df.columns:
            raise KeyError(f"Missing required column: {col}")

    invalid_mask = df[start_col] > df[end_col]
    if invalid_mask.any():
        bad_index = df.index[invalid_mask][0]
        raise ValueError(f"{start_col} > {end_col} for row index {bad_index}")

    if payload_cols is None:
        payload_columns = [col for col in df.columns if col not in {group_col, start_col, end_col}]
    else:
        payload_columns = list(payload_cols)
        for col in payload_columns:
            if col not in df.columns:
                raise KeyError(f"Missing required column: {col}")

    region_columns = [
        "region_id",
        group_col,
        "region_start",
        "region_end",
        "region_length",
        "n_collapsed_hits",
        *payload_columns,
    ]

    if df.empty:
        empty_regions = pd.DataFrame(columns=region_columns)
        empty_mapping = pd.Series(index=df.index, dtype="int64", name="region_id")
        return empty_regions, empty_mapping

    work = df.copy()
    work["__original_index"] = work.index
    work["__input_pos"] = np.arange(len(work), dtype=np.int64)
    work = work.sort_values(
        by=[group_col, start_col, end_col, "__original_index"],
        kind="mergesort",
    ).set_index("__input_pos", drop=False)

    committed_regions: list[tuple[object, int, int, list[int]]] = []

    for group_value, group in work.groupby(group_col, sort=False):
        open_start: int | None = None
        open_end: int | None = None
        member_positions: list[int] = []

        for hit_start, hit_end, input_pos in group[[start_col, end_col, "__input_pos"]].itertuples(index=False, name=None):
            hit_start = int(hit_start)
            hit_end = int(hit_end)
            input_pos = int(input_pos)

            if open_start is None:
                open_start = hit_start
                open_end = hit_end
                member_positions = [input_pos]
                continue

            assert open_end is not None
            if hit_start <= open_end + int(max_gap_bp) + 1:
                open_end = max(open_end, hit_end)
                member_positions.append(input_pos)
                continue

            committed_regions.append((group_value, open_start, open_end, member_positions))
            open_start = hit_start
            open_end = hit_end
            member_positions = [input_pos]

        if open_start is not None and open_end is not None:
            committed_regions.append((group_value, open_start, open_end, member_positions))

    region_rows: list[dict[str, object]] = []
    region_assignments = pd.Series(index=work["__input_pos"], dtype="int64", name="region_id")
    representative_ranks = None
    if len(committed_regions) > 1 and work.columns.is_unique and all(
        isinstance(work[column].dtype, np.dtype) and work[column].dtype.kind in "biuf"
        for column in (representative_by, representative_tiebreak)
    ):
        ranked_positions = work.sort_values(
            by=[representative_by, representative_tiebreak, "__original_index"],
            ascending=[False, True, True],
            kind="mergesort",
        ).index.to_numpy()
        representative_ranks = np.empty(len(work), dtype=np.intp)
        representative_ranks[ranked_positions] = np.arange(len(work), dtype=np.intp)

    for region_id, (group_value, region_start, region_end, member_positions) in enumerate(committed_regions, start=1):
        if representative_ranks is None:
            region_hits = work.loc[member_positions]
            representative = region_hits.sort_values(
                by=[representative_by, representative_tiebreak, "__original_index"],
                ascending=[False, True, True],
                kind="mergesort",
            ).iloc[0]
        else:
            representative_position = min(member_positions, key=representative_ranks.__getitem__)
            representative = work.loc[[representative_position]].iloc[0]

        region_row: dict[str, object] = {
            "region_id": region_id,
            group_col: group_value,
            "region_start": int(region_start),
            "region_end": int(region_end),
            "region_length": int(region_end - region_start + 1),
            "n_collapsed_hits": len(member_positions),
        }
        for col in payload_columns:
            region_row[col] = representative[col]

        region_rows.append(region_row)
        region_assignments.loc[member_positions] = region_id

    regions_df = pd.DataFrame(region_rows, columns=region_columns)
    hit_to_region_id = region_assignments.sort_index()
    hit_to_region_id.index = df.index
    return regions_df, hit_to_region_id


def filter_hits_by_bitscore_fraction(
    df: pd.DataFrame,
    *,
    bitscore_col: str = "bitscore",
    query_col: str = "qseqid",
    top_fraction: float = 0.9,
) -> pd.DataFrame:
    """Keep hits within a fraction of per-query maximum bitscore."""
    if bitscore_col not in df.columns or query_col not in df.columns:
        raise ValueError(f"DataFrame must contain '{query_col}' and '{bitscore_col}' columns.")

    if not (0 < float(top_fraction) <= 1):
        raise ValueError("top_fraction must be within (0, 1].")

    work = df.copy()
    work["__bitscore"] = pd.to_numeric(work[bitscore_col], errors="coerce")
    work = work[work["__bitscore"].notna()].copy()
    if work.empty:
        return work.drop(columns=["__bitscore"])

    top_by_query = work.groupby(query_col)["__bitscore"].transform("max")
    threshold = top_by_query * float(top_fraction)
    filtered = work[work["__bitscore"] >= threshold].copy()
    return filtered.drop(columns=["__bitscore"])
