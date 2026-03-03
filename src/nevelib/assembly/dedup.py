"""Self-BLAST-based deduplication of assembled contigs."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import subprocess

from nevelib._common.fasta import iter_fasta_records, validate_fasta, write_fasta
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class DedupConfig:
    """Configuration for self-BLAST deduplication.

    Attributes:
        blastn_exec: blastn binary.
        makeblastdb_exec: makeblastdb binary.
        evalue: E-value threshold for self-BLAST.
        pident_min: Minimum percent identity for a containment hit.
        min_coverage_fraction: Minimum fraction of the shorter contig covered
            by the alignment to consider it contained.
        threads: Number of threads.
    """

    blastn_exec: str = "blastn"
    makeblastdb_exec: str = "makeblastdb"
    evalue: float = 1e-10
    pident_min: float = 95.0
    min_coverage_fraction: float = 0.95
    threads: int = 4


@dataclass
class DedupResult:
    """Result of deduplication.

    Attributes:
        output_fasta: Path to deduplicated FASTA.
        n_input: Number of input contigs.
        n_unique: Number of contigs after deduplication.
        n_removed: Number of contained contigs removed.
        removed_ids: List of IDs of removed contigs.
    """

    output_fasta: Path
    n_input: int = 0
    n_unique: int = 0
    n_removed: int = 0
    removed_ids: list[str] = field(default_factory=list)


def _extract_stderr(exc: subprocess.CalledProcessError) -> str:
    """Extract stderr text from CalledProcessError."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return (stderr or "").strip()


def _parse_self_blast_tsv(path: Path) -> list[tuple[str, str, float, int, int, int]]:
    """Parse self-BLAST outfmt 6 rows used for containment filtering."""
    rows: list[tuple[str, str, float, int, int, int]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) < 12:
                continue
            qseqid = parts[0]
            sseqid = parts[1]
            try:
                pident = float(parts[2])
                aln_len = int(float(parts[3]))
                qlen = int(float(parts[4]))
                slen = int(float(parts[5]))
            except ValueError:
                continue
            rows.append((qseqid, sseqid, pident, aln_len, qlen, slen))

    return rows


def _select_contigs_to_remove(
    blast_rows: list[tuple[str, str, float, int, int, int]],
    *,
    pident_min: float,
    min_coverage_fraction: float,
    known_ids: set[str],
) -> set[str]:
    """Select contigs to remove based on containment relationships."""
    removed: set[str] = set()

    for qseqid, sseqid, pident, aln_len, qlen, slen in blast_rows:
        if qseqid == sseqid:
            continue
        if qseqid not in known_ids or sseqid not in known_ids:
            continue
        if pident < pident_min:
            continue

        shorter = min(qlen, slen)
        if shorter <= 0:
            continue
        coverage_fraction = float(aln_len) / float(shorter)
        if coverage_fraction < min_coverage_fraction:
            continue

        if qlen < slen:
            removed.add(qseqid)
        elif slen < qlen:
            removed.add(sseqid)
        else:
            # Deterministic tie-break: keep lexicographically smallest ID.
            removed.add(max(qseqid, sseqid))

    return removed


def deduplicate_contigs(
    input_fasta: Path,
    output_fasta: Path,
    cfg: DedupConfig,
    *,
    workdir: Path | None = None,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> DedupResult:
    """Remove contained contigs using self-BLAST comparisons.

    Args:
        input_fasta: Input FASTA to deduplicate.
        output_fasta: Output FASTA containing non-contained contigs.
        cfg: Deduplication runtime configuration.
        workdir: Optional directory for BLAST intermediate files.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        DedupResult summary.

    Raises:
        ValueError: If input FASTA is invalid.
        RuntimeError: If required tools are unavailable or BLAST commands fail.
    """
    fasta_result = validate_fasta(input_fasta, check_nonempty=True, min_records=1)
    if not fasta_result.valid:
        raise ValueError("Invalid input FASTA: " + "; ".join(fasta_result.errors))

    for name, exec_name in (
        ("makeblastdb", cfg.makeblastdb_exec),
        ("blastn", cfg.blastn_exec),
    ):
        info = check_tool(exec_name)
        if not info.available:
            raise RuntimeError(f"{name} executable not available: {exec_name}")

    output_fasta.parent.mkdir(parents=True, exist_ok=True)
    if workdir is None:
        workdir = output_fasta.parent / "dedup_work"
    workdir.mkdir(parents=True, exist_ok=True)

    db_prefix = workdir / "self_db"
    blast_out = workdir / "self_blast.tsv"

    makeblastdb_cmd = [
        cfg.makeblastdb_exec,
        "-in",
        str(input_fasta),
        "-dbtype",
        "nucl",
        "-out",
        str(db_prefix),
    ]

    blastn_cmd = [
        cfg.blastn_exec,
        "-query",
        str(input_fasta),
        "-db",
        str(db_prefix),
        "-out",
        str(blast_out),
        "-outfmt",
        "6 qseqid sseqid pident length qlen slen qstart qend sstart send evalue bitscore",
        "-evalue",
        str(cfg.evalue),
        "-num_threads",
        str(max(1, int(cfg.threads))),
    ]

    try:
        run_tool(makeblastdb_cmd, out_log=out_log, err_log=err_log, check=True)
        run_tool(blastn_cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        detail = _extract_stderr(exc)
        msg = f"Deduplication BLAST command failed with exit code {exc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg) from exc

    records = list(iter_fasta_records(input_fasta))
    known_ids = {rec_id for rec_id, _seq in records}

    blast_rows = _parse_self_blast_tsv(blast_out)
    removed = _select_contigs_to_remove(
        blast_rows,
        pident_min=float(cfg.pident_min),
        min_coverage_fraction=float(cfg.min_coverage_fraction),
        known_ids=known_ids,
    )

    kept_records = [(rec_id, seq) for rec_id, seq in records if rec_id not in removed]
    write_fasta(iter(kept_records), output_fasta)

    removed_ids = sorted(removed)

    return DedupResult(
        output_fasta=output_fasta,
        n_input=len(records),
        n_unique=len(kept_records),
        n_removed=len(removed_ids),
        removed_ids=removed_ids,
    )
