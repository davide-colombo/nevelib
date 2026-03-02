"""minimap2 execution helpers for generic sequence-to-sequence mapping."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import subprocess

from nevelib._common.fasta import validate_fasta
from nevelib._common.toolrun import check_tool, run_tool


LOGGER = logging.getLogger(__name__)


@dataclass
class Minimap2Config:
    """Configuration for minimap2 execution.

    Attributes:
        minimap2_exec: Name or path of the minimap2 binary.
        threads: Number of threads.
        preset: minimap2 preset (for example: map-ont, asm5, asm10, sr).
            None means no preset flag is added.
        extra_args: Additional minimap2 CLI arguments.
        output_format: Output format: 'paf' (default) or 'sam'.
    """

    minimap2_exec: str = "minimap2"
    threads: int = 4
    preset: str | None = "asm5"
    extra_args: list[str] | None = None
    output_format: str = "paf"


def _validate_fasta_input(path: Path, label: str) -> None:
    """Validate a FASTA input path and raise on invalid content."""
    result = validate_fasta(path, check_nonempty=True, min_records=1)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTA: " + "; ".join(result.errors))


def _stderr_tail_from_log(path: Path | None, n_lines: int = 20) -> str:
    """Read last stderr lines from a log path when available."""
    if path is None or not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n_lines:])


def _extract_error_text(exc: subprocess.CalledProcessError, err_log: Path | None) -> str:
    """Extract stderr text from an exception or a fallback log path."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        text = stderr.decode("utf-8", errors="replace")
    else:
        text = stderr or ""
    text = text.strip()
    if text:
        return text
    return _stderr_tail_from_log(err_log)


def run_minimap2(
    query: Path,
    reference: Path,
    output: Path,
    cfg: Minimap2Config,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> Path:
    """Run minimap2 and write output alignments to the provided file.

    Args:
        query: Query FASTA path.
        reference: Reference FASTA path.
        output: Output path (PAF or SAM depending on configuration).
        cfg: Minimap2 execution settings.
        out_log: Optional path receiving raw minimap2 stdout.
        err_log: Optional path receiving minimap2 stderr.

    Returns:
        Output path.

    Raises:
        ValueError: If inputs are invalid or output_format is unsupported.
        RuntimeError: If minimap2 is not available or returns non-zero exit.
    """
    _validate_fasta_input(query, "query")
    _validate_fasta_input(reference, "reference")

    fmt = str(cfg.output_format or "paf").strip().lower()
    if fmt not in {"paf", "sam"}:
        raise ValueError(f"Unsupported minimap2 output_format: {cfg.output_format}")

    tool = check_tool(cfg.minimap2_exec, version_args=["--version"])
    if not tool.available:
        raise RuntimeError(f"minimap2 executable not available: {cfg.minimap2_exec}")

    cmd: list[str] = [
        cfg.minimap2_exec,
        "-t",
        str(max(1, int(cfg.threads))),
    ]

    if cfg.preset is not None and str(cfg.preset).strip():
        cmd.extend(["-x", str(cfg.preset)])

    if fmt == "sam":
        cmd.append("-a")

    if cfg.extra_args:
        cmd.extend(str(arg) for arg in cfg.extra_args)

    cmd.extend([str(reference), str(query)])

    LOGGER.debug("Running minimap2 command: %s", " ".join(cmd))

    try:
        proc = run_tool(cmd, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        err_text = _extract_error_text(exc, err_log)
        msg = f"minimap2 failed with exit code {exc.returncode}"
        if err_text:
            msg = f"{msg}: {err_text}"
        raise RuntimeError(msg) from exc

    output.parent.mkdir(parents=True, exist_ok=True)
    out_text = proc.stdout or ""
    output.write_text(out_text, encoding="utf-8")

    if out_log is not None:
        out_log.parent.mkdir(parents=True, exist_ok=True)
        out_log.write_text(out_text, encoding="utf-8")

    return output
