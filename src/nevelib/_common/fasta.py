"""FASTA file validation, quality control, and shared I/O utilities.

Called by any module that reads or writes FASTA files.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator


@dataclass
class FastaValidationResult:
    """Result of FASTA validation.

    Attributes:
        valid: Whether the file passed all checks.
        path: Path to the validated file.
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected.
        record_count: Number of records (None if not counted).
        has_index: Whether a .fai index was found or generated.
        alphabet: Detected alphabet ('dna', 'protein', or None).
    """

    valid: bool
    path: Path
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    record_count: int | None = None
    has_index: bool = False
    alphabet: str | None = None


@dataclass
class FastaQCReport:
    """Quality control summary for a FASTA file.

    Attributes:
        path: Path to the FASTA file.
        record_count: Number of sequences.
        total_bases: Total number of bases across all sequences.
        n50: N50 length in bases.
        mean_length: Mean sequence length.
        min_length: Length of the shortest sequence.
        max_length: Length of the longest sequence.
        gc_fraction: GC content as a fraction.
        length_thresholds: Count of sequences exceeding standard thresholds.
    """

    path: Path
    record_count: int = 0
    total_bases: int = 0
    n50: int = 0
    mean_length: float = 0.0
    min_length: int = 0
    max_length: int = 0
    gc_fraction: float = 0.0
    length_thresholds: dict[int, int] = field(default_factory=dict)


def validate_fasta(
    path: Path,
    *,
    check_nonempty: bool = True,
    min_records: int = 1,
    check_duplicates: bool = True,
    check_alphabet: bool = False,
    expected_alphabet: str | None = None,
    require_index: bool = False,
    create_index: bool = False,
) -> FastaValidationResult:
    """Validate a FASTA file.

    Args:
        path: Path to the FASTA file.
        check_nonempty: Verify the file contains at least min_records.
        min_records: Minimum number of records required.
        check_duplicates: Check for duplicate sequence IDs.
        check_alphabet: Detect the sequence alphabet.
        expected_alphabet: If set, verify alphabet matches ('dna' or 'protein').
        require_index: Fail if .fai index does not exist.
        create_index: Create .fai index if missing (requires pyfaidx or samtools).

    Returns:
        FastaValidationResult with validation outcome.
    """
    raise NotImplementedError


def qc_fasta(
    path: Path,
    *,
    length_thresholds: tuple[int, ...] = (250, 500, 1000, 2000, 5000, 10000),
) -> FastaQCReport:
    """Compute quality control statistics for a FASTA file.

    Args:
        path: Path to the FASTA file.
        length_thresholds: Sequence length thresholds for counting.

    Returns:
        FastaQCReport with computed statistics.
    """
    raise NotImplementedError


def iter_fasta_records(path: Path) -> Iterator[tuple[str, str]]:
    """Iterate over FASTA records yielding (id, sequence) tuples.

    Args:
        path: Path to the FASTA file.

    Yields:
        Tuples of (record_id, sequence_string).
    """
    raise NotImplementedError


def write_fasta(
    records: Iterator[tuple[str, str]],
    path: Path,
    *,
    wrap_width: int = 80,
) -> int:
    """Write FASTA records to a file.

    Args:
        records: Iterator of (record_id, sequence_string) tuples.
        path: Output file path.
        wrap_width: Line width for sequence wrapping (0 for no wrap).

    Returns:
        Number of records written.
    """
    raise NotImplementedError
