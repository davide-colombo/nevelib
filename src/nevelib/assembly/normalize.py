"""Digital normalization utilities for paired FASTQ inputs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from nevelib._common.fastq import validate_fastq
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class NormalizeConfig:
    """Configuration for digital normalization via BBNorm.

    Attributes:
        bbnorm_exec: Name or path of the bbnorm.sh binary (BBTools).
        target_coverage: Target coverage depth for normalization.
        min_depth: Minimum depth to retain a k-mer.
        threads: Number of threads.
        memory: Java heap memory string (for example: '8g').
        extra_args: Additional BBNorm CLI arguments.
    """

    bbnorm_exec: str = "bbnorm.sh"
    target_coverage: int = 100
    min_depth: int = 5
    threads: int = 8
    memory: str = "8g"
    extra_args: list[str] | None = None


def _validate_input_fastq(path: Path, label: str) -> None:
    """Validate a FASTQ input path and raise if invalid."""
    result = validate_fastq(path, check_gzip=True, check_nonempty=True, min_reads=1)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTQ: " + "; ".join(result.errors))


def _extract_stderr(exc: subprocess.CalledProcessError) -> str:
    """Extract stderr text from CalledProcessError."""
    stderr = exc.stderr
    if isinstance(stderr, bytes):
        return stderr.decode("utf-8", errors="replace").strip()
    return (stderr or "").strip()


def normalize_pairs(
    r1_in: Path,
    r2_in: Path,
    r1_out: Path,
    r2_out: Path,
    cfg: NormalizeConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> tuple[Path, Path]:
    """Run BBNorm on paired-end FASTQ inputs.

    Args:
        r1_in: Input read-1 FASTQ path.
        r2_in: Input read-2 FASTQ path.
        r1_out: Output normalized read-1 FASTQ path.
        r2_out: Output normalized read-2 FASTQ path.
        cfg: Normalization runtime configuration.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        Tuple with output FASTQ paths `(r1_out, r2_out)`.

    Raises:
        ValueError: If input FASTQ validation fails.
        RuntimeError: If BBNorm is unavailable or fails.
    """
    _validate_input_fastq(r1_in, "r1")
    _validate_input_fastq(r2_in, "r2")

    tool = check_tool(cfg.bbnorm_exec)
    if not tool.available:
        raise RuntimeError(f"BBNorm executable not available: {cfg.bbnorm_exec}")

    r1_out.parent.mkdir(parents=True, exist_ok=True)
    r2_out.parent.mkdir(parents=True, exist_ok=True)

    cmd: list[str] = [
        cfg.bbnorm_exec,
        f"in={r1_in}",
        f"in2={r2_in}",
        f"out={r1_out}",
        f"out2={r2_out}",
        f"target={int(cfg.target_coverage)}",
        f"mindepth={int(cfg.min_depth)}",
        f"threads={max(1, int(cfg.threads))}",
        f"-Xmx{cfg.memory}",
    ]
    if cfg.extra_args:
        cmd.extend(str(arg) for arg in cfg.extra_args)

    try:
        run_tool(cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        detail = _extract_stderr(exc)
        msg = f"BBNorm failed with exit code {exc.returncode}"
        if detail:
            msg = f"{msg}: {detail}"
        raise RuntimeError(msg) from exc

    if not r1_out.exists() or not r2_out.exists():
        raise RuntimeError(
            "BBNorm did not produce expected outputs: "
            f"{r1_out} and {r2_out}"
        )

    return r1_out, r2_out
