"""Read trimming and quality-report execution utilities."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import subprocess

from nevelib._common.fastq import validate_fastq, validate_paired_fastq
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class TrimmingConfig:
    """Configuration for fastp-based trimming."""

    fastp_exec: str = "fastp"
    threads: int = 8
    qualified_quality_phred: int = 20
    min_length: int = 50
    detect_adapter_for_pe: bool = True
    extra_args: list[str] | None = None


@dataclass
class TrimmingResult:
    """Result of paired-read trimming."""

    r1: Path
    r2: Path
    json_report: Path | None = None
    html_report: Path | None = None
    reads_before: int = 0
    reads_after: int = 0
    bases_before: int = 0
    bases_after: int = 0


@dataclass
class FastQCConfig:
    """Configuration for FastQC report generation."""

    fastqc_exec: str = "fastqc"
    threads: int = 4


def _fastq_base_name(path: Path) -> str:
    """Return basename used by FastQC output naming."""
    name = path.name
    if name.endswith(".gz"):
        name = name[:-3]
    return Path(name).stem


def run_fastp(
    r1_in: Path,
    r2_in: Path,
    r1_out: Path,
    r2_out: Path,
    cfg: TrimmingConfig,
    *,
    output_dir: Path,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> TrimmingResult:
    """Run fastp on paired FASTQ files and parse summary metrics.

    Args:
        r1_in: Input read-1 FASTQ.
        r2_in: Input read-2 FASTQ.
        r1_out: Output read-1 FASTQ.
        r2_out: Output read-2 FASTQ.
        cfg: fastp configuration.
        output_dir: Directory where reports are written.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        TrimmingResult with output paths and summary counts.
    """
    r1_val, r2_val = validate_paired_fastq(
        r1_in,
        r2_in,
        check_sync=True,
        check_gzip=True,
        check_nonempty=True,
        min_reads=1,
    )
    if not r1_val.valid or not r2_val.valid:
        errors = r1_val.errors + r2_val.errors
        raise ValueError("Invalid FASTQ inputs for fastp: " + "; ".join(errors))

    tool = check_tool(cfg.fastp_exec, version_args=["--version"])
    if not tool.available:
        raise RuntimeError(f"fastp executable not available: {cfg.fastp_exec}")

    output_dir.mkdir(parents=True, exist_ok=True)
    r1_out.parent.mkdir(parents=True, exist_ok=True)
    r2_out.parent.mkdir(parents=True, exist_ok=True)

    json_report = output_dir / "fastp.json"
    html_report = output_dir / "fastp.html"

    cmd = [
        cfg.fastp_exec,
        "--in1",
        str(r1_in),
        "--in2",
        str(r2_in),
        "--out1",
        str(r1_out),
        "--out2",
        str(r2_out),
        "-w",
        str(max(1, int(cfg.threads))),
        "--qualified_quality_phred",
        str(int(cfg.qualified_quality_phred)),
        "--length_required",
        str(int(cfg.min_length)),
        "--json",
        str(json_report),
        "--html",
        str(html_report),
    ]

    if cfg.detect_adapter_for_pe:
        cmd.append("--detect_adapter_for_pe")

    if cfg.extra_args:
        cmd.extend(str(arg) for arg in cfg.extra_args)

    try:
        run_tool(cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        raise RuntimeError(f"fastp failed with exit code {exc.returncode}: {stderr.strip()}") from exc

    result = TrimmingResult(
        r1=r1_out,
        r2=r2_out,
        json_report=json_report if json_report.exists() else None,
        html_report=html_report if html_report.exists() else None,
    )

    if json_report.exists() and json_report.stat().st_size > 0:
        payload = json.loads(json_report.read_text(encoding="utf-8"))
        summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
        before = summary.get("before_filtering", {}) if isinstance(summary, dict) else {}
        after = summary.get("after_filtering", {}) if isinstance(summary, dict) else {}

        result.reads_before = int(before.get("total_reads", 0) or 0)
        result.reads_after = int(after.get("total_reads", 0) or 0)
        result.bases_before = int(before.get("total_bases", 0) or 0)
        result.bases_after = int(after.get("total_bases", 0) or 0)

    return result


def run_fastqc(
    fastq_files: list[Path],
    output_dir: Path,
    cfg: FastQCConfig,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
) -> list[Path]:
    """Run FastQC on one or more FASTQ files.

    Args:
        fastq_files: FASTQ inputs.
        output_dir: Output directory for FastQC reports.
        cfg: FastQC runtime settings.
        out_log: Optional stdout log path.
        err_log: Optional stderr log path.

    Returns:
        List of expected FastQC ZIP report paths.
    """
    if not fastq_files:
        return []

    for path in fastq_files:
        val = validate_fastq(path, check_gzip=True, check_nonempty=False)
        if not val.valid:
            raise ValueError(f"Invalid FASTQ for FastQC ({path}): {'; '.join(val.errors)}")

    tool = check_tool(cfg.fastqc_exec, version_args=["--version"])
    if not tool.available:
        raise RuntimeError(f"fastqc executable not available: {cfg.fastqc_exec}")

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        cfg.fastqc_exec,
        "-t",
        str(max(1, int(cfg.threads))),
        "-o",
        str(output_dir),
        *[str(path) for path in fastq_files],
    ]

    try:
        run_tool(cmd, out_log=out_log, err_log=err_log, check=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode("utf-8", errors="replace") if isinstance(exc.stderr, bytes) else str(exc.stderr or "")
        raise RuntimeError(f"FastQC failed with exit code {exc.returncode}: {stderr.strip()}") from exc

    report_paths = [output_dir / f"{_fastq_base_name(path)}_fastqc.zip" for path in fastq_files]
    return report_paths
