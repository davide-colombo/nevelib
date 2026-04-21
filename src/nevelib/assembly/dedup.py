"""Self-BLAST-based deduplication of assembled contigs."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
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
        task: BLAST task mode.
        word_size: BLAST word size.
        perc_identity: Required percent identity.
        qcov_hsp_perc: Required query coverage percent.
        max_target_seqs: Maximum targets per query (minimum effective value: 2).
        threads: Number of threads.
        extra_args: Additional blastn CLI arguments.
    """

    blastn_exec: str = "blastn"
    makeblastdb_exec: str = "makeblastdb"
    evalue: float = 1e-20
    task: str = "megablast"
    word_size: int = 28
    perc_identity: float = 100.0
    qcov_hsp_perc: float = 100.0
    max_target_seqs: int = 100
    threads: int = 8
    extra_args: list[str] | None = None


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


def _parse_self_blast_csv(path: Path) -> list[tuple[str, int, str, int]]:
    """Parse self-BLAST outfmt 10 rows used for containment filtering."""
    rows: list[tuple[str, int, str, int]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as handle:
        for raw in handle:
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) < 4:
                continue
            qseqid = parts[0]
            sseqid = parts[2]
            try:
                qlen = int(float(parts[1]))
                slen = int(float(parts[3]))
            except ValueError:
                continue
            rows.append((qseqid, qlen, sseqid, slen))

    return rows


def _select_contigs_to_remove(
    blast_rows: list[tuple[str, int, str, int]],
    *,
    known_ids: set[str],
) -> set[str]:
    """Select contigs to remove based on NextEVE containment relationships."""
    removed: set[str] = set()

    for qseqid, qlen, sseqid, slen in blast_rows:
        if qseqid == sseqid:
            continue
        if qseqid not in known_ids or sseqid not in known_ids:
            continue
        if slen < qlen:
            continue
        removed.add(qseqid)

    return removed


def deduplicate_contigs(
    input_fasta: Path,
    output_fasta: Path,
    cfg: DedupConfig,
    *,
    workdir: Path | None = None,
    out_log: Path | None = None,
    err_log: Path | None = None,
    logger: logging.Logger | None = None,
) -> DedupResult:
    """Remove contained contigs using self-BLAST comparisons.

    Args:
        input_fasta: Input FASTA to deduplicate.
        output_fasta: Output FASTA containing non-contained contigs.
        cfg: Deduplication runtime configuration.
        workdir: Optional directory for BLAST intermediate files.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.
        logger: Optional logger receiving external tool lifecycle messages.

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
    blast_out = workdir / "self_blast.csv"

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
        "-task",
        str(cfg.task),
        "-word_size",
        str(int(cfg.word_size)),
        "-query",
        str(input_fasta),
        "-db",
        str(db_prefix),
        "-num_threads",
        str(max(1, int(cfg.threads))),
        "-evalue",
        str(cfg.evalue),
        "-perc_identity",
        str(float(cfg.perc_identity)),
        "-qcov_hsp_perc",
        str(float(cfg.qcov_hsp_perc)),
        "-max_target_seqs",
        str(max(2, int(cfg.max_target_seqs))),
        "-outfmt",
        "10 qseqid qlen sseqid slen",
        "-out",
        str(blast_out),
    ]
    if cfg.extra_args:
        blastn_cmd.extend(str(arg) for arg in cfg.extra_args)

    try:
        run_tool(makeblastdb_cmd, out_log=out_log, err_log=err_log, check=True, logger=logger)
        run_tool(blastn_cmd, out_log=out_log, err_log=err_log, check=True, logger=logger)
    except subprocess.CalledProcessError as exc:
        detail = _extract_stderr(exc)
        msg = f"Deduplication BLAST command failed with exit code {exc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg) from exc

    records = list(iter_fasta_records(input_fasta))
    known_ids = {rec_id for rec_id, _seq in records}

    blast_rows = _parse_self_blast_csv(blast_out)
    removed = _select_contigs_to_remove(
        blast_rows,
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
