"""Tests for the nevelib.msa module."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from nevelib._common.config import load_config
from nevelib._common.toolrun import ToolInfo
from nevelib.msa import cli as msa_cli
from nevelib.msa.mafft import MafftConfig, run_mafft, run_mafft_seed_and_add
from nevelib.msa.metrics import MetricsConfig, compute_alignment_metrics, parse_fasta_alignment


def _write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    lines: list[str] = []
    for rec_id, seq in records:
        lines.append(f">{rec_id}")
        lines.append(seq)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- mafft.py tests ---

def test_mafft_config_defaults() -> None:
    """MafftConfig defaults are sensible."""
    cfg = MafftConfig()
    assert cfg.mafft_exec == "mafft"
    assert cfg.threads == 4
    assert cfg.auto is True
    assert cfg.extra_args is None


def test_run_mafft_rejects_missing_input(tmp_path: Path) -> None:
    """Missing input FASTA raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        run_mafft(tmp_path / "missing.fasta", tmp_path / "out.fasta", MafftConfig())


def test_run_mafft_rejects_empty_fasta(tmp_path: Path) -> None:
    """Empty FASTA fails validation."""
    inp = tmp_path / "empty.fasta"
    inp.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid input FASTA"):
        run_mafft(inp, tmp_path / "out.fasta", MafftConfig())


def test_run_mafft_singleton_copies_input(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Singleton input is copied without invoking MAFFT."""
    inp = tmp_path / "singleton.fasta"
    out = tmp_path / "aligned.fasta"
    _write_fasta(inp, [("s1", "ACGT")])

    called = {"n": 0}

    def _fake_run_tool(*_args, **_kwargs):
        called["n"] += 1
        return subprocess.CompletedProcess(args=["mafft"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.msa.mafft.run_tool", _fake_run_tool)

    result = run_mafft(inp, out, MafftConfig())

    assert result == out
    assert out.exists()
    assert out.read_text(encoding="utf-8") == inp.read_text(encoding="utf-8")
    assert called["n"] == 0


def test_run_mafft_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_mafft builds expected MAFFT command arguments."""
    inp = tmp_path / "input.fasta"
    out = tmp_path / "aligned.fasta"
    _write_fasta(inp, [("s1", "ACGT"), ("s2", "ACGA")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=">s1\nACGT\n>s2\nACGA\n", stderr="")

    monkeypatch.setattr(
        "nevelib.msa.mafft.check_tool",
        lambda *_a, **_k: ToolInfo(name="mafft", available=True, path=Path("/usr/bin/mafft")),
    )
    monkeypatch.setattr("nevelib.msa.mafft.run_tool", _fake_run_tool)

    cfg = MafftConfig(mafft_exec="mafft", threads=8, auto=True, extra_args=["--maxiterate", "1000"])
    run_mafft(inp, out, cfg)

    cmd = seen["cmd"]
    assert cmd[0] == "mafft"
    assert "--thread" in cmd and "8" in cmd
    assert "--auto" in cmd
    assert "--maxiterate" in cmd and "1000" in cmd
    assert str(inp) in cmd
    assert out.exists()


def test_run_mafft_nonzero_exit_raises(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MAFFT non-zero exit is translated to RuntimeError."""
    inp = tmp_path / "input.fasta"
    out = tmp_path / "aligned.fasta"
    _write_fasta(inp, [("s1", "ACGT"), ("s2", "ACGA")])

    def _fake_run_tool(cmd, **_kwargs):
        raise subprocess.CalledProcessError(returncode=1, cmd=cmd, stderr="mafft failure")

    monkeypatch.setattr(
        "nevelib.msa.mafft.check_tool",
        lambda *_a, **_k: ToolInfo(name="mafft", available=True, path=Path("/usr/bin/mafft")),
    )
    monkeypatch.setattr("nevelib.msa.mafft.run_tool", _fake_run_tool)

    with pytest.raises(RuntimeError, match="MAFFT failed"):
        run_mafft(inp, out, MafftConfig())


def test_run_mafft_seed_and_add_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Seed+add workflow runs MAFFT with add-fragments command."""
    seed = tmp_path / "seed.fasta"
    add = tmp_path / "add.fasta"
    out = tmp_path / "aligned.fasta"
    _write_fasta(seed, [("s1", "ACGT"), ("s2", "ACGA")])
    _write_fasta(add, [("s3", "ACGG")])

    calls: list[list[str]] = []

    def _fake_run_tool(cmd, **_kwargs):
        calls.append(cmd)
        if "--addfragments" in cmd:
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=0,
                stdout=">s1\nACGT\n>s2\nACGA\n>s3\nACGG\n",
                stderr="",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=">s1\nACGT\n>s2\nACGA\n", stderr="")

    monkeypatch.setattr(
        "nevelib.msa.mafft.check_tool",
        lambda *_a, **_k: ToolInfo(name="mafft", available=True, path=Path("/usr/bin/mafft")),
    )
    monkeypatch.setattr("nevelib.msa.mafft.run_tool", _fake_run_tool)

    run_mafft_seed_and_add(seed, add, out, MafftConfig())

    assert len(calls) == 2
    assert calls[0][0] == "mafft"
    assert str(seed) in calls[0]
    assert "--addfragments" in calls[1]
    assert str(add) in calls[1]
    assert out.exists()


def test_run_mafft_seed_and_add_falls_back_for_empty_add(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty add FASTA falls back to seed-only alignment output."""
    seed = tmp_path / "seed.fasta"
    add = tmp_path / "add.fasta"
    out = tmp_path / "aligned.fasta"
    _write_fasta(seed, [("s1", "ACGT"), ("s2", "ACGA")])
    add.write_text("", encoding="utf-8")

    calls: list[list[str]] = []

    def _fake_run_tool(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=">s1\nACGT\n>s2\nACGA\n", stderr="")

    monkeypatch.setattr(
        "nevelib.msa.mafft.check_tool",
        lambda *_a, **_k: ToolInfo(name="mafft", available=True, path=Path("/usr/bin/mafft")),
    )
    monkeypatch.setattr("nevelib.msa.mafft.run_tool", _fake_run_tool)

    run_mafft_seed_and_add(seed, add, out, MafftConfig())

    assert len(calls) == 1
    assert str(seed) in calls[0]
    assert out.exists()


# --- metrics.py tests ---

def test_parse_fasta_alignment_valid(tmp_path: Path) -> None:
    """Aligned FASTA is parsed into expected ID -> sequence mapping."""
    path = tmp_path / "aln.fasta"
    _write_fasta(path, [("a", "AC-G"), ("b", "AT-G")])

    parsed = parse_fasta_alignment(path)

    assert parsed == {"a": "AC-G", "b": "AT-G"}
    assert len({len(v) for v in parsed.values()}) == 1


def test_parse_fasta_alignment_rejects_unequal_lengths(tmp_path: Path) -> None:
    """Alignment parser rejects unequal sequence lengths."""
    path = tmp_path / "bad_aln.fasta"
    _write_fasta(path, [("a", "ACGT"), ("b", "ACG")])

    with pytest.raises(ValueError, match="inconsistent"):
        parse_fasta_alignment(path)


def test_compute_metrics_empty_alignment_matches_stage06_behavior() -> None:
    """Empty aligned input returns zero-span metrics with n_total from core lengths."""
    metrics = compute_alignment_metrics(
        aligned={},
        cfg=MetricsConfig(occupancy_threshold=0.6, min_seq_length=80),
        core_lengths={"node1": 120},
    )
    assert metrics.n_total == 1
    assert metrics.n_aligned == 0
    assert metrics.shared_span_bp == 0
    assert metrics.shared_span_frac == 0.0
    assert metrics.median_identity is None
    assert metrics.p10_identity is None


def test_compute_metrics_all_gap_column() -> None:
    """All-gap shared-span edge case matches NextEVE zero-division handling."""
    aligned = {
        "a": "---",
        "b": "---",
    }
    metrics = compute_alignment_metrics(
        aligned=aligned,
        cfg=MetricsConfig(occupancy_threshold=0.6, min_seq_length=80),
        core_lengths={"a": 0, "b": 0},
    )
    assert metrics.shared_span_bp == 0
    assert metrics.shared_span_frac == 0.0
    assert metrics.median_identity == pytest.approx(0.0)
    assert metrics.p10_identity == pytest.approx(0.0)


def test_compute_metrics_single_sequence() -> None:
    """Single-sequence alignment does not divide by zero."""
    aligned = {"only": "ACGT"}
    metrics = compute_alignment_metrics(
        aligned=aligned,
        cfg=MetricsConfig(occupancy_threshold=0.5, min_seq_length=4),
        core_lengths={"only": 4},
    )
    assert metrics.n_total == 1
    assert metrics.n_aligned == 1
    assert metrics.shared_span_bp == 4
    assert metrics.shared_span_frac == pytest.approx(1.0)
    assert metrics.median_identity == pytest.approx(1.0)
    assert metrics.p10_identity == pytest.approx(1.0)


def test_compute_metrics_consensus_identity_stats() -> None:
    """Median and p10 identities are computed from per-sequence consensus identity."""
    aligned = {
        "a": "AAAA",
        "b": "AAAT",
        "c": "AATT",
        "d": "TTTT",
    }
    metrics = compute_alignment_metrics(
        aligned=aligned,
        cfg=MetricsConfig(occupancy_threshold=0.5, min_seq_length=4),
        core_lengths={"a": 4, "b": 4, "c": 4, "d": 4},
    )
    assert metrics.shared_span_bp == 4
    assert metrics.shared_span_frac == pytest.approx(1.0)
    assert metrics.median_identity == pytest.approx(0.75)
    assert metrics.p10_identity == pytest.approx(0.25)


def test_compute_metrics_length_summaries() -> None:
    """Length summary outputs mirror Stage_06 median/fraction logic."""
    aligned = {
        "a": "ACGT",
        "b": "ACGT",
        "c": "ACGT",
    }
    metrics = compute_alignment_metrics(
        aligned=aligned,
        cfg=MetricsConfig(occupancy_threshold=0.6, min_seq_length=80),
        core_lengths={"a": 120, "b": 60, "c": 80, "d": 200},
    )
    assert metrics.n_total == 4
    assert metrics.n_aligned == 3
    assert metrics.median_sequence_length == pytest.approx(80.0)
    assert metrics.frac_length_ge_min == pytest.approx(2 / 3)


def test_metrics_config_defaults() -> None:
    """MetricsConfig defaults match msa/config.sample.yaml."""
    sample_path = Path(__file__).resolve().parents[1] / "msa" / "config.sample.yaml"
    sample_cfg = load_config(sample_path)
    defaults = MetricsConfig()

    mcfg = sample_cfg["metrics"]
    assert defaults.occupancy_threshold == mcfg["occupancy_threshold"]
    assert defaults.min_seq_length == mcfg["min_seq_length"]


# --- CLI tests ---

def test_msa_cli_rejects_missing_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI exits with code 1 when config file does not exist."""
    monkeypatch.setattr("sys.argv", ["nevelib-msa", "/nonexistent.yaml"])

    with pytest.raises(SystemExit) as exc:
        msa_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "config file not found" in captured.err


def test_msa_cli_prints_usage_on_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI prints usage and exits 0 for --help."""
    monkeypatch.setattr("sys.argv", ["nevelib-msa", "--help"])

    with pytest.raises(SystemExit) as exc:
        msa_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "Usage: nevelib-msa <config.yaml>" in captured.err
