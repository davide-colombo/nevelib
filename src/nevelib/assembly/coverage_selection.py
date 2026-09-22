"""In-memory coverage eligibility and per-contig measurement facts."""

from __future__ import annotations

from collections.abc import Iterator


def coverage_is_unmapped(
    records: list[tuple[str, str]],
    coverage: dict[str, tuple[int, int, float]],
) -> bool:
    return (not coverage) or all(
        coverage.get(rec_id, (0, 0, 0.0))[2] <= 0.0 for rec_id, _seq in records
    )


def _passes_mean_coverage(mean_coverage: float, threshold: float, force_pass: bool = False) -> bool:
    return True if force_pass else (mean_coverage >= float(threshold))


def select_covered_records(
    records: list[tuple[str, str]],
    coverage: dict[str, tuple[int, int, float]],
    min_mean_coverage: float,
) -> list[tuple[str, str]]:
    return [
        (rec_id, seq)
        for rec_id, seq in records
        if _passes_mean_coverage(coverage.get(rec_id, (0, 0, 0.0))[2], min_mean_coverage)
    ]


def coverage_rows(
    records: list[tuple[str, str]],
    coverage: dict[str, tuple[int, int, float]] | None,
    *,
    min_mean_coverage: float,
    force_pass: bool = False,
) -> Iterator[tuple[str, int, int, float, bool]]:
    for rec_id, seq in records:
        if coverage is None:
            length, bases, mean_cov = len(seq), 0, 0.0
        else:
            length, bases, mean_cov = coverage.get(rec_id, (len(seq), 0, 0.0))
        passed = _passes_mean_coverage(mean_cov, min_mean_coverage, force_pass)
        yield rec_id, length, bases, mean_cov, passed
