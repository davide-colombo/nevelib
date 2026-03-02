"""Tests for nevelib.reads module."""

from __future__ import annotations

import gzip
import json
from pathlib import Path
import subprocess

import pytest

from nevelib._common.bam import BamValidationResult
from nevelib._common.toolrun import ToolInfo
from nevelib.reads import cli as reads_cli
from nevelib.reads.extract import ExtractionConfig, extract_reads_from_bam
from nevelib.reads.qc import FastQCConfig, TrimmingConfig, run_fastp, run_fastqc


def _write_fastq(path: Path, records: list[tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as handle:
        for header, seq, qual in records:
            handle.write(f"@{header}\n{seq}\n+\n{qual}\n")


def _write_bam_with_index(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"BAM")
    path.with_suffix(path.suffix + ".bai").write_bytes(b"BAI")


# --- extraction tests ---

def test_extraction_config_defaults() -> None:
    """ExtractionConfig defaults are sensible."""
    cfg = ExtractionConfig()
    assert cfg.samtools_exec == "samtools"
    assert cfg.threads == 8
    assert cfg.extract_unmapped is True
    assert cfg.extract_supplementary is False
    assert cfg.include_secondary is False
    assert cfg.mapq_min == 0


def test_extract_reads_rejects_missing_bam(tmp_path: Path) -> None:
    """Missing BAM input raises validation error."""
    with pytest.raises(ValueError, match="Invalid BAM input"):
        extract_reads_from_bam(
            tmp_path / "missing.bam",
            tmp_path / "out",
            ExtractionConfig(),
        )


def test_extract_reads_builds_samtools_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction builds expected samtools view|fastq command."""
    bam = tmp_path / "reads.bam"
    _write_bam_with_index(bam)
    out_dir = tmp_path / "out"

    seen: dict[str, str] = {}

    def _fake_run_tool(cmd, **_kwargs):
        assert isinstance(cmd, str)
        seen["cmd"] = cmd

        _write_fastq(out_dir / "reads_R1.fq.gz", [("r1/1", "ACGT", "IIII")])
        _write_fastq(out_dir / "reads_R2.fq.gz", [("r1/2", "TGCA", "IIII")])
        _write_fastq(out_dir / "reads_singletons.fq.gz", [])

        return subprocess.CompletedProcess(args=[cmd], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.extract.validate_bam",
        lambda *_a, **_k: BamValidationResult(valid=True, path=bam, is_sorted=True, has_index=True),
    )
    monkeypatch.setattr(
        "nevelib.reads.extract.check_tool",
        lambda *_a, **_k: ToolInfo(name="samtools", available=True, path=Path("/usr/bin/samtools")),
    )
    monkeypatch.setattr("nevelib.reads.extract.run_tool", _fake_run_tool)

    extract_reads_from_bam(bam, out_dir, ExtractionConfig(mapq_min=10))

    cmd = seen["cmd"]
    assert "samtools view" in cmd
    assert "samtools fastq" in cmd
    assert "-q 10" in cmd
    assert "-1" in cmd and "reads_R1.fq.gz" in cmd
    assert "-2" in cmd and "reads_R2.fq.gz" in cmd
    assert "-s" in cmd and "reads_singletons.fq.gz" in cmd


def test_extract_reads_recompresses_bgzf(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BGZF outputs trigger recompression to standard gzip."""
    bam = tmp_path / "reads.bam"
    _write_bam_with_index(bam)
    out_dir = tmp_path / "out"

    called: list[Path] = []

    def _fake_run_tool(cmd, **_kwargs):
        _write_fastq(out_dir / "reads_R1.fq.gz", [("r1/1", "ACGT", "IIII")])
        _write_fastq(out_dir / "reads_R2.fq.gz", [("r1/2", "TGCA", "IIII")])
        _write_fastq(out_dir / "reads_singletons.fq.gz", [])
        return subprocess.CompletedProcess(args=[cmd], returncode=0, stdout="", stderr="")

    def _fake_validate_gzip(path: Path) -> str:
        if path.name == "reads_R1.fq.gz":
            return "bgzf"
        return "gzip"

    def _fake_recompress(input_path: Path, output_path: Path, _cfg):
        called.append(input_path)
        output_path.write_bytes(input_path.read_bytes())
        return output_path

    monkeypatch.setattr(
        "nevelib.reads.extract.validate_bam",
        lambda *_a, **_k: BamValidationResult(valid=True, path=bam, is_sorted=True, has_index=True),
    )
    monkeypatch.setattr(
        "nevelib.reads.extract.check_tool",
        lambda *_a, **_k: ToolInfo(name="samtools", available=True, path=Path("/usr/bin/samtools")),
    )
    monkeypatch.setattr("nevelib.reads.extract.run_tool", _fake_run_tool)
    monkeypatch.setattr("nevelib.reads.extract.validate_gzip", _fake_validate_gzip)
    monkeypatch.setattr("nevelib.reads.extract.recompress_if_bgzf", _fake_recompress)

    extract_reads_from_bam(bam, out_dir, ExtractionConfig())

    assert out_dir / "reads_R1.fq.gz" in called


def test_extract_reads_returns_correct_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Extraction result returns expected output paths and counts."""
    bam = tmp_path / "reads.bam"
    _write_bam_with_index(bam)
    out_dir = tmp_path / "out"

    def _fake_run_tool(cmd, **_kwargs):
        _write_fastq(out_dir / "reads_R1.fq.gz", [("r1/1", "ACGT", "IIII")])
        _write_fastq(out_dir / "reads_R2.fq.gz", [("r1/2", "TGCA", "IIII")])
        _write_fastq(out_dir / "reads_singletons.fq.gz", [("s1", "AAAA", "IIII")])
        return subprocess.CompletedProcess(args=[cmd], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.extract.validate_bam",
        lambda *_a, **_k: BamValidationResult(valid=True, path=bam, is_sorted=True, has_index=True),
    )
    monkeypatch.setattr(
        "nevelib.reads.extract.check_tool",
        lambda *_a, **_k: ToolInfo(name="samtools", available=True, path=Path("/usr/bin/samtools")),
    )
    monkeypatch.setattr("nevelib.reads.extract.run_tool", _fake_run_tool)

    result = extract_reads_from_bam(bam, out_dir, ExtractionConfig())

    assert result.r1 == out_dir / "reads_R1.fq.gz"
    assert result.r2 == out_dir / "reads_R2.fq.gz"
    assert result.singleton == out_dir / "reads_singletons.fq.gz"
    assert result.paired_count == 1
    assert result.singleton_count == 1


# --- trimming/QC tests ---

def test_trimming_config_defaults() -> None:
    """TrimmingConfig defaults are sensible."""
    cfg = TrimmingConfig()
    assert cfg.fastp_exec == "fastp"
    assert cfg.threads == 8
    assert cfg.qualified_quality_phred == 20
    assert cfg.min_length == 50
    assert cfg.detect_adapter_for_pe is True
    assert cfg.extra_args is None


def test_run_fastp_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_fastp builds expected fastp command with required options."""
    r1_in = tmp_path / "in_R1.fq.gz"
    r2_in = tmp_path / "in_R2.fq.gz"
    r1_out = tmp_path / "out_R1.fq.gz"
    r2_out = tmp_path / "out_R2.fq.gz"
    out_dir = tmp_path / "trim"

    _write_fastq(r1_in, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2_in, [("x/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        assert isinstance(cmd, list)
        seen["cmd"] = cmd
        _write_fastq(r1_out, [("x/1", "ACGT", "IIII")])
        _write_fastq(r2_out, [("x/2", "TGCA", "IIII")])
        (out_dir / "fastp.json").write_text('{"summary":{}}', encoding="utf-8")
        (out_dir / "fastp.html").write_text("<html></html>", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.qc.check_tool",
        lambda *_a, **_k: ToolInfo(name="fastp", available=True, path=Path("/usr/bin/fastp")),
    )
    monkeypatch.setattr("nevelib.reads.qc.run_tool", _fake_run_tool)

    run_fastp(
        r1_in,
        r2_in,
        r1_out,
        r2_out,
        TrimmingConfig(threads=4),
        output_dir=out_dir,
    )

    cmd = seen["cmd"]
    assert cmd[0] == "fastp"
    assert "--in1" in cmd and str(r1_in) in cmd
    assert "--in2" in cmd and str(r2_in) in cmd
    assert "--out1" in cmd and str(r1_out) in cmd
    assert "--out2" in cmd and str(r2_out) in cmd
    assert "-w" in cmd and "4" in cmd


def test_run_fastp_parses_json_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_fastp extracts before/after counts from fastp JSON summary."""
    r1_in = tmp_path / "in_R1.fq.gz"
    r2_in = tmp_path / "in_R2.fq.gz"
    r1_out = tmp_path / "out_R1.fq.gz"
    r2_out = tmp_path / "out_R2.fq.gz"
    out_dir = tmp_path / "trim"

    _write_fastq(r1_in, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2_in, [("x/2", "TGCA", "IIII")])

    report = {
        "summary": {
            "before_filtering": {"total_reads": 10000, "total_bases": 1500000},
            "after_filtering": {"total_reads": 9500, "total_bases": 1400000},
        }
    }

    def _fake_run_tool(cmd, **_kwargs):
        _write_fastq(r1_out, [("x/1", "ACGT", "IIII")])
        _write_fastq(r2_out, [("x/2", "TGCA", "IIII")])
        (out_dir / "fastp.json").write_text(json.dumps(report), encoding="utf-8")
        (out_dir / "fastp.html").write_text("<html></html>", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.qc.check_tool",
        lambda *_a, **_k: ToolInfo(name="fastp", available=True, path=Path("/usr/bin/fastp")),
    )
    monkeypatch.setattr("nevelib.reads.qc.run_tool", _fake_run_tool)

    result = run_fastp(
        r1_in,
        r2_in,
        r1_out,
        r2_out,
        TrimmingConfig(),
        output_dir=out_dir,
    )

    assert result.reads_before == 10000
    assert result.reads_after == 9500
    assert result.bases_before == 1500000
    assert result.bases_after == 1400000


def test_run_fastp_with_extra_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Configured fastp extra_args are appended to command."""
    r1_in = tmp_path / "in_R1.fq.gz"
    r2_in = tmp_path / "in_R2.fq.gz"
    r1_out = tmp_path / "out_R1.fq.gz"
    r2_out = tmp_path / "out_R2.fq.gz"
    out_dir = tmp_path / "trim"

    _write_fastq(r1_in, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2_in, [("x/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fastq(r1_out, [("x/1", "ACGT", "IIII")])
        _write_fastq(r2_out, [("x/2", "TGCA", "IIII")])
        (out_dir / "fastp.json").write_text('{"summary":{}}', encoding="utf-8")
        (out_dir / "fastp.html").write_text("<html></html>", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.qc.check_tool",
        lambda *_a, **_k: ToolInfo(name="fastp", available=True, path=Path("/usr/bin/fastp")),
    )
    monkeypatch.setattr("nevelib.reads.qc.run_tool", _fake_run_tool)

    run_fastp(
        r1_in,
        r2_in,
        r1_out,
        r2_out,
        TrimmingConfig(extra_args=["--trim_front1", "5"]),
        output_dir=out_dir,
    )

    cmd = seen["cmd"]
    assert "--trim_front1" in cmd
    assert "5" in cmd


def test_run_fastqc_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_fastqc builds expected command arguments."""
    r1 = tmp_path / "R1.fq.gz"
    r2 = tmp_path / "R2.fq.gz"
    out_dir = tmp_path / "qc"
    _write_fastq(r1, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2, [("x/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.qc.check_tool",
        lambda *_a, **_k: ToolInfo(name="fastqc", available=True, path=Path("/usr/bin/fastqc")),
    )
    monkeypatch.setattr("nevelib.reads.qc.run_tool", _fake_run_tool)

    run_fastqc([r1, r2], out_dir, FastQCConfig(threads=3))

    cmd = seen["cmd"]
    assert cmd[0] == "fastqc"
    assert "-t" in cmd and "3" in cmd
    assert "-o" in cmd and str(out_dir) in cmd
    assert str(r1) in cmd and str(r2) in cmd


def test_run_fastqc_returns_expected_report_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """FastQC wrapper returns expected ZIP report file paths."""
    r1 = tmp_path / "sample_R1.fq.gz"
    r2 = tmp_path / "sample_R2.fq.gz"
    out_dir = tmp_path / "qc"
    _write_fastq(r1, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2, [("x/2", "TGCA", "IIII")])

    def _fake_run_tool(cmd, **_kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.reads.qc.check_tool",
        lambda *_a, **_k: ToolInfo(name="fastqc", available=True, path=Path("/usr/bin/fastqc")),
    )
    monkeypatch.setattr("nevelib.reads.qc.run_tool", _fake_run_tool)

    reports = run_fastqc([r1, r2], out_dir, FastQCConfig())

    assert reports == [
        out_dir / "sample_R1_fastqc.zip",
        out_dir / "sample_R2_fastqc.zip",
    ]


# --- CLI tests ---

def test_reads_cli_rejects_missing_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """reads CLI exits with code 1 for a missing config path."""
    monkeypatch.setattr("sys.argv", ["nevelib-reads", "/nonexistent.yaml"])

    with pytest.raises(SystemExit) as exc:
        reads_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "config file not found" in captured.err


def test_reads_cli_prints_usage_on_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """reads CLI prints usage and exits 0 on --help."""
    monkeypatch.setattr("sys.argv", ["nevelib-reads", "--help"])

    with pytest.raises(SystemExit) as exc:
        reads_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "Usage: nevelib-reads <config.yaml>" in captured.err
