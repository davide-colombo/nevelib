"""BLAST database validation.

Called by the search module before running BLAST queries.
"""

from __future__ import annotations

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


def _has_all(paths: list[Path]) -> bool:
    """Return True when all paths exist."""
    return all(path.exists() for path in paths)


def _glob_any(base: Path, pattern: str) -> bool:
    """Return True when glob pattern matches at least one file."""
    return any(base.parent.glob(pattern))


def _validate_nucleotide_prefix(prefix: Path) -> bool:
    """Validate nucleotide database indicators for BLAST+ variants."""
    p = str(prefix)
    nin = Path(f"{p}.nin")
    nsq = Path(f"{p}.nsq")
    nhr = Path(f"{p}.nhr")
    ndb = Path(f"{p}.ndb")
    nal = Path(f"{p}.nal")

    # Legacy single-volume indicators.
    legacy = _has_all([nhr, nin, nsq])
    # Modern BLAST+ layouts may include .ndb and still expose .nin/.nsq.
    modern_v5 = _has_all([nin, nsq]) and (ndb.exists() or nhr.exists())
    # Multi-volume indicators use numbered sidecars and often a .nal alias.
    multivol = (
        _glob_any(prefix, f"{prefix.name}.[0-9][0-9].nin")
        and _glob_any(prefix, f"{prefix.name}.[0-9][0-9].nsq")
    )
    alias = nal.exists()

    return legacy or modern_v5 or multivol or (alias and multivol)


def _validate_protein_prefix(prefix: Path) -> bool:
    """Validate protein database indicators for BLAST+ variants."""
    p = str(prefix)
    pin = Path(f"{p}.pin")
    psq = Path(f"{p}.psq")
    phr = Path(f"{p}.phr")
    pdb = Path(f"{p}.pdb")
    pal = Path(f"{p}.pal")

    legacy = _has_all([phr, pin, psq])
    modern_v5 = _has_all([pin, psq]) and (pdb.exists() or phr.exists())
    multivol = (
        _glob_any(prefix, f"{prefix.name}.[0-9][0-9].pin")
        and _glob_any(prefix, f"{prefix.name}.[0-9][0-9].psq")
    )
    alias = pal.exists()

    return legacy or modern_v5 or multivol or (alias and multivol)


def validate_blast_db(
    prefix: Path,
    *,
    db_type: str = "nucl",
    require_taxonomy: bool = False,
) -> BlastDbValidationResult:
    """Validate a BLAST database prefix.

    Checks that expected sidecar files (.nhr, .nin, .nsq for nucleotide;
    .phr, .pin, .psq for protein) exist. Optionally checks for taxonomy
    files (taxdb.bti + taxdb.btd or taxonomy4blast.sqlite3).

    Args:
        prefix: BLAST database prefix path.
        db_type: 'nucl' for nucleotide or 'prot' for protein.
        require_taxonomy: Fail if taxonomy sidecar files are missing.

    Returns:
        BlastDbValidationResult with validation outcome.
    """
    resolved_prefix = prefix.expanduser()
    result = BlastDbValidationResult(valid=True, prefix=resolved_prefix, db_type=db_type)

    db_type_norm = db_type.strip().lower()
    if db_type_norm not in {"nucl", "prot"}:
        result.valid = False
        result.errors.append(f"Unsupported BLAST database type: {db_type}")
        return result

    has_db = (
        _validate_nucleotide_prefix(resolved_prefix)
        if db_type_norm == "nucl"
        else _validate_protein_prefix(resolved_prefix)
    )

    if not has_db:
        result.valid = False
        if db_type_norm == "nucl":
            result.errors.append(
                "BLAST nucleotide database files not found for prefix "
                f"{resolved_prefix} (expected .nin/.nsq/.nhr, .ndb, .nal, or multi-volume files)."
            )
        else:
            result.errors.append(
                "BLAST protein database files not found for prefix "
                f"{resolved_prefix} (expected .pin/.psq/.phr, .pdb, .pal, or multi-volume files)."
            )

    db_dir = resolved_prefix.parent
    taxonomy_sqlite = db_dir / "taxonomy4blast.sqlite3"
    taxonomy_pair = (db_dir / "taxdb.bti").exists() and (db_dir / "taxdb.btd").exists()
    result.has_taxonomy = taxonomy_sqlite.exists() or taxonomy_pair

    if require_taxonomy and not result.has_taxonomy:
        result.valid = False
        result.errors.append(
            "BLAST taxonomy sidecar not found. Expected taxonomy4blast.sqlite3 "
            "or taxdb.bti + taxdb.btd in the database directory."
        )

    return result
