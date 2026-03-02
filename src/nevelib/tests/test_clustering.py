"""Tests for the nevelib.clustering module."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pandas as pd
import pytest

from nevelib._common.config import load_config
from nevelib._common.toolrun import ToolInfo
from nevelib.clustering import cli as clustering_cli
from nevelib.clustering.mmseqs import MmseqsConfig, run_mmseqs_linclust
from nevelib.clustering.parse import (
    ClusterAssignment,
    cluster_assignments_to_dataframe,
    parse_mmseqs_clusters,
    validate_existing_clusters,
)


def test_mmseqs_config_defaults_match_sample_yaml() -> None:
    """Default MmseqsConfig values match clustering/config.sample.yaml."""
    sample_path = Path(__file__).resolve().parents[1] / "clustering" / "config.sample.yaml"
    sample_cfg = load_config(sample_path)

    defaults = MmseqsConfig()
    mmseqs_cfg = sample_cfg["mmseqs"]

    assert defaults.mmseqs_exec == mmseqs_cfg["exec"]
    assert defaults.min_seq_id == mmseqs_cfg["min_seq_id"]
    assert defaults.coverage == mmseqs_cfg["coverage"]
    assert defaults.cov_mode == mmseqs_cfg["cov_mode"]
    assert defaults.alignment_mode == mmseqs_cfg["alignment_mode"]
    assert defaults.threads == mmseqs_cfg["threads"]
    assert defaults.min_aln_len == mmseqs_cfg["min_aln_len"]
    assert defaults.split_memory_limit == mmseqs_cfg["split_memory_limit"]
    assert defaults.tmp_dir_name == mmseqs_cfg["tmp_dir_name"]


def test_run_mmseqs_linclust_rejects_missing_input(tmp_path: Path) -> None:
    """Missing input FASTA raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        run_mmseqs_linclust(
            input_fasta=tmp_path / "missing.fasta",
            output_prefix=tmp_path / "linclust",
            tmp_dir=tmp_path / "tmp",
            cfg=MmseqsConfig(),
        )


def test_run_mmseqs_linclust_rejects_empty_fasta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Empty FASTA fails input validation."""
    fasta = tmp_path / "empty.fasta"
    fasta.write_text("", encoding="utf-8")

    monkeypatch.setattr(
        "nevelib.clustering.mmseqs.check_tool",
        lambda *_a, **_k: ToolInfo(name="mmseqs", available=True, path=Path("/usr/bin/mmseqs")),
    )

    with pytest.raises(ValueError, match="Invalid input FASTA"):
        run_mmseqs_linclust(
            input_fasta=fasta,
            output_prefix=tmp_path / "linclust",
            tmp_dir=tmp_path / "tmp",
            cfg=MmseqsConfig(),
        )


def test_run_mmseqs_linclust_nonzero_exit_raises_and_cleans_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-zero MMseqs execution raises RuntimeError and removes tmp dir."""
    fasta = tmp_path / "input.fasta"
    fasta.write_text(">seq1\nACGT\n", encoding="utf-8")
    output_prefix = tmp_path / "linclust"
    tmp_dir = tmp_path / "mmseqs_tmp"

    monkeypatch.setattr(
        "nevelib.clustering.mmseqs.check_tool",
        lambda *_a, **_k: ToolInfo(name="mmseqs", available=True, path=Path("/usr/bin/mmseqs")),
    )

    def _fake_run_tool(*_args, **_kwargs):
        raise subprocess.CalledProcessError(returncode=7, cmd=["mmseqs", "easy-linclust"])

    monkeypatch.setattr("nevelib.clustering.mmseqs.run_tool", _fake_run_tool)

    with pytest.raises(RuntimeError, match="MMseqs2 easy-linclust failed"):
        run_mmseqs_linclust(
            input_fasta=fasta,
            output_prefix=output_prefix,
            tmp_dir=tmp_dir,
            cfg=MmseqsConfig(),
        )

    assert not tmp_dir.exists()


def test_run_mmseqs_linclust_success_cleans_tmp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Successful MMseqs execution removes tmp dir and returns cluster TSV path."""
    fasta = tmp_path / "input.fasta"
    fasta.write_text(">seq1\nACGT\n", encoding="utf-8")
    output_prefix = tmp_path / "linclust"
    tmp_dir = tmp_path / "mmseqs_tmp"

    monkeypatch.setattr(
        "nevelib.clustering.mmseqs.check_tool",
        lambda *_a, **_k: ToolInfo(name="mmseqs", available=True, path=Path("/usr/bin/mmseqs")),
    )

    def _fake_run_tool(*_args, **_kwargs):
        cluster_tsv = output_prefix.with_name(f"{output_prefix.name}_cluster.tsv")
        cluster_tsv.write_text("seq1\tseq1\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=["mmseqs"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.clustering.mmseqs.run_tool", _fake_run_tool)

    cluster_tsv = run_mmseqs_linclust(
        input_fasta=fasta,
        output_prefix=output_prefix,
        tmp_dir=tmp_dir,
        cfg=MmseqsConfig(),
    )

    assert cluster_tsv.exists()
    assert not tmp_dir.exists()


def test_parse_mmseqs_clusters_deterministic_ids(tmp_path: Path) -> None:
    """Cluster IDs are deterministic: size-descending then representative-ascending."""
    cluster_tsv = tmp_path / "clusters.tsv"
    cluster_tsv.write_text(
        "rep_b\trep_b\n"
        "rep_b\tb1\n"
        "rep_b\tb2\n"
        "rep_a\trep_a\n"
        "rep_a\ta1\n"
        "rep_c\trep_c\n",
        encoding="utf-8",
    )

    all_ids = ["b2", "rep_a", "a1", "rep_b", "b1", "rep_c"]

    assignments_a = parse_mmseqs_clusters(cluster_tsv, all_ids)
    assignments_b = parse_mmseqs_clusters(cluster_tsv, all_ids)

    assert assignments_a == assignments_b

    by_seq = {entry.sequence_id: entry for entry in assignments_a}
    assert by_seq["rep_b"].cluster_id == 1
    assert by_seq["b1"].cluster_id == 1
    assert by_seq["b2"].cluster_id == 1
    assert by_seq["rep_a"].cluster_id == 2
    assert by_seq["a1"].cluster_id == 2
    assert by_seq["rep_c"].cluster_id == 3


def test_parse_mmseqs_clusters_singletons_get_own_ids(tmp_path: Path) -> None:
    """IDs missing from cluster TSV are added as singleton clusters."""
    cluster_tsv = tmp_path / "clusters.tsv"
    cluster_tsv.write_text("rep1\trep1\nrep1\ta\n", encoding="utf-8")

    all_ids = ["rep1", "a", "x", "y"]
    assignments = parse_mmseqs_clusters(cluster_tsv, all_ids)
    by_seq = {entry.sequence_id: entry for entry in assignments}

    assert by_seq["rep1"].cluster_id == by_seq["a"].cluster_id
    assert by_seq["x"].cluster_id != by_seq["y"].cluster_id
    assert by_seq["x"].cluster_id > by_seq["rep1"].cluster_id
    assert by_seq["y"].cluster_id > by_seq["rep1"].cluster_id


def test_parse_mmseqs_clusters_all_ids_accounted_for(tmp_path: Path) -> None:
    """Parser returns one assignment per input ID."""
    cluster_tsv = tmp_path / "clusters.tsv"
    cluster_tsv.write_text("rep1\trep1\n", encoding="utf-8")

    all_ids = ["rep1", "a", "b", "c"]
    assignments = parse_mmseqs_clusters(cluster_tsv, all_ids)

    assert len(assignments) == len(all_ids)
    assert {a.sequence_id for a in assignments} == set(all_ids)


def test_validate_existing_clusters_valid(tmp_path: Path) -> None:
    """Existing cluster TSV is valid when all IDs are covered."""
    cluster_tsv = tmp_path / "clusters.tsv"
    cluster_tsv.write_text("r1\tr1\nr1\ta\n", encoding="utf-8")

    valid, reason = validate_existing_clusters(cluster_tsv, ["r1", "a"])

    assert valid is True
    assert reason == ""


def test_validate_existing_clusters_missing_ids(tmp_path: Path) -> None:
    """Validation fails when some expected IDs are missing."""
    cluster_tsv = tmp_path / "clusters.tsv"
    cluster_tsv.write_text("r1\tr1\n", encoding="utf-8")

    valid, reason = validate_existing_clusters(cluster_tsv, ["r1", "a"])

    assert valid is False
    assert "missing" in reason.lower()


def test_validate_existing_clusters_nonexistent_file(tmp_path: Path) -> None:
    """Validation fails cleanly when the cluster TSV does not exist."""
    valid, reason = validate_existing_clusters(tmp_path / "missing.tsv", ["a"])

    assert valid is False
    assert "exist" in reason.lower()


def test_cluster_assignments_to_dataframe_schema() -> None:
    """Assignment DataFrame has expected columns, dtypes, and sort order."""
    assignments = [
        ClusterAssignment("b", 2, False, "r2"),
        ClusterAssignment("a", 1, True, "a"),
        ClusterAssignment("r2", 2, True, "r2"),
    ]

    df = cluster_assignments_to_dataframe(assignments)

    assert list(df.columns) == ["sequence_id", "cluster_id", "is_representative", "representative_id"]
    assert pd.api.types.is_integer_dtype(df["cluster_id"])
    assert pd.api.types.is_bool_dtype(df["is_representative"])
    assert list(df["sequence_id"]) == ["a", "b", "r2"]


def test_cli_rejects_missing_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """CLI exits with code 1 and clear error when config file is missing."""
    monkeypatch.setattr("sys.argv", ["nevelib-clustering", "/nonexistent.yaml"])

    with pytest.raises(SystemExit) as exc:
        clustering_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "config file not found" in captured.err
