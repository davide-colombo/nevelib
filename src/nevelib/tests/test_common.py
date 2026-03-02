"""Tests for implemented nevelib._common helpers used in this phase."""

from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

from nevelib._common.blast_db import validate_blast_db
from nevelib._common.compression import CompressionConfig, compress, decompress, validate_gzip
from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import iter_fasta_records, validate_fasta, write_fasta
from nevelib._common.toolrun import check_tool, run_tool
from nevelib._common.tsv import validate_tsv


def test_validate_fasta_rejects_missing_file(tmp_path: Path) -> None:
    """Missing FASTA path returns invalid validation result."""
    result = validate_fasta(tmp_path / "missing.fasta")
    assert result.valid is False
    assert result.errors


def test_validate_fasta_rejects_empty_file(tmp_path: Path) -> None:
    """Empty FASTA fails non-empty validation."""
    path = tmp_path / "empty.fasta"
    path.write_text("", encoding="utf-8")

    result = validate_fasta(path, check_nonempty=True)
    assert result.valid is False
    assert any("minimum required" in err for err in result.errors)


def test_validate_fasta_accepts_valid_file(tmp_path: Path) -> None:
    """Minimal valid FASTA passes validation with correct record count."""
    path = tmp_path / "ok.fasta"
    path.write_text(">id1\nACGT\n>id2\nTTAA\n", encoding="utf-8")

    result = validate_fasta(path)
    assert result.valid is True
    assert result.record_count == 2


def test_validate_fasta_detects_duplicate_ids(tmp_path: Path) -> None:
    """Duplicate FASTA IDs are reported as warnings."""
    path = tmp_path / "dup.fasta"
    path.write_text(">id1\nACGT\n>id1\nTTAA\n", encoding="utf-8")

    result = validate_fasta(path, check_duplicates=True)
    assert result.valid is True
    assert any("duplicate" in warning.lower() for warning in result.warnings)


def test_iter_fasta_records_parses_multiline_sequences(tmp_path: Path) -> None:
    """Multiline sequences are concatenated correctly by the parser."""
    path = tmp_path / "multi.fasta"
    path.write_text(">r1\nAC\nGT\n>r2\nTT\nAA\n", encoding="utf-8")

    records = list(iter_fasta_records(path))
    assert records == [("r1", "ACGT"), ("r2", "TTAA")]


def test_write_fasta_roundtrip(tmp_path: Path) -> None:
    """Writing then reading FASTA preserves record content."""
    path = tmp_path / "roundtrip.fasta"
    source = [("a", "ACGT"), ("b", "TTAA")]

    written = write_fasta(iter(source), path)
    observed = list(iter_fasta_records(path))

    assert written == len(source)
    assert observed == source


def test_write_fasta_wraps_at_configured_width(tmp_path: Path) -> None:
    """Sequence lines obey the configured wrapping width."""
    path = tmp_path / "wrapped.fasta"
    write_fasta(iter([("x", "A" * 135)]), path, wrap_width=60)

    lines = path.read_text(encoding="utf-8").splitlines()
    seq_lines = [line for line in lines if not line.startswith(">")]
    assert seq_lines
    assert all(len(line) <= 60 for line in seq_lines)


def test_check_tool_finds_python() -> None:
    """check_tool reports python3 as available in this environment."""
    info = check_tool("python3")
    assert info.available is True
    assert info.path is not None


def test_check_tool_returns_unavailable_for_nonexistent() -> None:
    """check_tool reports unavailable for a fake executable name."""
    info = check_tool("nonexistent_binary_xyz")
    assert info.available is False
    assert info.path is None


def test_run_tool_captures_stdout() -> None:
    """run_tool captures stdout when no log files are configured."""
    proc = run_tool(["echo", "hello"], check=True)
    assert proc.returncode == 0
    assert (proc.stdout or "").strip() == "hello"


def test_run_tool_raises_on_nonzero_exit() -> None:
    """run_tool raises CalledProcessError on non-zero exit with check=True."""
    with pytest.raises(subprocess.CalledProcessError):
        run_tool(["/bin/sh", "-c", "exit 5"], check=True)


def test_run_tool_writes_log_files(tmp_path: Path) -> None:
    """run_tool writes stdout/stderr streams to requested log files."""
    out_log = tmp_path / "out.log"
    err_log = tmp_path / "err.log"

    proc = run_tool(
        ["python3", "-c", "import sys; print('OUT'); print('ERR', file=sys.stderr)"],
        out_log=out_log,
        err_log=err_log,
        check=True,
    )

    assert proc.returncode == 0
    assert out_log.exists()
    assert err_log.exists()
    assert "OUT" in out_log.read_text(encoding="utf-8")
    assert "ERR" in err_log.read_text(encoding="utf-8")


def test_load_config_valid_yaml(tmp_path: Path) -> None:
    """load_config parses valid YAML into a dictionary."""
    cfg_path = tmp_path / "cfg.yaml"
    cfg_path.write_text("alpha: 1\nbeta:\n  gamma: true\n", encoding="utf-8")

    cfg = load_config(cfg_path)
    assert cfg["alpha"] == 1
    assert cfg["beta"]["gamma"] is True


def test_load_config_invalid_yaml(tmp_path: Path) -> None:
    """load_config raises ValueError on malformed YAML input."""
    cfg_path = tmp_path / "bad.yaml"
    cfg_path.write_text("alpha: [1, 2\n", encoding="utf-8")

    with pytest.raises(ValueError):
        load_config(cfg_path)


def test_merge_defaults_user_wins() -> None:
    """User values override defaults during merge."""
    defaults = {"threads": 4, "mode": "fast"}
    user_cfg = {"threads": 8}

    merged = merge_defaults(user_cfg, defaults)
    assert merged["threads"] == 8
    assert merged["mode"] == "fast"


def test_merge_defaults_nested_merge() -> None:
    """Nested dictionaries are merged recursively instead of replaced."""
    defaults = {"a": {"x": 1, "y": 2}, "b": 3}
    user_cfg = {"a": {"x": 9}}

    merged = merge_defaults(user_cfg, defaults)
    assert merged["a"]["x"] == 9
    assert merged["a"]["y"] == 2
    assert merged["b"] == 3


def test_validate_required_keys_raises_on_missing() -> None:
    """Missing required keys trigger ValueError."""
    with pytest.raises(ValueError, match="missing required keys"):
        validate_required_keys({"a": 1}, ["a", "b"], context="cfg")


def test_validate_required_keys_raises_on_placeholder() -> None:
    """Placeholder values trigger ValueError."""
    with pytest.raises(ValueError, match="placeholder"):
        validate_required_keys({"path": "/path/to/..."}, ["path"], context="cfg")


def test_validate_blast_db_valid_nucl(tmp_path: Path) -> None:
    """Nucleotide BLAST DB with core sidecars validates successfully."""
    prefix = tmp_path / "db" / "core"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".nin").write_text("", encoding="utf-8")
    prefix.with_suffix(".nsq").write_text("", encoding="utf-8")
    prefix.with_suffix(".nhr").write_text("", encoding="utf-8")

    result = validate_blast_db(prefix, db_type="nucl")
    assert result.valid is True


def test_validate_blast_db_missing_files(tmp_path: Path) -> None:
    """Incomplete BLAST DB sidecars fail validation."""
    prefix = tmp_path / "db" / "core"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".nin").write_text("", encoding="utf-8")

    result = validate_blast_db(prefix, db_type="nucl")
    assert result.valid is False
    assert result.errors


def test_validate_blast_db_taxonomy_present(tmp_path: Path) -> None:
    """Taxonomy sidecar files are detected when present."""
    prefix = tmp_path / "db" / "core"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".nin").write_text("", encoding="utf-8")
    prefix.with_suffix(".nsq").write_text("", encoding="utf-8")
    prefix.with_suffix(".nhr").write_text("", encoding="utf-8")
    (prefix.parent / "taxdb.bti").write_text("", encoding="utf-8")
    (prefix.parent / "taxdb.btd").write_text("", encoding="utf-8")

    result = validate_blast_db(prefix, db_type="nucl")
    assert result.has_taxonomy is True


def test_validate_blast_db_taxonomy_missing_when_required(tmp_path: Path) -> None:
    """Validation fails when taxonomy is required but missing."""
    prefix = tmp_path / "db" / "core"
    prefix.parent.mkdir(parents=True, exist_ok=True)
    prefix.with_suffix(".nin").write_text("", encoding="utf-8")
    prefix.with_suffix(".nsq").write_text("", encoding="utf-8")
    prefix.with_suffix(".nhr").write_text("", encoding="utf-8")

    result = validate_blast_db(prefix, db_type="nucl", require_taxonomy=True)
    assert result.valid is False
    assert any("taxonomy" in err.lower() for err in result.errors)


def test_validate_tsv_valid_file(tmp_path: Path) -> None:
    """TSV with required columns and rows validates successfully."""
    path = tmp_path / "table.tsv"
    path.write_text("a\tb\n1\t2\n3\t4\n5\t6\n", encoding="utf-8")

    result = validate_tsv(path, required_columns=["a", "b"])
    assert result.valid is True
    assert result.row_count == 3


def test_validate_tsv_missing_columns(tmp_path: Path) -> None:
    """TSV validation fails when required columns are missing."""
    path = tmp_path / "table.tsv"
    path.write_text("a\tb\n1\t2\n", encoding="utf-8")

    result = validate_tsv(path, required_columns=["a", "c"])
    assert result.valid is False
    assert any("missing required columns" in err.lower() for err in result.errors)


def test_validate_tsv_empty_file(tmp_path: Path) -> None:
    """Header-only TSV fails non-empty validation."""
    path = tmp_path / "table.tsv"
    path.write_text("a\tb\n", encoding="utf-8")

    result = validate_tsv(path, check_nonempty=True)
    assert result.valid is False
    assert result.row_count == 0


def test_validate_gzip_detects_standard_gzip(tmp_path: Path) -> None:
    """Gzip detector identifies valid gzip archives."""
    import gzip

    gz_path = tmp_path / "file.txt.gz"
    with gzip.open(gz_path, "wb") as handle:
        handle.write(b"hello\n")

    assert validate_gzip(gz_path) == "gzip"


def test_validate_gzip_rejects_non_gzip(tmp_path: Path) -> None:
    """Non-gzip files raise ValueError."""
    text_path = tmp_path / "plain.txt"
    text_path.write_text("plain\n", encoding="utf-8")

    with pytest.raises(ValueError):
        validate_gzip(text_path)


def test_compress_decompress_roundtrip(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """compress/decompress roundtrip preserves file content."""
    import gzip

    src = tmp_path / "input.txt"
    src.write_text("alpha\nbeta\n", encoding="utf-8")
    gz = tmp_path / "input.txt.gz"
    out = tmp_path / "output.txt"

    def _fake_check_tool(name: str, **_kwargs: object):
        return type("T", (), {"available": True, "path": Path(f"/usr/bin/{name}")})()

    def _fake_run_tool(cmd, **_kwargs):
        if not isinstance(cmd, str):
            raise AssertionError("Expected shell command string.")
        marker = "< '"
        if marker not in cmd or "' > '" not in cmd:
            raise AssertionError(f"Unexpected command format: {cmd}")
        src_part = cmd.split("< '", 1)[1].split("'", 1)[0]
        dst_part = cmd.split("' > '", 1)[1].split("'", 1)[0]
        src_path = Path(src_part)
        dst_path = Path(dst_part)

        if " -d " in cmd:
            with gzip.open(src_path, "rb") as in_fh, dst_path.open("wb") as out_fh:
                out_fh.write(in_fh.read())
        else:
            with src_path.open("rb") as in_fh, gzip.open(dst_path, "wb") as out_fh:
                out_fh.write(in_fh.read())
        return subprocess.CompletedProcess(args=["mock"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr("nevelib._common.compression.check_tool", _fake_check_tool)
    monkeypatch.setattr("nevelib._common.compression.run_tool", _fake_run_tool)

    cfg = CompressionConfig(compressor="pigz", fallback="gzip")
    compress(src, gz, cfg)
    decompress(gz, out, cfg)
    assert out.read_text(encoding="utf-8") == src.read_text(encoding="utf-8")
