"""MMseqs2 clustering interfaces.

This module provides a generic API for running `mmseqs easy-linclust`
and resolving the generated cluster assignment TSV.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import subprocess

from nevelib._common.fasta import validate_fasta
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class MmseqsConfig:
    """Configuration for MMseqs2 linclust execution."""

    mmseqs_exec: str = "mmseqs"
    min_seq_id: float = 0.9
    coverage: float = 0.8
    cov_mode: int = 0
    alignment_mode: int = 3
    threads: int = 4
    min_aln_len: int = 0
    split_memory_limit: str | None = None
    tmp_dir_name: str = "mmseqs_tmp"


def _resolve_cluster_tsv(output_prefix: Path) -> Path:
    """Resolve the MMseqs2 cluster TSV path for the provided output prefix."""
    candidates = [
        output_prefix.with_name(f"{output_prefix.name}_cluster.tsv"),
        output_prefix.with_suffix(".tsv"),
        output_prefix / "cluster.tsv",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    glob_candidates = sorted(output_prefix.parent.glob(f"{output_prefix.name}*_cluster.tsv"))
    if glob_candidates:
        return glob_candidates[0]

    looked = ", ".join(str(p) for p in candidates)
    raise FileNotFoundError(f"MMseqs cluster TSV not found. Looked for: {looked}")


def run_mmseqs_linclust(
    input_fasta: Path,
    output_prefix: Path,
    tmp_dir: Path,
    cfg: MmseqsConfig,
) -> Path:
    """Run MMseqs2 easy-linclust for sequence clustering.

    Args:
        input_fasta: Input FASTA containing sequences to cluster.
        output_prefix: Output prefix used by MMseqs2.
        tmp_dir: Temporary working directory for MMseqs2 internals.
        cfg: MMseqs2 execution and threshold parameters.

    Returns:
        Path to the generated cluster TSV file.

    Raises:
        FileNotFoundError: If input FASTA does not exist.
        ValueError: If FASTA validation fails.
        RuntimeError: If MMseqs2 is unavailable or execution fails.
    """
    if not input_fasta.exists():
        raise FileNotFoundError(input_fasta)

    validation = validate_fasta(
        input_fasta,
        check_nonempty=True,
        min_records=1,
        check_duplicates=False,
    )
    if not validation.valid:
        raise ValueError("Invalid input FASTA: " + "; ".join(validation.errors))

    tool_info = check_tool(cfg.mmseqs_exec, version_args=["--version"])
    if not tool_info.available:
        raise RuntimeError(f"MMseqs2 executable is not available: {cfg.mmseqs_exec}")

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    tmp_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        cfg.mmseqs_exec,
        "easy-linclust",
        str(input_fasta),
        str(output_prefix),
        str(tmp_dir),
        "--min-seq-id",
        str(cfg.min_seq_id),
        "--min-aln-len",
        str(cfg.min_aln_len),
        "-c",
        str(cfg.coverage),
        "--cov-mode",
        str(cfg.cov_mode),
        "--alignment-mode",
        str(cfg.alignment_mode),
        "--similarity-type",
        "2",
        "--threads",
        str(cfg.threads),
    ]
    if cfg.split_memory_limit:
        cmd.extend(["--split-memory-limit", str(cfg.split_memory_limit)])

    try:
        run_tool(cmd, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        raise RuntimeError(f"MMseqs2 easy-linclust failed: {exc}") from exc
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return _resolve_cluster_tsv(output_prefix)
