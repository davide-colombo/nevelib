"""BAM file validation and basic integrity checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from nevelib._common.toolrun import check_tool, run_tool


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


def _resolve_bai_candidates(path: Path) -> tuple[Path, Path]:
    """Return supported BAM index path candidates."""
    return path.with_suffix(path.suffix + ".bai"), path.with_suffix(".bai")


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
    result = BamValidationResult(valid=True, path=path)

    if not path.exists():
        result.valid = False
        result.errors.append(f"BAM file not found: {path}")
        return result

    if not path.is_file():
        result.valid = False
        result.errors.append(f"BAM path is not a regular file: {path}")
        return result

    bai_a, bai_b = _resolve_bai_candidates(path)
    result.has_index = bai_a.exists() or bai_b.exists()
    if require_index and not result.has_index:
        result.valid = False
        result.errors.append(f"Missing BAM index (.bai): expected {bai_a} or {bai_b}")

    samtools = check_tool("samtools", version_args=["--version"])

    if require_sorted:
        if samtools.available:
            proc = run_tool(["samtools", "view", "-H", str(path)], check=False)
            if proc.returncode != 0:
                result.valid = False
                err = (proc.stderr or "").strip()
                result.errors.append(f"samtools view -H failed for {path}: {err or 'unknown error'}")
            else:
                header = proc.stdout or ""
                sort_order: str | None = None
                for line in header.splitlines():
                    if not line.startswith("@HD"):
                        continue
                    for field in line.split("\t"):
                        if field.startswith("SO:"):
                            sort_order = field.split(":", 1)[1].strip()
                            break
                    if sort_order is not None:
                        break
                result.is_sorted = sort_order == "coordinate"
                if not result.is_sorted:
                    result.valid = False
                    result.errors.append(
                        "BAM sort order is not coordinate (missing or non-coordinate @HD SO tag)."
                    )
        else:
            result.warnings.append(
                "samtools not available: skipping BAM header sort-order check and assuming coordinate-sorted."
            )
            result.is_sorted = True
    else:
        result.is_sorted = True

    if run_quickcheck:
        if samtools.available:
            proc = run_tool(["samtools", "quickcheck", str(path)], check=False)
            if proc.returncode != 0:
                result.is_truncated = True
                result.valid = False
                err = (proc.stderr or "").strip()
                result.errors.append(
                    f"samtools quickcheck failed for {path}: {err or 'quickcheck reported an error'}"
                )
        else:
            result.warnings.append("samtools not available: skipping BAM quickcheck integrity test.")

    if result.errors:
        result.valid = False

    return result
