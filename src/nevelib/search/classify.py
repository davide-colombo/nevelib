"""Taxonomy-based hit classification interfaces.

This module defines the public API for classifying parsed BLAST hits into
viral/non-viral/uninformative categories.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class TaxonomyClassificationConfig:
    """Configuration for taxonomy-based classification.

    Attributes:
        rule: Classification rule (`any_hit_viral` or `top_hit_viral`).
        viral_keyword_fallback_enabled: Enable title-based fallback classification.
    """

    rule: str = "top_hit_viral"
    viral_keyword_fallback_enabled: bool = True


def classify_hits_by_taxonomy(
    hits_df: pd.DataFrame,
    cfg: TaxonomyClassificationConfig,
) -> pd.DataFrame:
    """Classify BLAST hits using taxonomy fields and fallback heuristics.

    Args:
        hits_df: DataFrame of BLAST hit records with taxonomy annotations.
        cfg: Classification policy and fallback controls.

    Returns:
        DataFrame with classification columns appended.

    Side Effects:
        None; classification is computed from in-memory hit data.
    """
    raise NotImplementedError
