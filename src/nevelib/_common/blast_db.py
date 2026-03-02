"""BLAST database validation.

Called by the search module before running BLAST queries.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class BlastDbValidationResult:
    """Result of BLAST database validation.

    Attributes:
        valid: Whether the database passed all checks.
        prefix: Database prefix path.
        db_type: Database type ('nucl' or 'prot').
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected.
        has_taxonomy: Whether taxonomy sidecar files are present.
    """

    valid: bool
    prefix: Path
    db_type: str = "nucl"
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    has_taxonomy: bool = False


def validate_blast_db(
    prefix: Path,
    *,
    db_type: str = "nucl",
    require_taxonomy: bool = False,
) -> BlastDbValidationResult:
    """Validate a BLAST database prefix.

    Checks that expected sidecar files (.nhr, .nin, .nsq for nucleotide;
    .phr, .pin, .psq for protein) exist.  Optionally checks for taxonomy
    files (taxdb.bti + taxdb.btd or taxonomy4blast.sqlite3).

    Args:
        prefix: BLAST database prefix path.
        db_type: 'nucl' for nucleotide or 'prot' for protein.
        require_taxonomy: Fail if taxonomy sidecar files are missing.

    Returns:
        BlastDbValidationResult with validation outcome.
    """
    raise NotImplementedError
