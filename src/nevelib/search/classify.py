"""Taxonomy-driven classification helpers for parsed BLAST hits."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


@dataclass
class ClassificationResult:
    """Classification outcome for one query.

    Attributes:
        query_id: Query identifier.
        classification: Tri-state result: 'positive', 'negative', or 'ambiguous'.
        reason: Human-readable explanation of the classification.
        top_hit_taxon: Taxonomy value of the top hit when available.
        keyword_match: Whether classification used keyword fallback matching.
    """

    query_id: str
    classification: str
    reason: str = ""
    top_hit_taxon: str | None = None
    keyword_match: bool = False


def is_missing_taxonomy(value: object) -> bool:
    """Return True when taxonomy value is empty or placeholder-like."""
    if value is None:
        return True

    text = str(value).strip()
    if not text:
        return True

    tokens = [token.strip() for token in text.split(";")]
    if not tokens:
        return True

    for token in tokens:
        if not token:
            continue
        normalized = token.lower()
        if normalized in {"n/a", "na", "none", "null", ".", "-", "nan", "unclassified"}:
            continue
        return False
    return True


def matches_keywords(text: str, keywords: list[str]) -> bool:
    """Case-insensitive keyword match against free-text content."""
    haystack = (text or "").lower()
    return any(keyword.lower() in haystack for keyword in keywords if keyword)


def classify_hits_by_taxonomy(
    hits_df: pd.DataFrame,
    *,
    taxonomy_col: str,
    rule: str = "majority",
    keywords: list[str] | None = None,
    keyword_fallback: bool = False,
) -> list[ClassificationResult]:
    """Classify grouped hits using taxonomy and optional keyword fallback.

    Args:
        hits_df: BLAST hits as a DataFrame containing query and taxonomy columns.
        taxonomy_col: Taxonomy column name.
        rule: Aggregation rule: 'majority', 'any', or 'all'.
        keywords: Positive-class keywords matched against taxonomy/title values.
        keyword_fallback: Use title keyword matching when taxonomy is missing.

    Returns:
        One ClassificationResult per query.
    """
    if hits_df.empty:
        return []

    if "qseqid" not in hits_df.columns:
        raise ValueError("hits_df must contain 'qseqid' column.")
    if taxonomy_col not in hits_df.columns:
        raise ValueError(f"hits_df must contain taxonomy column '{taxonomy_col}'.")

    rule_norm = (rule or "majority").strip().lower()
    if rule_norm not in {"majority", "any", "all"}:
        raise ValueError("rule must be one of: 'majority', 'any', 'all'.")

    keywords_list = keywords or []
    results: list[ClassificationResult] = []

    grouped = hits_df.groupby("qseqid", sort=False)
    for query_id, group in grouped:
        informative = group[~group[taxonomy_col].apply(is_missing_taxonomy)]

        top_taxon: str | None = None
        if not informative.empty:
            top_taxon = str(informative.iloc[0][taxonomy_col])

        if informative.empty:
            if keyword_fallback and "stitle" in group.columns:
                has_keyword = any(matches_keywords(str(value), keywords_list) for value in group["stitle"].tolist())
                if has_keyword:
                    results.append(
                        ClassificationResult(
                            query_id=str(query_id),
                            classification="positive",
                            reason="keyword_fallback_match",
                            top_hit_taxon=None,
                            keyword_match=True,
                        )
                    )
                else:
                    results.append(
                        ClassificationResult(
                            query_id=str(query_id),
                            classification="ambiguous",
                            reason="missing_taxonomy_and_no_keyword_match",
                            top_hit_taxon=None,
                            keyword_match=False,
                        )
                    )
            else:
                results.append(
                    ClassificationResult(
                        query_id=str(query_id),
                        classification="ambiguous",
                        reason="missing_taxonomy",
                        top_hit_taxon=None,
                        keyword_match=False,
                    )
                )
            continue

        votes = [matches_keywords(str(value), keywords_list) for value in informative[taxonomy_col].tolist()]

        if rule_norm == "any":
            is_positive = any(votes)
            classification = "positive" if is_positive else "negative"
            reason = "any_keyword_match" if is_positive else "no_keyword_match"
        elif rule_norm == "all":
            is_positive = all(votes)
            classification = "positive" if is_positive else "negative"
            reason = "all_keyword_match" if is_positive else "not_all_keyword_match"
        else:
            positives = sum(1 for vote in votes if vote)
            negatives = len(votes) - positives
            if positives > negatives:
                classification = "positive"
                reason = "majority_positive"
            elif negatives > positives:
                classification = "negative"
                reason = "majority_negative"
            else:
                classification = "ambiguous"
                reason = "majority_tie"

        results.append(
            ClassificationResult(
                query_id=str(query_id),
                classification=classification,
                reason=reason,
                top_hit_taxon=top_taxon,
                keyword_match=False,
            )
        )

    return results
