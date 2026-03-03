"""Tests for nevelib.mapping module."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from nevelib._common.toolrun import ToolInfo
from nevelib.mapping import cli as mapping_cli
from nevelib.mapping.minimap2 import Minimap2Config, run_minimap2
from nevelib.mapping.paf import (
    PafRecord,
    alignment_identity,
    best_hit_per_query,
    filter_paf_records,
    parse_paf,
    parse_paf_by_query,
    query_coverage,
    target_coverage,
)


def _write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    lines: list[str] = []
    for rid, seq in records:
        lines.append(f">{rid}")
        lines.append(seq)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _make_record(
    *,
    qname: str = "q1",
    qlen: int = 100,
    qstart: int = 0,
    qend: int = 100,
    strand: str = "+",
    tname: str = "t1",
    tlen: int = 200,
    tstart: int = 0,
    tend: int = 100,
    nmatch: int = 90,
    aln_len: int = 100,
    mapq: int = 60,
) -> PafRecord:
    return PafRecord(
        qname=qname,
        qlen=qlen,
        qstart=qstart,
        qend=qend,
        strand=strand,
        tname=tname,
        tlen=tlen,
        tstart=tstart,
        tend=tend,
        nmatch=nmatch,
        aln_len=aln_len,
        mapq=mapq,
    )


# --- minimap2.py tests ---

def test_minimap2_config_defaults() -> None:
    """Minimap2Config defaults are sensible."""
    cfg = Minimap2Config()
    assert cfg.minimap2_exec == "minimap2"
    assert cfg.threads == 4
    assert cfg.preset == "asm5"
    assert cfg.extra_args is None
    assert cfg.output_format == "paf"


def test_run_minimap2_rejects_missing_query(tmp_path: Path) -> None:
    """Missing query FASTA triggers validation failure."""
    ref = tmp_path / "reference.fasta"
    _write_fasta(ref, [("r1", "ACGT")])

    with pytest.raises(ValueError, match="Invalid query FASTA"):
        run_minimap2(tmp_path / "missing.fasta", ref, tmp_path / "out.paf", Minimap2Config())


def test_run_minimap2_rejects_missing_reference(tmp_path: Path) -> None:
    """Missing reference FASTA triggers validation failure."""
    query = tmp_path / "query.fasta"
    _write_fasta(query, [("q1", "ACGT")])

    with pytest.raises(ValueError, match="Invalid reference FASTA"):
        run_minimap2(query, tmp_path / "missing_ref.fasta", tmp_path / "out.paf", Minimap2Config())


def test_run_minimap2_rejects_empty_query(tmp_path: Path) -> None:
    """Empty query FASTA is rejected."""
    query = tmp_path / "query.fasta"
    query.write_text("", encoding="utf-8")
    ref = tmp_path / "reference.fasta"
    _write_fasta(ref, [("r1", "ACGT")])

    with pytest.raises(ValueError, match="Invalid query FASTA"):
        run_minimap2(query, ref, tmp_path / "out.paf", Minimap2Config())


def test_run_minimap2_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_minimap2 builds expected command structure."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    out = tmp_path / "out.paf"
    _write_fasta(query, [("q1", "ACGT"), ("q2", "ACGA")])
    _write_fasta(ref, [("r1", "ACGT"), ("r2", "TGCA")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    run_minimap2(query, ref, out, Minimap2Config())

    cmd = seen["cmd"]
    assert cmd[0] == "minimap2"
    assert "-t" in cmd and "4" in cmd
    assert "-x" in cmd and "asm5" in cmd
    assert str(ref) in cmd
    assert str(query) in cmd
    assert out.exists()


def test_run_minimap2_with_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Preset is translated to '-x <preset>' in the command."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    _write_fasta(query, [("q1", "ACGT")])
    _write_fasta(ref, [("r1", "ACGT")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    cfg = Minimap2Config(preset="map-ont")
    run_minimap2(query, ref, tmp_path / "out.paf", cfg)

    cmd = seen["cmd"]
    assert "-x" in cmd
    assert "map-ont" in cmd


def test_run_minimap2_without_preset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No preset omits the '-x' flag."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    _write_fasta(query, [("q1", "ACGT")])
    _write_fasta(ref, [("r1", "ACGT")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    cfg = Minimap2Config(preset=None)
    run_minimap2(query, ref, tmp_path / "out.paf", cfg)

    cmd = seen["cmd"]
    assert "-x" not in cmd


def test_run_minimap2_with_extra_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Additional minimap2 arguments are appended."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    _write_fasta(query, [("q1", "ACGT")])
    _write_fasta(ref, [("r1", "ACGT")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    cfg = Minimap2Config(extra_args=["--secondary=no", "-k", "15"])
    run_minimap2(query, ref, tmp_path / "out.paf", cfg)

    cmd = seen["cmd"]
    assert "--secondary=no" in cmd
    assert "-k" in cmd and "15" in cmd


def test_run_minimap2_sam_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """SAM output mode adds '-a' flag."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    _write_fasta(query, [("q1", "ACGT")])
    _write_fasta(ref, [("r1", "ACGT")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    cfg = Minimap2Config(output_format="sam")
    run_minimap2(query, ref, tmp_path / "out.sam", cfg)

    assert "-a" in seen["cmd"]


def test_run_minimap2_nonzero_exit_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-zero minimap2 execution raises RuntimeError."""
    query = tmp_path / "query.fasta"
    ref = tmp_path / "reference.fasta"
    _write_fasta(query, [("q1", "ACGT")])
    _write_fasta(ref, [("r1", "ACGT")])

    def _fake_run_tool(cmd, **_kwargs):
        raise subprocess.CalledProcessError(returncode=2, cmd=cmd, stderr="minimap2 error")

    monkeypatch.setattr(
        "nevelib.mapping.minimap2.check_tool",
        lambda *_a, **_k: ToolInfo(name="minimap2", available=True, path=Path("/usr/bin/minimap2")),
    )
    monkeypatch.setattr("nevelib.mapping.minimap2.run_tool", _fake_run_tool)

    with pytest.raises(RuntimeError, match="minimap2 failed"):
        run_minimap2(query, ref, tmp_path / "out.paf", Minimap2Config())


# --- paf.py tests ---

def test_parse_paf_valid_file(tmp_path: Path) -> None:
    """Valid PAF file is parsed into typed records."""
    paf = tmp_path / "a.paf"
    paf.write_text(
        "q1\t100\t0\t90\t+\tt1\t200\t10\t100\t85\t90\t60\n"
        "q1\t100\t5\t80\t+\tt2\t300\t20\t95\t70\t75\t40\n"
        "q2\t150\t10\t120\t-\tt3\t500\t200\t310\t95\t110\t50\n",
        encoding="utf-8",
    )

    records = parse_paf(paf)

    assert len(records) == 3
    assert records[0].qname == "q1"
    assert records[0].tname == "t1"
    assert records[2].strand == "-"


def test_parse_paf_skips_malformed_lines(tmp_path: Path) -> None:
    """Lines with fewer than 12 columns are skipped."""
    paf = tmp_path / "a.paf"
    paf.write_text(
        "q1\t100\t0\t90\t+\tt1\t200\t10\t100\t85\t90\t60\n"
        "bad\tline\ttoo\tshort\n",
        encoding="utf-8",
    )

    records = parse_paf(paf)
    assert len(records) == 1


def test_parse_paf_empty_file(tmp_path: Path) -> None:
    """Empty file parses to an empty list."""
    paf = tmp_path / "empty.paf"
    paf.write_text("", encoding="utf-8")

    assert parse_paf(paf) == []


def test_parse_paf_with_tags(tmp_path: Path) -> None:
    """Optional tag fields are captured in tags dictionary."""
    paf = tmp_path / "a.paf"
    paf.write_text(
        "q1\t100\t0\t90\t+\tt1\t200\t10\t100\t85\t90\t60\tNM:i:5\tAS:i:100\n",
        encoding="utf-8",
    )

    records = parse_paf(paf)
    assert len(records) == 1
    assert records[0].tags["NM"] == "5"
    assert records[0].tags["AS"] == "100"


def test_parse_paf_by_query_groups_correctly(tmp_path: Path) -> None:
    """PAF grouping by query returns expected buckets."""
    paf = tmp_path / "a.paf"
    paf.write_text(
        "q1\t100\t0\t90\t+\tt1\t200\t10\t100\t85\t90\t60\n"
        "q2\t100\t0\t90\t+\tt1\t200\t10\t100\t85\t90\t60\n"
        "q1\t100\t5\t80\t+\tt2\t300\t20\t95\t70\t75\t40\n",
        encoding="utf-8",
    )

    grouped = parse_paf_by_query(paf)
    assert set(grouped) == {"q1", "q2"}
    assert len(grouped["q1"]) == 2
    assert len(grouped["q2"]) == 1


def test_filter_paf_records_by_mapq() -> None:
    """Filtering by mapq keeps only high-quality records."""
    records = [
        _make_record(mapq=10),
        _make_record(qname="q2", mapq=40),
    ]

    filtered = filter_paf_records(records, min_mapq=20)
    assert len(filtered) == 1
    assert filtered[0].qname == "q2"


def test_filter_paf_records_by_aln_len() -> None:
    """Filtering by alignment length works."""
    records = [
        _make_record(aln_len=20),
        _make_record(qname="q2", aln_len=80),
    ]

    filtered = filter_paf_records(records, min_aln_len=50)
    assert len(filtered) == 1
    assert filtered[0].qname == "q2"


def test_filter_paf_records_by_identity() -> None:
    """Filtering by identity threshold works."""
    records = [
        _make_record(nmatch=30, aln_len=100),
        _make_record(qname="q2", nmatch=90, aln_len=100),
    ]

    filtered = filter_paf_records(records, min_identity=0.8)
    assert len(filtered) == 1
    assert filtered[0].qname == "q2"


def test_filter_paf_records_multiple_criteria() -> None:
    """Multiple filter criteria are applied together."""
    records = [
        _make_record(qname="q1", mapq=60, aln_len=100, nmatch=90),
        _make_record(qname="q2", mapq=5, aln_len=100, nmatch=90),
        _make_record(qname="q3", mapq=60, aln_len=20, nmatch=19),
    ]

    filtered = filter_paf_records(
        records,
        min_mapq=20,
        min_aln_len=50,
        min_identity=0.8,
    )
    assert [r.qname for r in filtered] == ["q1"]


def test_filter_paf_records_no_filters() -> None:
    """When no thresholds are set, all records are retained."""
    records = [_make_record(qname="q1"), _make_record(qname="q2")]
    filtered = filter_paf_records(records)
    assert len(filtered) == 2


def test_best_hit_per_query_selects_highest_mapq() -> None:
    """Best-hit selection uses mapq as the default primary metric."""
    records = [
        _make_record(qname="q1", nmatch=95, mapq=30),
        _make_record(qname="q1", nmatch=50, mapq=60),
    ]

    best = best_hit_per_query(records)
    assert best["q1"].mapq == 60


def test_best_hit_per_query_tiebreak_by_mapq() -> None:
    """Tie on mapq is resolved by aln_len descending."""
    records = [
        _make_record(qname="q1", mapq=50, aln_len=80, nmatch=90),
        _make_record(qname="q1", mapq=50, aln_len=120, nmatch=70),
    ]

    best = best_hit_per_query(records)
    assert best["q1"].aln_len == 120


def test_best_hit_per_query_deterministic_for_equal_scores() -> None:
    """Equal-score records are selected deterministically across input order."""
    a = _make_record(qname="q1", nmatch=80, mapq=40, aln_len=100, tname="chr2", tstart=200, tend=260)
    b = _make_record(qname="q1", nmatch=80, mapq=40, aln_len=100, tname="chr1", tstart=100, tend=160)

    pick1 = best_hit_per_query([a, b])["q1"]
    pick2 = best_hit_per_query([b, a])["q1"]

    assert (pick1.tname, pick1.tstart, pick1.tend) == (pick2.tname, pick2.tstart, pick2.tend)


def test_alignment_identity_basic() -> None:
    """Identity is nmatch / aln_len."""
    record = _make_record(nmatch=90, aln_len=100)
    assert alignment_identity(record) == pytest.approx(0.9)


def test_alignment_identity_zero_aln_len() -> None:
    """Zero alignment length yields identity 0.0."""
    record = _make_record(nmatch=0, aln_len=0)
    assert alignment_identity(record) == 0.0


def test_query_coverage_basic() -> None:
    """Query coverage is computed from half-open query coordinates."""
    record = _make_record(qlen=100, qstart=10, qend=90)
    assert query_coverage(record) == pytest.approx(0.8)


def test_target_coverage_basic() -> None:
    """Target coverage is computed from half-open target coordinates."""
    record = _make_record(tlen=200, tstart=0, tend=50)
    assert target_coverage(record) == pytest.approx(0.25)


# --- CLI tests ---

def test_mapping_cli_rejects_missing_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI exits with code 1 for missing config file."""
    monkeypatch.setattr("sys.argv", ["nevelib-mapping", "/nonexistent.yaml"])

    with pytest.raises(SystemExit) as exc:
        mapping_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "config file not found" in captured.err


def test_mapping_cli_prints_usage_on_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI prints usage and exits 0 on --help."""
    monkeypatch.setattr("sys.argv", ["nevelib-mapping", "--help"])

    with pytest.raises(SystemExit) as exc:
        mapping_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "Usage: nevelib-mapping <config.yaml>" in captured.err
