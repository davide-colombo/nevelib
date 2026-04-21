"""Tests for nevelib.search module and related prerequisites."""

from __future__ import annotations

import logging
from pathlib import Path
import subprocess

import pandas as pd
import pytest

from nevelib._common.toolrun import ToolInfo
from nevelib.search import cli as search_cli
from nevelib.search.blast import BlastConfig, run_blastn, run_blastx, run_makeblastdb
from nevelib.search.classify import (
    classify_hits_by_taxonomy,
    is_missing_taxonomy,
    matches_keywords,
)
from nevelib.search.hits import (
    BlastHit,
    filter_hits,
    filter_hits_by_bitscore_fraction,
    normalize_blast_strand,
    parse_blast_tabular,
    parse_blast_to_dataframe,
    prune_contained_intervals,
    select_best_hit_per_query,
)


def _write_query_fasta(path: Path) -> None:
    path.write_text(">q1\nACGTACGT\n", encoding="utf-8")


def _write_fake_db(prefix: Path, db_type: str = "nucl") -> None:
    prefix.parent.mkdir(parents=True, exist_ok=True)
    if db_type == "nucl":
        (prefix.with_suffix(".nin")).write_text("", encoding="utf-8")
        (prefix.with_suffix(".nsq")).write_text("", encoding="utf-8")
        (prefix.with_suffix(".nhr")).write_text("", encoding="utf-8")
    else:
        (prefix.with_suffix(".pin")).write_text("", encoding="utf-8")
        (prefix.with_suffix(".psq")).write_text("", encoding="utf-8")
        (prefix.with_suffix(".phr")).write_text("", encoding="utf-8")


# --- blast.py tests ---

def test_blast_config_defaults() -> None:
    """BlastConfig defaults are initialized correctly."""
    cfg = BlastConfig()
    assert cfg.blast_exec == "blastn"
    assert cfg.db_prefix == ""
    assert cfg.evalue == 1e-5
    assert cfg.max_target_seqs == 10
    assert cfg.threads == 4
    assert cfg.outfmt == 6


def test_run_blastn_rejects_missing_query(tmp_path: Path) -> None:
    """run_blastn rejects missing query FASTA path."""
    cfg = BlastConfig(db_prefix=str(tmp_path / "db" / "core"))
    with pytest.raises(ValueError, match="Invalid query FASTA"):
        run_blastn(tmp_path / "missing.fasta", tmp_path / "out.tsv", cfg)


def test_run_blastn_rejects_invalid_db(tmp_path: Path) -> None:
    """run_blastn rejects invalid BLAST database prefix."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)

    cfg = BlastConfig(db_prefix=str(tmp_path / "db" / "missing"))
    with pytest.raises(ValueError, match="Invalid BLAST database"):
        run_blastn(query, tmp_path / "out.tsv", cfg)


def test_run_blastn_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_blastn builds expected BLAST command arguments."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)
    db_prefix = tmp_path / "db" / "core"
    _write_fake_db(db_prefix)

    captured: dict[str, object] = {}

    def _fake_run_tool(cmd, **_kwargs):
        captured["cmd"] = cmd
        output = Path(cmd[cmd.index("-out") + 1])
        output.write_text("q1\ts1\t99.0\t10\t0\t0\t1\t10\t2\t11\t1e-5\t100\t10\t20\n", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda *_a, **_k: ToolInfo("blastn", True, path=Path("/usr/bin/blastn")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(db_prefix=str(db_prefix), evalue=1e-6, max_target_seqs=20, threads=8)
    run_blastn(query, tmp_path / "raw.tsv", cfg)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert cmd[0] == "blastn"
    assert "-query" in cmd and str(query) in cmd
    assert "-db" in cmd and str(db_prefix) in cmd
    assert "-evalue" in cmd and "1e-06" in cmd
    assert "-max_target_seqs" in cmd and "20" in cmd
    assert "-num_threads" in cmd and "8" in cmd
    assert "-outfmt" in cmd


def test_run_blastn_with_perc_identity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_blastn includes -perc_identity when configured."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)
    db_prefix = tmp_path / "db" / "core"
    _write_fake_db(db_prefix)

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        Path(cmd[cmd.index("-out") + 1]).write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda *_a, **_k: ToolInfo("blastn", True, path=Path("/usr/bin/blastn")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(db_prefix=str(db_prefix), perc_identity=97.5)
    run_blastn(query, tmp_path / "raw.tsv", cfg)

    cmd = seen["cmd"]
    assert "-perc_identity" in cmd
    assert "97.5" in cmd


def test_run_blastn_with_extra_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_blastn appends extra BLAST arguments."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)
    db_prefix = tmp_path / "db" / "core"
    _write_fake_db(db_prefix)

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        Path(cmd[cmd.index("-out") + 1]).write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda *_a, **_k: ToolInfo("blastn", True, path=Path("/usr/bin/blastn")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(db_prefix=str(db_prefix), extra_args=["-task", "blastn-short"])
    run_blastn(query, tmp_path / "raw.tsv", cfg)

    cmd = seen["cmd"]
    assert cmd[-2:] == ["-task", "blastn-short"]


def test_run_blastn_threads_logger_to_run_tool(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_blastn forwards the injected logger to run_tool."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)
    db_prefix = tmp_path / "db" / "core"
    _write_fake_db(db_prefix)
    logger = logging.getLogger("test.blast.logger")
    captured: dict[str, object] = {}

    def _fake_run_tool(cmd, **kwargs):  # type: ignore[no-untyped-def]
        captured["kwargs"] = kwargs
        Path(cmd[cmd.index("-out") + 1]).write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda *_a, **_k: ToolInfo("blastn", True, path=Path("/usr/bin/blastn")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(db_prefix=str(db_prefix))
    run_blastn(query, tmp_path / "raw.tsv", cfg, logger=logger)

    assert captured["kwargs"]["logger"] is logger


def test_run_blastx_uses_blastx_binary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_blastx uses blastx executable in command."""
    query = tmp_path / "query.fasta"
    _write_query_fasta(query)
    db_prefix = tmp_path / "db" / "core"
    _write_fake_db(db_prefix, db_type="prot")

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        Path(cmd[cmd.index("-out") + 1]).write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda name, **_k: ToolInfo(name, True, path=Path(f"/usr/bin/{name}")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(db_prefix=str(db_prefix), db_type="prot")
    run_blastx(query, tmp_path / "raw.tsv", cfg)

    cmd = seen["cmd"]
    assert cmd[0] == "blastx"


def test_run_makeblastdb_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """run_makeblastdb builds the expected makeblastdb command."""
    fasta = tmp_path / "input.fasta"
    fasta.write_text(">x\nACGT\n", encoding="utf-8")
    db_prefix = tmp_path / "db" / "newdb"

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib.search.blast.check_tool", lambda *_a, **_k: ToolInfo("makeblastdb", True, path=Path("/usr/bin/makeblastdb")))
    monkeypatch.setattr("nevelib.search.blast.run_tool", _fake_run_tool)

    cfg = BlastConfig(makeblastdb_exec="makeblastdb")
    run_makeblastdb(fasta, db_prefix, cfg, db_type="nucl")

    cmd = seen["cmd"]
    assert cmd[0] == "makeblastdb"
    assert "-in" in cmd and str(fasta) in cmd
    assert "-dbtype" in cmd and "nucl" in cmd
    assert "-out" in cmd and str(db_prefix) in cmd


# --- hits.py tests ---

def _write_hits_file(path: Path, rows: list[str]) -> None:
    path.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def test_parse_blast_tabular_valid_file(tmp_path: Path) -> None:
    """parse_blast_tabular parses valid rows into hit objects."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q1\ts2\t97.0\t80\t2\t0\t10\t89\t20\t99\t1e-20\t150\t100\t900",
            "q2\ts3\t95.0\t60\t3\t1\t1\t60\t30\t89\t1e-10\t120\t60\t700",
        ],
    )

    hits = parse_blast_tabular(path)
    assert len(hits) == 3
    assert hits[0].qseqid == "q1"
    assert hits[0].sseqid == "s1"
    assert hits[0].bitscore == 200.0


def test_parse_blast_tabular_skips_truncated_rows(tmp_path: Path) -> None:
    """Rows with insufficient columns are skipped."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q_bad\ts_bad\t99.0",
        ],
    )

    hits = parse_blast_tabular(path)
    assert len(hits) == 1
    assert hits[0].qseqid == "q1"


def test_parse_blast_tabular_skips_comment_lines(tmp_path: Path) -> None:
    """Comment lines are ignored when parsing BLAST tabular output."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "# BLAST output",
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "# end",
        ],
    )

    hits = parse_blast_tabular(path)
    assert len(hits) == 1


def test_parse_blast_tabular_empty_file(tmp_path: Path) -> None:
    """Empty BLAST file returns an empty hit list."""
    path = tmp_path / "empty.tsv"
    _write_hits_file(path, [])
    hits = parse_blast_tabular(path)
    assert hits == []


def test_parse_blast_to_dataframe_column_names(tmp_path: Path) -> None:
    """DataFrame columns follow expected BLAST field names."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        ["q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000"],
    )
    df = parse_blast_to_dataframe(path)
    assert list(df.columns) == [
        "qseqid",
        "sseqid",
        "pident",
        "length",
        "mismatch",
        "gapopen",
        "qstart",
        "qend",
        "sstart",
        "send",
        "evalue",
        "bitscore",
        "qlen",
        "slen",
    ]


def test_filter_hits_by_pident(tmp_path: Path) -> None:
    """filter_hits applies minimum percent identity threshold."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q1\ts2\t70.0\t100\t0\t0\t1\t100\t5\t104\t1e-20\t180\t100\t1000",
        ],
    )
    hits = parse_blast_tabular(path)
    filtered = filter_hits(hits, min_pident=90.0)
    assert isinstance(filtered, list)
    assert len(filtered) == 1
    assert filtered[0].sseqid == "s1"


def test_filter_hits_by_evalue(tmp_path: Path) -> None:
    """filter_hits applies maximum evalue threshold."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q1\ts2\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-2\t180\t100\t1000",
        ],
    )
    df = parse_blast_to_dataframe(path)
    filtered = filter_hits(df, max_evalue=1e-5)
    assert isinstance(filtered, pd.DataFrame)
    assert len(filtered) == 1


def test_filter_hits_multiple_criteria(tmp_path: Path) -> None:
    """filter_hits supports multiple threshold criteria simultaneously."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q1\ts2\t85.0\t20\t0\t0\t1\t20\t5\t24\t1e-3\t50\t20\t200",
        ],
    )
    hits = parse_blast_tabular(path)
    filtered = filter_hits(hits, min_pident=90, min_length=50, max_evalue=1e-5)
    assert len(filtered) == 1
    assert filtered[0].sseqid == "s1"


def test_select_best_hit_per_query(tmp_path: Path) -> None:
    """select_best_hit_per_query returns one best entry per query."""
    path = tmp_path / "hits.tsv"
    _write_hits_file(
        path,
        [
            "q1\ts1\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-30\t200\t100\t1000",
            "q1\ts2\t99.0\t100\t0\t0\t1\t100\t5\t104\t1e-40\t250\t100\t1000",
            "q2\ts3\t95.0\t90\t0\t0\t1\t90\t5\t94\t1e-20\t150\t90\t800",
            "q2\ts4\t95.0\t90\t0\t0\t1\t90\t5\t94\t1e-10\t140\t90\t700",
        ],
    )
    df = parse_blast_to_dataframe(path)
    best = select_best_hit_per_query(df, metric="bitscore", ascending=False)
    assert len(best) == 2
    assert set(best["sseqid"].tolist()) == {"s2", "s3"}


def test_prune_contained_intervals_removes_contained() -> None:
    """Contained intervals are removed from each query group."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 100, "sseqid": "a"},
            {"qseqid": "q1", "qstart": 20, "qend": 30, "sseqid": "b"},
        ]
    )
    pruned, removed = prune_contained_intervals(df)
    assert len(pruned) == 1
    assert pruned.iloc[0]["sseqid"] == "a"
    assert removed["q1"] == 1


def test_prune_contained_intervals_keeps_partial_overlaps() -> None:
    """Partially overlapping intervals are retained."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "a"},
            {"qseqid": "q1", "qstart": 40, "qend": 80, "sseqid": "b"},
        ]
    )
    pruned, removed = prune_contained_intervals(df)
    assert len(pruned) == 2
    assert removed["q1"] == 0


def test_prune_contained_intervals_handles_identical() -> None:
    """Identical intervals are preserved (NextEVE-compatible behavior)."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "a"},
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "b"},
        ]
    )
    pruned, removed = prune_contained_intervals(df)
    assert len(pruned) == 2
    assert removed["q1"] == 0


def test_prune_contained_intervals_equal_end_boundary() -> None:
    """Equal-end intervals prune only when the start is strictly larger."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "outer"},
            {"qseqid": "q1", "qstart": 20, "qend": 50, "sseqid": "inner"},
        ]
    )
    pruned, removed = prune_contained_intervals(df)
    assert len(pruned) == 1
    assert pruned.iloc[0]["sseqid"] == "outer"
    assert removed["q1"] == 1


def test_normalize_blast_strand_positive() -> None:
    """sstart < send remains unchanged with '+' strand."""
    hits = [
        BlastHit(
            qseqid="q1",
            sseqid="s1",
            pident=99.0,
            length=100,
            mismatch=0,
            gapopen=0,
            qstart=1,
            qend=100,
            sstart=10,
            send=80,
            evalue=1e-20,
            bitscore=200.0,
        )
    ]
    out = normalize_blast_strand(hits)
    assert isinstance(out, list)
    assert out[0].strand == "+"
    assert out[0].sstart == 10
    assert out[0].send == 80


def test_normalize_blast_strand_negative() -> None:
    """sstart > send is swapped with '-' strand."""
    hits = [
        BlastHit(
            qseqid="q1",
            sseqid="s1",
            pident=99.0,
            length=100,
            mismatch=0,
            gapopen=0,
            qstart=1,
            qend=100,
            sstart=80,
            send=10,
            evalue=1e-20,
            bitscore=200.0,
        )
    ]
    out = normalize_blast_strand(hits)
    assert isinstance(out, list)
    assert out[0].strand == "-"
    assert out[0].sstart == 10
    assert out[0].send == 80


def test_normalize_blast_strand_equal() -> None:
    """sstart == send is treated as '+' strand."""
    df = pd.DataFrame([{"sstart": 10, "send": 10, "qseqid": "q1", "sseqid": "s1"}])
    out = normalize_blast_strand(df)
    assert isinstance(out, pd.DataFrame)
    assert out.loc[0, "strand"] == "+"
    assert int(out.loc[0, "sstart"]) == 10
    assert int(out.loc[0, "send"]) == 10


def test_filter_hits_by_bitscore_fraction() -> None:
    """Bitscore fraction filtering retains top-scoring subset per query."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "bitscore": 100, "sseqid": "a"},
            {"qseqid": "q1", "bitscore": 95, "sseqid": "b"},
            {"qseqid": "q1", "bitscore": 80, "sseqid": "c"},
        ]
    )
    filtered = filter_hits_by_bitscore_fraction(df, top_fraction=0.9)
    assert set(filtered["sseqid"].tolist()) == {"a", "b"}


# --- classify.py tests ---

def test_classify_majority_rule() -> None:
    """Majority rule returns positive when most taxonomy values match keywords."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "sskingdoms": "Viruses", "stitle": "x"},
            {"qseqid": "q1", "sskingdoms": "Viruses", "stitle": "y"},
            {"qseqid": "q1", "sskingdoms": "Bacteria", "stitle": "z"},
        ]
    )
    out = classify_hits_by_taxonomy(df, taxonomy_col="sskingdoms", rule="majority", keywords=["virus"])
    assert out[0].classification == "positive"


def test_classify_majority_rule_negative() -> None:
    """Majority rule returns negative when most taxonomy values miss keywords."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "sskingdoms": "Bacteria", "stitle": "x"},
            {"qseqid": "q1", "sskingdoms": "Archaea", "stitle": "y"},
            {"qseqid": "q1", "sskingdoms": "Viruses", "stitle": "z"},
        ]
    )
    out = classify_hits_by_taxonomy(df, taxonomy_col="sskingdoms", rule="majority", keywords=["virus"])
    assert out[0].classification == "negative"


def test_classify_any_rule() -> None:
    """Any rule returns positive when at least one value matches keywords."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "sskingdoms": "Bacteria", "stitle": "x"},
            {"qseqid": "q1", "sskingdoms": "Viruses", "stitle": "y"},
        ]
    )
    out = classify_hits_by_taxonomy(df, taxonomy_col="sskingdoms", rule="any", keywords=["virus"])
    assert out[0].classification == "positive"


def test_classify_all_rule() -> None:
    """All rule returns negative when not all values match keywords."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "sskingdoms": "Viruses", "stitle": "x"},
            {"qseqid": "q1", "sskingdoms": "Bacteria", "stitle": "y"},
        ]
    )
    out = classify_hits_by_taxonomy(df, taxonomy_col="sskingdoms", rule="all", keywords=["virus"])
    assert out[0].classification == "negative"


def test_classify_keyword_fallback() -> None:
    """Keyword fallback classifies positive when title contains a keyword."""
    df = pd.DataFrame(
        [
            {"qseqid": "q1", "sskingdoms": "N/A", "stitle": "Tobacco mosaic virus"},
        ]
    )
    out = classify_hits_by_taxonomy(
        df,
        taxonomy_col="sskingdoms",
        rule="any",
        keywords=["virus"],
        keyword_fallback=True,
    )
    assert out[0].classification == "positive"
    assert out[0].keyword_match is True


def test_is_missing_taxonomy() -> None:
    """is_missing_taxonomy recognizes placeholder values."""
    assert is_missing_taxonomy(None)
    assert is_missing_taxonomy("")
    assert is_missing_taxonomy("N/A")
    assert is_missing_taxonomy("na")
    assert is_missing_taxonomy("0")
    assert is_missing_taxonomy("unclassified")
    assert not is_missing_taxonomy("Viruses")


def test_classify_missing_taxonomy_token_zero() -> None:
    """Token '0' is treated as missing taxonomy."""
    df = pd.DataFrame([{"qseqid": "q1", "sskingdoms": "0", "stitle": "Tobacco mosaic virus"}])
    out = classify_hits_by_taxonomy(
        df,
        taxonomy_col="sskingdoms",
        rule="any",
        keywords=["virus"],
        keyword_fallback=True,
    )
    assert out[0].classification == "positive"
    assert out[0].keyword_match is True


def test_matches_keywords() -> None:
    """matches_keywords performs case-insensitive substring matching."""
    assert matches_keywords("Tobacco mosaic virus", ["virus"])
    assert not matches_keywords("Homo sapiens", ["virus", "phage"])

# --- CLI tests ---

def test_search_cli_rejects_missing_config(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """search CLI exits with code 1 when config file does not exist."""
    monkeypatch.setattr("sys.argv", ["nevelib-search", "/nonexistent.yaml"])

    with pytest.raises(SystemExit) as exc:
        search_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "config file not found" in captured.err


def test_search_cli_prints_usage_on_help(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """search CLI prints usage and exits 0 on --help."""
    monkeypatch.setattr("sys.argv", ["nevelib-search", "--help"])

    with pytest.raises(SystemExit) as exc:
        search_cli.main()

    captured = capsys.readouterr()
    assert exc.value.code == 0
    assert "Usage: nevelib-search <config.yaml>" in captured.err
