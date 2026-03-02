"""FASTQ validation helpers and lightweight QC wrappers."""

from __future__ import annotations

from dataclasses import dataclass, field
import gzip
import json
from pathlib import Path
import tempfile

from nevelib._common.compression import validate_gzip
from nevelib._common.toolrun import check_tool, run_tool


@dataclass
class FastqValidationResult:
    """Result of FASTQ validation.

    Attributes:
        valid: Whether the file passed all checks.
        path: Path to the validated file.
        warnings: Non-fatal issues detected.
        errors: Fatal issues detected (empty if valid is True).
        read_count: Number of reads detected (None if not counted).
        encoding: Detected quality encoding ('phred33', 'phred64', or None).
    """

    valid: bool
    path: Path
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    read_count: int | None = None
    encoding: str | None = None


@dataclass
class FastqQCReport:
    """Quality control summary for a FASTQ file.

    Attributes:
        path: Path to the FASTQ file.
        total_reads: Total number of reads.
        total_bases: Total number of bases.
        mean_read_length: Mean read length in bases.
        q20_fraction: Fraction of bases with quality >= 20.
        q30_fraction: Fraction of bases with quality >= 30.
        gc_fraction: GC content as a fraction.
        adapter_fraction: Fraction of reads with detected adapters (None if not checked).
        report_path: Path to the full QC report file (for example fastp JSON).
    """

    path: Path
    total_reads: int = 0
    total_bases: int = 0
    mean_read_length: float = 0.0
    q20_fraction: float = 0.0
    q30_fraction: float = 0.0
    gc_fraction: float = 0.0
    adapter_fraction: float | None = None
    report_path: Path | None = None


def _open_fastq(path: Path):
    """Open FASTQ path in text mode, transparently handling gzip files."""
    if path.suffix.lower() == ".gz":
        return gzip.open(path, "rt", encoding="utf-8", errors="replace")
    return path.open("r", encoding="utf-8", errors="replace")


def _iter_fastq_records(path: Path):
    """Yield FASTQ records as (header, sequence, plus, qualities)."""
    with _open_fastq(path) as handle:
        while True:
            header = handle.readline()
            if not header:
                return
            sequence = handle.readline()
            plus = handle.readline()
            quality = handle.readline()

            if not sequence or not plus or not quality:
                raise ValueError("FASTQ appears truncated (record does not contain 4 complete lines).")

            header = header.rstrip("\n\r")
            sequence = sequence.rstrip("\n\r")
            plus = plus.rstrip("\n\r")
            quality = quality.rstrip("\n\r")

            if not header.startswith("@"):
                raise ValueError("FASTQ header line does not start with '@'.")
            if not plus.startswith("+"):
                raise ValueError("FASTQ separator line does not start with '+'.")
            if len(sequence) != len(quality):
                raise ValueError("FASTQ sequence and quality lengths do not match.")

            yield header, sequence, plus, quality


def _normalize_header(header: str) -> str:
    """Normalize read header for paired-end synchronization checks."""
    text = header[1:] if header.startswith("@") else header
    parts = text.split()
    token = parts[0] if parts else text

    if token.endswith("/1") or token.endswith("/2"):
        token = token[:-2]

    return token


def _detect_phred_encoding(min_char: int, max_char: int) -> str | None:
    """Detect likely FASTQ quality encoding using ASCII quality range."""
    if min_char < 33:
        return None
    if min_char >= 64:
        return "phred64"
    if max_char <= 74:
        return "phred33"
    # Ambiguous range defaults to modern Phred+33.
    return "phred33"


def validate_fastq(
    path: Path,
    *,
    check_gzip: bool = True,
    check_nonempty: bool = True,
    min_reads: int = 1,
    check_encoding: bool = False,
) -> FastqValidationResult:
    """Validate a single FASTQ file.

    Args:
        path: Path to the FASTQ file (may be gzip-compressed).
        check_gzip: Verify gzip integrity if file is compressed.
        check_nonempty: Verify file contains at least min_reads records.
        min_reads: Minimum number of reads required.
        check_encoding: Detect Phred encoding variant.

    Returns:
        FastqValidationResult with validation outcome.
    """
    result = FastqValidationResult(valid=True, path=path)

    if not path.exists():
        result.valid = False
        result.errors.append(f"FASTQ file not found: {path}")
        return result

    if not path.is_file():
        result.valid = False
        result.errors.append(f"FASTQ path is not a regular file: {path}")
        return result

    if check_gzip and path.suffix.lower() == ".gz":
        try:
            validate_gzip(path)
        except ValueError as exc:
            result.valid = False
            result.errors.append(str(exc))
            return result

    read_count = 0
    min_quality_char = 127
    max_quality_char = 0

    try:
        for _header, sequence, _plus, quality in _iter_fastq_records(path):
            read_count += 1
            if check_encoding:
                if quality:
                    q_vals = [ord(c) for c in quality]
                    min_quality_char = min(min_quality_char, min(q_vals))
                    max_quality_char = max(max_quality_char, max(q_vals))
    except (OSError, ValueError) as exc:
        result.valid = False
        result.errors.append(f"FASTQ parsing failed for {path}: {exc}")
        return result

    result.read_count = read_count

    if check_nonempty and read_count < int(min_reads):
        result.valid = False
        result.errors.append(
            f"FASTQ contains {read_count} read(s); minimum required is {int(min_reads)}."
        )

    if check_encoding and read_count > 0:
        result.encoding = _detect_phred_encoding(min_quality_char, max_quality_char)
        if result.encoding is None:
            result.warnings.append("Could not confidently detect FASTQ quality encoding.")

    if result.errors:
        result.valid = False

    return result


def validate_paired_fastq(
    r1: Path,
    r2: Path,
    *,
    check_sync: bool = True,
    **kwargs,
) -> tuple[FastqValidationResult, FastqValidationResult]:
    """Validate paired FASTQ files and optional header synchronization.

    Args:
        r1: Path to read-1 FASTQ.
        r2: Path to read-2 FASTQ.
        check_sync: Validate first 100 records for synchronized pair headers.
        **kwargs: Extra keyword arguments forwarded to validate_fastq.

    Returns:
        Pair of validation results `(r1_result, r2_result)`.
    """
    r1_result = validate_fastq(r1, **kwargs)
    r2_result = validate_fastq(r2, **kwargs)

    if not check_sync:
        return r1_result, r2_result

    if not (r1_result.valid and r2_result.valid):
        return r1_result, r2_result

    try:
        r1_headers: list[str] = []
        r2_headers: list[str] = []

        for idx, (h1, _s1, _p1, _q1) in enumerate(_iter_fastq_records(r1), start=1):
            r1_headers.append(_normalize_header(h1))
            if idx >= 100:
                break

        for idx, (h2, _s2, _p2, _q2) in enumerate(_iter_fastq_records(r2), start=1):
            r2_headers.append(_normalize_header(h2))
            if idx >= 100:
                break

        if len(r1_headers) != len(r2_headers):
            msg = (
                "Paired FASTQ synchronization check failed: "
                f"different sampled read counts ({len(r1_headers)} vs {len(r2_headers)})."
            )
            r1_result.valid = False
            r2_result.valid = False
            r1_result.errors.append(msg)
            r2_result.errors.append(msg)
            return r1_result, r2_result

        for idx, (left, right) in enumerate(zip(r1_headers, r2_headers), start=1):
            if left != right:
                msg = (
                    "Paired FASTQ synchronization mismatch at sampled record "
                    f"{idx}: {left} != {right}"
                )
                r1_result.valid = False
                r2_result.valid = False
                r1_result.errors.append(msg)
                r2_result.errors.append(msg)
                break
    except (OSError, ValueError) as exc:
        msg = f"Paired FASTQ synchronization check failed: {exc}"
        r1_result.valid = False
        r2_result.valid = False
        r1_result.errors.append(msg)
        r2_result.errors.append(msg)

    return r1_result, r2_result


def run_fastq_qc(
    r1: Path,
    r2: Path | None = None,
    *,
    output_dir: Path | None = None,
    tool: str = "fastp",
    threads: int = 4,
) -> FastqQCReport:
    """Run lightweight QC reporting on FASTQ inputs.

    Args:
        r1: Read-1 FASTQ (or single-end FASTQ).
        r2: Optional read-2 FASTQ.
        output_dir: Directory for reports (temporary directory if None).
        tool: QC backend ('fastp' or 'fastqc').
        threads: Number of worker threads.

    Returns:
        FastqQCReport summary.
    """
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="nevelib_fastq_qc_"))
    output_dir.mkdir(parents=True, exist_ok=True)

    tool_norm = tool.strip().lower()

    if tool_norm == "fastp":
        if not check_tool("fastp", version_args=["--version"]).available:
            raise RuntimeError("fastp executable not available.")

        json_report = output_dir / "fastp.qc.json"
        html_report = output_dir / "fastp.qc.html"

        cmd = [
            "fastp",
            "-w",
            str(max(1, int(threads))),
            "-i",
            str(r1),
            "-o",
            "/dev/null",
            "--json",
            str(json_report),
            "--html",
            str(html_report),
        ]
        if r2 is not None:
            cmd.extend(["-I", str(r2), "-O", "/dev/null", "--detect_adapter_for_pe"])

        run_tool(cmd, check=True)

        report = FastqQCReport(path=r1, report_path=json_report)
        if json_report.exists() and json_report.stat().st_size > 0:
            raw = json.loads(json_report.read_text(encoding="utf-8"))
            summary = raw.get("summary", {}) if isinstance(raw, dict) else {}
            after = summary.get("after_filtering", {}) if isinstance(summary, dict) else {}
            before = summary.get("before_filtering", {}) if isinstance(summary, dict) else {}

            report.total_reads = int(after.get("total_reads", before.get("total_reads", 0)) or 0)
            report.total_bases = int(after.get("total_bases", before.get("total_bases", 0)) or 0)
            report.mean_read_length = float(
                after.get("read1_mean_length", after.get("read_mean_length", 0.0)) or 0.0
            )
            report.q20_fraction = float(after.get("q20_rate", 0.0) or 0.0)
            report.q30_fraction = float(after.get("q30_rate", 0.0) or 0.0)
            gc_value = float(after.get("gc_content", 0.0) or 0.0)
            report.gc_fraction = gc_value / 100.0 if gc_value > 1.0 else gc_value

            adapter = raw.get("adapter_cutting", {}) if isinstance(raw, dict) else {}
            if isinstance(adapter, dict):
                adapter_rate = adapter.get("adapter_trimmed_reads_rate")
                if adapter_rate is not None:
                    report.adapter_fraction = float(adapter_rate)

        return report

    if tool_norm == "fastqc":
        if not check_tool("fastqc", version_args=["--version"]).available:
            raise RuntimeError("fastqc executable not available.")

        inputs = [str(r1)]
        if r2 is not None:
            inputs.append(str(r2))

        cmd = [
            "fastqc",
            "-t",
            str(max(1, int(threads))),
            "-o",
            str(output_dir),
            *inputs,
        ]
        run_tool(cmd, check=True)

        first_name = r1.name[:-3] if r1.name.endswith(".gz") else r1.name
        stem = Path(first_name).stem
        report_path = output_dir / f"{stem}_fastqc.zip"

        return FastqQCReport(path=r1, report_path=report_path)

    raise ValueError(f"Unsupported QC tool: {tool}")
