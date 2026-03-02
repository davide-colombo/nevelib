"""Tabular file (TSV/CSV) validation.

Called by any module that reads or writes structured tabular output.
"""

from __future__ import annotations

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
    result = TsvValidationResult(valid=True, path=path)

    if not path.exists():
        result.valid = False
        result.errors.append(f"Tabular file not found: {path}")
        return result

    if not path.is_file():
        result.valid = False
        result.errors.append(f"Tabular path is not a regular file: {path}")
        return result

    with path.open("r", encoding="utf-8") as handle:
        header = handle.readline()
        if not header:
            result.valid = False
            result.errors.append("Tabular file is empty (missing header).")
            return result

        result.column_names = [col.strip() for col in header.rstrip("\n\r").split(delimiter)]

        if required_columns:
            missing = [col for col in required_columns if col not in result.column_names]
            if missing:
                result.valid = False
                result.errors.append(
                    "Missing required columns: " + ", ".join(missing)
                )

        row_count = 0
        for line in handle:
            if line.strip():
                row_count += 1
        result.row_count = row_count

    if check_nonempty and result.row_count < min_rows:
        result.valid = False
        result.errors.append(
            f"Tabular file has {result.row_count} data row(s); minimum required is {min_rows}."
        )

    return result
