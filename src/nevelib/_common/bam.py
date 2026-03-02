"""BAM file validation and quality control.

Called by the reads module before read extraction.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BamValidationResult:
    """Result of BAM validation.

    Attributes:
        valid: Whether the file passed all checks.
        path: Path to the validated file.
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected.
        is_sorted: Whether the BAM is coordinate-sorted.
        has_index: Whether a .bai index was found.
        is_truncated: Whether samtools quickcheck detected truncation.
    """

    valid: bool
    path: Path
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    is_sorted: bool = False
    has_index: bool = False
    is_truncated: bool = False


def validate_bam(
    path: Path,
    *,
    require_sorted: bool = True,
    require_index: bool = True,
    run_quickcheck: bool = True,
) -> BamValidationResult:
    """Validate a BAM file.

    Args:
        path: Path to the BAM file.
        require_sorted: Fail if BAM is not coordinate-sorted.
        require_index: Fail if .bai index is not found.
        run_quickcheck: Run samtools quickcheck for truncation detection.

    Returns:
        BamValidationResult with validation outcome.
    """
    raise NotImplementedError
