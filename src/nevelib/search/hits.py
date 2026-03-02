"""BLAST hit parsing, filtering, and overlap pruning interfaces.

This module exposes structured operations for loading BLAST tabular output,
applying configurable filters, and removing fully contained intervals.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd


@dataclass
class HitFilterConfig:
    """Configuration for BLAST hit filtering.

    Attributes:
        min_len: Minimum aligned length to keep a hit.
        min_overlap_frac: Minimum overlap fraction for region collapsing.
        min_bitscore_top_frac: Fraction of top bitscore retained per query.
    """

    min_len: int = 80
    min_overlap_frac: float = 0.8
    min_bitscore_top_frac: float = 0.9


def parse_blast_tabular(path: Path, cfg: HitFilterConfig) -> pd.DataFrame:
    """Parse BLAST tabular output into a normalized DataFrame.

    Args:
        path: BLAST output file path (outfmt 6/10 style columns).
        cfg: Parsing/filter context including expected thresholds.

    Returns:
        DataFrame containing normalized hit records.

    Side Effects:
        None; this function reads and parses input only.
    """
    raise NotImplementedError


def filter_hits(df: pd.DataFrame, cfg: HitFilterConfig) -> pd.DataFrame:
    """Apply configured thresholds to BLAST hits.

    Args:
        df: Input hit table.
        cfg: Hit filtering thresholds.

    Returns:
        Filtered DataFrame of retained hits.
    """
    raise NotImplementedError


def prune_contained_intervals(df: pd.DataFrame) -> pd.DataFrame:
    """Remove intervals fully contained in larger intervals per group.

    Args:
        df: Hit table containing normalized start/end coordinates.

    Returns:
        DataFrame with contained intervals removed while preserving stable order.
    """
    raise NotImplementedError
