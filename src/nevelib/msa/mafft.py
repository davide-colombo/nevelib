"""MAFFT command wrappers for multiple sequence alignment workflows."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
import shutil
import subprocess

from nevelib._common.fasta import validate_fasta
from nevelib._common.toolrun import check_tool, run_tool


LOGGER = logging.getLogger(__name__)


@dataclass
class MafftConfig:
    """Configuration for MAFFT execution.

    Attributes:
        mafft_exec: Name or path of the MAFFT binary.
        threads: Number of threads for MAFFT.
        extra_args: Additional MAFFT CLI arguments.
        auto: Use MAFFT --auto mode for automatic strategy selection.
    """

    mafft_exec: str = "mafft"
    threads: int = 4
    extra_args: list[str] | None = None
    auto: bool = True


def _read_stderr_tail(path: Path | None, n: int = 20) -> str:
    """Read the last stderr lines from a log file when available."""
    if path is None or not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    return "\n".join(lines[-n:])


def _extract_error_text(exc: subprocess.CalledProcessError, err_log: Path | None) -> str:
    """Extract stderr text from an exception or fallback log file."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        text = stderr.decode("utf-8", errors="replace")
    else:
        text = stderr or ""
    text = text.strip()
    if text:
        return text
    return _read_stderr_tail(err_log)


def _validate_input_fasta(path: Path, label: str) -> int:
    """Validate a FASTA input and return record count."""
    if not path.exists():
        raise FileNotFoundError(path)

    result = validate_fasta(path, check_nonempty=True, min_records=1)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTA: " + "; ".join(result.errors))
    return int(result.record_count or 0)


def _ensure_mafft_available(exec_name: str) -> None:
    """Verify MAFFT binary is available."""
    info = check_tool(exec_name, version_args=["--version"])
    if not info.available:
        raise RuntimeError(f"MAFFT executable not available: {exec_name}")


def _run_mafft_stdout(
    cmd: list[str],
    *,
    err_log: Path | None = None,
) -> str:
    """Run MAFFT command and return stdout alignment text."""
    LOGGER.debug("Running MAFFT command: %s", " ".join(cmd))
    try:
        proc = run_tool(cmd, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        err_text = _extract_error_text(exc, err_log)
        detail = f"MAFFT failed with exit code {exc.returncode}"
        if err_text:
            detail = f"{detail}: {err_text}"
        raise RuntimeError(detail) from exc

    out_text = proc.stdout or ""
    if not out_text.strip():
        raise RuntimeError("MAFFT produced empty alignment output.")
    return out_text


def run_mafft(
    input_fasta: Path,
    output_alignment: Path,
    cfg: MafftConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> Path:
    """Run MAFFT alignment for all sequences in one FASTA input.

    Singleton inputs are copied directly to output without invoking MAFFT.

    Args:
        input_fasta: Input FASTA path.
        output_alignment: Output aligned FASTA path.
        cfg: MAFFT runtime configuration.
        out_log: Optional path to write captured MAFFT stdout.
        err_log: Optional path to write MAFFT stderr.

    Returns:
        Path to the output aligned FASTA.
    """
    n_records = _validate_input_fasta(input_fasta, "input")

    output_alignment.parent.mkdir(parents=True, exist_ok=True)

    if n_records == 1:
        LOGGER.info("Singleton FASTA input detected; copying input to alignment output.")
        shutil.copyfile(input_fasta, output_alignment)
        return output_alignment

    _ensure_mafft_available(cfg.mafft_exec)

    # MAFFT does not expose a public seed flag here, so alignment output may vary across runs.
    cmd = [
        cfg.mafft_exec,
        "--thread",
        str(max(1, int(cfg.threads))),
    ]
    if cfg.auto:
        cmd.append("--auto")
    if cfg.extra_args:
        cmd.extend(str(arg) for arg in cfg.extra_args)
    cmd.append(str(input_fasta))

    out_text = _run_mafft_stdout(cmd, err_log=err_log)
    output_alignment.write_text(out_text, encoding="utf-8")
    if out_log is not None:
        out_log.parent.mkdir(parents=True, exist_ok=True)
        out_log.write_text(out_text, encoding="utf-8")

    return output_alignment


def run_mafft_seed_and_add(
    seed_fasta: Path,
    add_fasta: Path | None,
    output_alignment: Path,
    cfg: MafftConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> Path:
    """Run MAFFT seed alignment and optional add-fragments extension.

    Behavior is extracted from NextEVE Stage_06:
    1) align seed FASTA;
    2) if add FASTA has records, run MAFFT add-fragments on the seed alignment.

    Args:
        seed_fasta: Seed FASTA for the initial alignment.
        add_fasta: Additional FASTA to add (optional).
        output_alignment: Final output alignment path.
        cfg: MAFFT runtime configuration.
        out_log: Optional path to write captured MAFFT stdout.
        err_log: Optional path to write MAFFT stderr.

    Returns:
        Path to final output alignment FASTA.
    """
    _validate_input_fasta(seed_fasta, "seed")
    _ensure_mafft_available(cfg.mafft_exec)

    output_alignment.parent.mkdir(parents=True, exist_ok=True)
    threads = str(max(1, int(cfg.threads)))
    extra_args = [str(arg) for arg in (cfg.extra_args or [])]

    # MAFFT does not expose a public seed flag here, so alignment output may vary across runs.
    cmd_seed = [cfg.mafft_exec]
    if cfg.auto:
        cmd_seed.append("--auto")
    cmd_seed.extend(["--thread", threads, *extra_args, str(seed_fasta)])

    seed_alignment = _run_mafft_stdout(cmd_seed, err_log=err_log)

    add_records = 0
    if add_fasta is not None:
        if not add_fasta.exists():
            raise FileNotFoundError(add_fasta)
        add_result = validate_fasta(add_fasta, check_nonempty=False, min_records=0)
        if not add_result.valid:
            raise ValueError("Invalid add FASTA: " + "; ".join(add_result.errors))
        add_records = int(add_result.record_count or 0)

    if add_fasta is None or add_records == 0:
        output_alignment.write_text(seed_alignment, encoding="utf-8")
        if out_log is not None:
            out_log.parent.mkdir(parents=True, exist_ok=True)
            out_log.write_text(seed_alignment, encoding="utf-8")
        return output_alignment

    seed_alignment_path = output_alignment.with_suffix(".seed.aln.fasta")
    seed_alignment_path.write_text(seed_alignment, encoding="utf-8")

    # MAFFT add-fragments does not expose a public seed flag here, so final output may vary across runs.
    cmd_add = [
        cfg.mafft_exec,
        "--addfragments",
        str(add_fasta),
        "--keeplength",
        "--thread",
        threads,
        *extra_args,
        str(seed_alignment_path),
    ]

    final_alignment = _run_mafft_stdout(cmd_add, err_log=err_log)
    output_alignment.write_text(final_alignment, encoding="utf-8")

    if out_log is not None:
        out_log.parent.mkdir(parents=True, exist_ok=True)
        out_log.write_text(final_alignment, encoding="utf-8")

    return output_alignment
