"""FASTA file validation and shared I/O utilities.

Called by any module that reads or writes FASTA files.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import subprocess
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


def _index_path(path: Path) -> Path:
    """Return the expected FASTA index path (`<fasta>.fai`)."""
    return Path(f"{path}.fai")


def _detect_alphabet(sequences: list[str]) -> str | None:
    """Detect a coarse sequence alphabet from parsed FASTA sequences."""
    if not sequences:
        return None
    chars = {c.upper() for seq in sequences for c in seq if not c.isspace()}
    if not chars:
        return None

    dna_chars = set("ACGTNURYKMSWBDHV-.")
    protein_chars = set("ABCDEFGHIKLMNPQRSTVWXYZ*-.UOJ")

    if chars.issubset(dna_chars):
        return "dna"
    if chars.issubset(protein_chars):
        return "protein"
    return None


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
    result = FastaValidationResult(valid=True, path=path)

    if not path.exists():
        result.valid = False
        result.errors.append(f"FASTA file not found: {path}")
        return result

    if not path.is_file():
        result.valid = False
        result.errors.append(f"FASTA path is not a regular file: {path}")
        return result

    fai_path = _index_path(path)
    result.has_index = fai_path.exists()

    record_ids: list[str] = []
    sequences: list[str] = []
    try:
        for record_id, sequence in iter_fasta_records(path):
            record_ids.append(record_id)
            if check_alphabet or expected_alphabet is not None:
                sequences.append(sequence)
    except ValueError as exc:
        result.valid = False
        result.errors.append(str(exc))
        return result

    result.record_count = len(record_ids)

    if check_nonempty and result.record_count < min_records:
        result.valid = False
        result.errors.append(
            f"FASTA contains {result.record_count} record(s); minimum required is {min_records}."
        )

    if check_duplicates and record_ids:
        seen: set[str] = set()
        duplicates: set[str] = set()
        for rec_id in record_ids:
            if rec_id in seen:
                duplicates.add(rec_id)
            else:
                seen.add(rec_id)
        if duplicates:
            dup_list = ", ".join(sorted(duplicates))
            result.warnings.append(f"Duplicate FASTA IDs detected: {dup_list}")

    if create_index and not result.has_index:
        index_created = False
        try:
            from pyfaidx import Faidx  # type: ignore

            Faidx(str(path), build_index=True)
            index_created = True
        except Exception:
            samtools = shutil.which("samtools")
            if samtools:
                try:
                    subprocess.run(
                        [samtools, "faidx", str(path)],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        check=True,
                    )
                    index_created = True
                except subprocess.CalledProcessError as exc:
                    result.errors.append(
                        f"Failed to create FASTA index with samtools: {exc.stderr.strip() or exc}"
                    )
            else:
                result.errors.append(
                    "FASTA index creation requested but neither pyfaidx nor samtools is available."
                )

        result.has_index = _index_path(path).exists() or index_created

    if require_index and not result.has_index:
        result.valid = False
        result.errors.append(f"Missing FASTA index file: {_index_path(path)}")

    if check_alphabet or expected_alphabet is not None:
        detected = _detect_alphabet(sequences)
        result.alphabet = detected
        if expected_alphabet is not None:
            expected = expected_alphabet.strip().lower()
            if detected is None:
                result.warnings.append(
                    f"Could not confidently detect alphabet; expected '{expected}'."
                )
            elif detected != expected:
                result.valid = False
                result.errors.append(
                    f"Detected alphabet '{detected}' does not match expected '{expected}'."
                )

    if result.errors:
        result.valid = False

    return result


def iter_fasta_records(path: Path) -> Iterator[tuple[str, str]]:
    """Iterate over FASTA records yielding (id, sequence) tuples.

    Args:
        path: Path to the FASTA file.

    Yields:
        Tuples of (record_id, sequence_string).
    """
    if not path.exists():
        raise FileNotFoundError(path)

    current_id: str | None = None
    sequence_parts: list[str] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue

            if line.startswith(">"):
                if current_id is not None:
                    yield current_id, "".join(sequence_parts)
                header = line[1:].strip()
                if not header:
                    raise ValueError(f"Invalid FASTA header at line {line_number} in {path}.")
                current_id = header.split()[0]
                sequence_parts = []
                continue

            if current_id is None:
                raise ValueError(
                    f"Invalid FASTA content at line {line_number} in {path}: "
                    "sequence encountered before first header."
                )
            sequence_parts.append(line)

    if current_id is not None:
        yield current_id, "".join(sequence_parts)


def write_fasta(
    records: Iterator[tuple[str, str]],
    path: Path,
    *,
    wrap_width: int = 60,
) -> int:
    """Write FASTA records to a file.

    Args:
        records: Iterator of (record_id, sequence_string) tuples.
        path: Output file path.
        wrap_width: Line width for sequence wrapping (0 for no wrap).

    Returns:
        Number of records written.
    """
    if wrap_width < 0:
        raise ValueError("wrap_width must be >= 0")

    path.parent.mkdir(parents=True, exist_ok=True)

    n_written = 0
    with path.open("w", encoding="utf-8") as handle:
        for record_id, sequence in records:
            rec_id = str(record_id).strip()
            if not rec_id:
                raise ValueError("FASTA record ID must be non-empty.")

            seq = str(sequence).replace("\n", "").replace("\r", "")
            handle.write(f">{rec_id}\n")

            if wrap_width == 0:
                handle.write(f"{seq}\n")
            else:
                for start in range(0, len(seq), wrap_width):
                    handle.write(f"{seq[start:start + wrap_width]}\n")

            n_written += 1

    return n_written
