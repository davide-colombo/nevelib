"""BLAST execution interfaces for homology search workflows."""

from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path

from nevelib._common.blast_db import validate_blast_db
from nevelib._common.fasta import validate_fasta
from nevelib._common.toolrun import check_tool, run_tool


DEFAULT_OUTFMT_FIELDS: list[str] = [
    "qseqid",
    "sseqid",
    "pident",
    "length",
    "mismatch",
    "gapopen",
    "qstart",
    "qend",
    "sstart",
    "send",
    "evalue",
    "bitscore",
    "qlen",
    "slen",
]


@dataclass
class BlastConfig:
    """Configuration for BLAST execution."""

    blast_exec: str = "blastn"
    db_prefix: str = ""
    evalue: float = 1e-5
    max_target_seqs: int = 10
    perc_identity: float | None = None
    threads: int = 4
    outfmt: int = 6
    outfmt_fields: list[str] | None = None
    extra_args: list[str] | None = None
    db_type: str = "nucl"
    require_taxonomy: bool = False
    makeblastdb_exec: str = "makeblastdb"


def _resolve_outfmt(cfg: BlastConfig) -> str:
    """Resolve the outfmt string based on numeric format and fields."""
    fields = cfg.outfmt_fields or DEFAULT_OUTFMT_FIELDS
    if int(cfg.outfmt) == 6:
        return "6 " + " ".join(fields)
    return str(cfg.outfmt)


def _validate_query_and_db(query: Path, cfg: BlastConfig) -> None:
    """Validate query FASTA and BLAST database inputs."""
    fasta_result = validate_fasta(query, check_nonempty=True, min_records=1)
    if not fasta_result.valid:
        raise ValueError("Invalid query FASTA: " + "; ".join(fasta_result.errors))

    db_result = validate_blast_db(
        Path(cfg.db_prefix),
        db_type=cfg.db_type,
        require_taxonomy=cfg.require_taxonomy,
    )
    if not db_result.valid:
        raise ValueError("Invalid BLAST database: " + "; ".join(db_result.errors))


def _build_blast_command(query: Path, output: Path, cfg: BlastConfig) -> list[str]:
    """Build a BLAST command line from typed configuration."""
    cmd = [
        cfg.blast_exec,
        "-query",
        str(query),
        "-db",
        str(cfg.db_prefix),
        "-out",
        str(output),
        "-evalue",
        str(cfg.evalue),
        "-max_target_seqs",
        str(int(cfg.max_target_seqs)),
        "-num_threads",
        str(int(cfg.threads)),
        "-outfmt",
        _resolve_outfmt(cfg),
    ]

    if cfg.perc_identity is not None:
        cmd.extend(["-perc_identity", str(cfg.perc_identity)])

    if cfg.extra_args:
        cmd.extend([str(arg) for arg in cfg.extra_args])

    return cmd


def run_blastn(
    query: Path,
    output: Path,
    cfg: BlastConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
    logger: logging.Logger | None = None,
) -> Path:
    """Run blastn and write tabular results to output path."""
    cfg_local = BlastConfig(**{**cfg.__dict__, "blast_exec": cfg.blast_exec or "blastn"})
    if cfg_local.blast_exec == "blastx":
        cfg_local.blast_exec = "blastn"

    _validate_query_and_db(query, cfg_local)

    tool_info = check_tool(cfg_local.blast_exec)
    if not tool_info.available:
        raise RuntimeError(f"BLAST executable not available: {cfg_local.blast_exec}")

    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_blast_command(query, output, cfg_local)
    run_tool(cmd, out_log=out_log, err_log=err_log, check=True, logger=logger)

    if not output.exists():
        raise RuntimeError(f"BLAST output file was not created: {output}")
    return output


def run_blastx(
    query: Path,
    output: Path,
    cfg: BlastConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
    logger: logging.Logger | None = None,
) -> Path:
    """Run blastx and write tabular results to output path."""
    cfg_local = BlastConfig(**{**cfg.__dict__, "blast_exec": "blastx"})

    _validate_query_and_db(query, cfg_local)

    tool_info = check_tool(cfg_local.blast_exec)
    if not tool_info.available:
        raise RuntimeError(f"BLAST executable not available: {cfg_local.blast_exec}")

    output.parent.mkdir(parents=True, exist_ok=True)
    cmd = _build_blast_command(query, output, cfg_local)
    run_tool(cmd, out_log=out_log, err_log=err_log, check=True, logger=logger)

    if not output.exists():
        raise RuntimeError(f"BLAST output file was not created: {output}")
    return output


def run_makeblastdb(
    input_fasta: Path,
    db_prefix: Path,
    cfg: BlastConfig,
    *,
    db_type: str = "nucl",
    out_log: Path | None = None,
    err_log: Path | None = None,
    logger: logging.Logger | None = None,
) -> Path:
    """Run makeblastdb and return the generated database prefix path."""
    fasta_result = validate_fasta(input_fasta, check_nonempty=True, min_records=1)
    if not fasta_result.valid:
        raise ValueError("Invalid FASTA for makeblastdb: " + "; ".join(fasta_result.errors))

    tool_info = check_tool(cfg.makeblastdb_exec)
    if not tool_info.available:
        raise RuntimeError(f"makeblastdb executable not available: {cfg.makeblastdb_exec}")

    db_prefix.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        cfg.makeblastdb_exec,
        "-in",
        str(input_fasta),
        "-dbtype",
        db_type,
        "-out",
        str(db_prefix),
    ]
    run_tool(cmd, out_log=out_log, err_log=err_log, check=True, logger=logger)
    return db_prefix
