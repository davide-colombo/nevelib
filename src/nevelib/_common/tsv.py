"""Tabular file (TSV/CSV) validation.

Called by any module that reads or writes structured tabular output.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TsvValidationResult:
    """Result of TSV/CSV validation.

    Attributes:
        valid: Whether the file passed all checks.
        path: Path to the validated file.
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected.
        column_names: Detected column names from header.
        row_count: Number of data rows (excluding header).
    """

    valid: bool
    path: Path
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    column_names: list[str] = field(default_factory=list)
    row_count: int = 0


def validate_tsv(
    path: Path,
    *,
    required_columns: list[str] | None = None,
    delimiter: str = "\t",
    check_nonempty: bool = True,
    min_rows: int = 1,
) -> TsvValidationResult:
    """Validate a TSV or CSV file.

    Args:
        path: Path to the tabular file.
        required_columns: Column names that must be present in the header.
        delimiter: Column delimiter character.
        check_nonempty: Verify the file has at least min_rows data rows.
        min_rows: Minimum number of data rows required.

    Returns:
        TsvValidationResult with validation outcome.
    """
    raise NotImplementedError
