"""Tests for nevelib.assembly module."""

from __future__ import annotations

import gzip
from pathlib import Path
import subprocess

import pytest

from nevelib._common.toolrun import ToolInfo
from nevelib.assembly import cli as assembly_cli
from nevelib.assembly.assemble import AssemblyConfig, assemble_reads
from nevelib.assembly.coverage import CoverageFilterConfig, filter_by_coverage
from nevelib.assembly.dedup import DedupConfig, deduplicate_contigs
from nevelib.assembly.normalize import NormalizeConfig, normalize_pairs


def _write_fastq(path: Path, records: list[tuple[str, str, str]]) -> None:
    """Write a plain or gzipped FASTQ file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", encoding="utf-8") as handle:
        for header, seq, qual in records:
            handle.write(f"@{header}\n{seq}\n+\n{qual}\n")


def _write_fasta(path: Path, records: list[tuple[str, str]]) -> None:
    """Write FASTA records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    for rec_id, seq in records:
        lines.append(f">{rec_id}")
        lines.append(seq)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- normalize.py ---

def test_normalize_config_defaults() -> None:
    """NormalizeConfig defaults are sensible."""
    cfg = NormalizeConfig()
    assert cfg.bbnorm_exec == "bbnorm.sh"
    assert cfg.target_coverage == 100
    assert cfg.min_depth == 5
    assert cfg.threads == 8
    assert cfg.memory == "8g"
    assert cfg.extra_args is None


def test_normalize_pairs_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """normalize_pairs builds expected bbnorm command arguments."""
    r1_in = tmp_path / "R1.fastq.gz"
    r2_in = tmp_path / "R2.fastq.gz"
    r1_out = tmp_path / "R1.norm.fastq.gz"
    r2_out = tmp_path / "R2.norm.fastq.gz"

    _write_fastq(r1_in, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2_in, [("x/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        assert isinstance(cmd, list)
        seen["cmd"] = cmd
        _write_fastq(r1_out, [("x/1", "ACGT", "IIII")])
        _write_fastq(r2_out, [("x/2", "TGCA", "IIII")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.normalize.check_tool",
        lambda *_a, **_k: ToolInfo(name="bbnorm.sh", available=True, path=Path("/usr/bin/bbnorm.sh")),
    )
    monkeypatch.setattr("nevelib.assembly.normalize.run_tool", _fake_run_tool)

    normalize_pairs(r1_in, r2_in, r1_out, r2_out, NormalizeConfig())

    cmd = seen["cmd"]
    assert cmd[0] == "bbnorm.sh"
    assert f"in={r1_in}" in cmd
    assert f"in2={r2_in}" in cmd
    assert f"out={r1_out}" in cmd
    assert f"out2={r2_out}" in cmd
    assert "target=100" in cmd
    assert "mindepth=5" in cmd


def test_normalize_pairs_rejects_missing_input(tmp_path: Path) -> None:
    """normalize_pairs fails when input FASTQ files are missing."""
    with pytest.raises(ValueError, match="Invalid r1 FASTQ"):
        normalize_pairs(
            tmp_path / "missing_r1.fastq.gz",
            tmp_path / "missing_r2.fastq.gz",
            tmp_path / "out_r1.fastq.gz",
            tmp_path / "out_r2.fastq.gz",
            NormalizeConfig(),
        )


def test_normalize_pairs_with_extra_args(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """normalize_pairs appends extra_args to the command."""
    r1_in = tmp_path / "R1.fastq.gz"
    r2_in = tmp_path / "R2.fastq.gz"
    r1_out = tmp_path / "R1.norm.fastq.gz"
    r2_out = tmp_path / "R2.norm.fastq.gz"

    _write_fastq(r1_in, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2_in, [("x/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fastq(r1_out, [("x/1", "ACGT", "IIII")])
        _write_fastq(r2_out, [("x/2", "TGCA", "IIII")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.normalize.check_tool",
        lambda *_a, **_k: ToolInfo(name="bbnorm.sh", available=True, path=Path("/usr/bin/bbnorm.sh")),
    )
    monkeypatch.setattr("nevelib.assembly.normalize.run_tool", _fake_run_tool)

    cfg = NormalizeConfig(extra_args=["passes=2", "prefilter=t"])
    normalize_pairs(r1_in, r2_in, r1_out, r2_out, cfg)

    cmd = seen["cmd"]
    assert "passes=2" in cmd
    assert "prefilter=t" in cmd


# --- assemble.py ---

def test_assembly_config_defaults() -> None:
    """AssemblyConfig defaults are sensible."""
    cfg = AssemblyConfig()
    assert cfg.spades_exec == "spades.py"
    assert cfg.kmers is None
    assert cfg.threads == 8
    assert cfg.memory == 16
    assert cfg.careful is True
    assert cfg.only_assembler is False
    assert cfg.extra_args is None


def test_assemble_reads_builds_correct_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assemble_reads builds expected SPAdes command arguments."""
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    singleton = tmp_path / "singletons.fastq.gz"
    outdir = tmp_path / "spades"

    _write_fastq(r1, [("a/1", "ACGT", "IIII")])
    _write_fastq(r2, [("a/2", "TGCA", "IIII")])
    _write_fastq(singleton, [("s1", "AAAA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fasta(outdir / "contigs.fasta", [("c1", "ACGT")])
        _write_fasta(outdir / "scaffolds.fasta", [("s1", "ACGT")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.assemble.check_tool",
        lambda *_a, **_k: ToolInfo(name="spades.py", available=True, path=Path("/usr/bin/spades.py")),
    )
    monkeypatch.setattr("nevelib.assembly.assemble.run_tool", _fake_run_tool)

    assemble_reads(r1, r2, singleton, outdir, AssemblyConfig())

    cmd = seen["cmd"]
    assert cmd[0] == "spades.py"
    assert "-1" in cmd and str(r1) in cmd
    assert "-2" in cmd and str(r2) in cmd
    assert "-o" in cmd and str(outdir) in cmd
    assert "-t" in cmd and "8" in cmd
    assert "-m" in cmd and "16" in cmd


def test_assemble_reads_with_kmers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assemble_reads includes custom k-mer list when configured."""
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    outdir = tmp_path / "spades"
    _write_fastq(r1, [("a/1", "ACGT", "IIII")])
    _write_fastq(r2, [("a/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fasta(outdir / "contigs.fasta", [("c1", "ACGT")])
        _write_fasta(outdir / "scaffolds.fasta", [("s1", "ACGT")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.assemble.check_tool",
        lambda *_a, **_k: ToolInfo(name="spades.py", available=True, path=Path("/usr/bin/spades.py")),
    )
    monkeypatch.setattr("nevelib.assembly.assemble.run_tool", _fake_run_tool)

    cfg = AssemblyConfig(kmers=[21, 33, 55])
    assemble_reads(r1, r2, None, outdir, cfg)

    cmd = seen["cmd"]
    assert "-k" in cmd
    assert "21,33,55" in cmd


def test_assemble_reads_careful_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assemble_reads adds --careful when careful=True."""
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    outdir = tmp_path / "spades"
    _write_fastq(r1, [("a/1", "ACGT", "IIII")])
    _write_fastq(r2, [("a/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fasta(outdir / "contigs.fasta", [("c1", "ACGT")])
        _write_fasta(outdir / "scaffolds.fasta", [("s1", "ACGT")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.assemble.check_tool",
        lambda *_a, **_k: ToolInfo(name="spades.py", available=True, path=Path("/usr/bin/spades.py")),
    )
    monkeypatch.setattr("nevelib.assembly.assemble.run_tool", _fake_run_tool)

    assemble_reads(r1, r2, None, outdir, AssemblyConfig(careful=True))
    assert "--careful" in seen["cmd"]


def test_assemble_reads_without_singleton(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assemble_reads omits singleton flag when singleton is None."""
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    outdir = tmp_path / "spades"
    _write_fastq(r1, [("a/1", "ACGT", "IIII")])
    _write_fastq(r2, [("a/2", "TGCA", "IIII")])

    seen: dict[str, list[str]] = {}

    def _fake_run_tool(cmd, **_kwargs):
        seen["cmd"] = cmd
        _write_fasta(outdir / "contigs.fasta", [("c1", "ACGT")])
        _write_fasta(outdir / "scaffolds.fasta", [("s1", "ACGT")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.assemble.check_tool",
        lambda *_a, **_k: ToolInfo(name="spades.py", available=True, path=Path("/usr/bin/spades.py")),
    )
    monkeypatch.setattr("nevelib.assembly.assemble.run_tool", _fake_run_tool)

    assemble_reads(r1, r2, None, outdir, AssemblyConfig())
    assert "-s" not in seen["cmd"]


def test_assemble_reads_counts_output_contigs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """assemble_reads reports contig/scaffold counts from output FASTAs."""
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    outdir = tmp_path / "spades"
    _write_fastq(r1, [("a/1", "ACGT", "IIII")])
    _write_fastq(r2, [("a/2", "TGCA", "IIII")])

    def _fake_run_tool(cmd, **_kwargs):
        _write_fasta(outdir / "contigs.fasta", [("c1", "ACGT"), ("c2", "GGGG")])
        _write_fasta(outdir / "scaffolds.fasta", [("s1", "ACGT")])
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.assemble.check_tool",
        lambda *_a, **_k: ToolInfo(name="spades.py", available=True, path=Path("/usr/bin/spades.py")),
    )
    monkeypatch.setattr("nevelib.assembly.assemble.run_tool", _fake_run_tool)

    result = assemble_reads(r1, r2, None, outdir, AssemblyConfig())
    assert result.n_contigs == 2
    assert result.n_scaffolds == 1


# --- coverage.py ---

def test_coverage_filter_config_defaults() -> None:
    """CoverageFilterConfig defaults are sensible."""
    cfg = CoverageFilterConfig()
    assert cfg.samtools_exec == "samtools"
    assert cfg.minimap2_exec == "minimap2"
    assert cfg.mosdepth_exec == "mosdepth"
    assert cfg.threads == 8
    assert cfg.min_mean_coverage == 5.0
    assert cfg.minimap2_preset == "sr"
    assert cfg.mosdepth_window == 0


def test_filter_by_coverage_builds_minimap2_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """filter_by_coverage emits minimap2 mapping command."""
    contigs = tmp_path / "contigs.fasta"
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    out = tmp_path / "filtered.fasta"
    workdir = tmp_path / "work"

    _write_fasta(contigs, [("c1", "ACGT"), ("c2", "GGGG")])
    _write_fastq(r1, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2, [("x/2", "TGCA", "IIII")])

    calls: list[list[str] | str] = []

    def _fake_run_tool(cmd, **_kwargs):
        calls.append(cmd)
        if isinstance(cmd, list) and cmd and cmd[0] == "mosdepth":
            summary = workdir / "coverage.mosdepth.summary.txt"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text(
                "c1\t4\t16\t8.0\n"
                "c2\t4\t20\t6.0\n"
                "total\t8\t36\t7.0\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.coverage.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.coverage.run_tool", _fake_run_tool)

    filter_by_coverage(contigs, r1, r2, None, out, workdir, CoverageFilterConfig())

    assert any(
        isinstance(cmd, str)
        and "minimap2" in cmd
        and "samtools sort" in cmd
        and str(contigs) in cmd
        and str(r1) in cmd
        and str(r2) in cmd
        for cmd in calls
    )


def test_filter_by_coverage_parses_mosdepth_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """filter_by_coverage computes pass/fail counts from mosdepth summary."""
    contigs = tmp_path / "contigs.fasta"
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    out = tmp_path / "filtered.fasta"
    workdir = tmp_path / "work"

    _write_fasta(contigs, [("c1", "ACGT"), ("c2", "GGGG"), ("c3", "TTTT")])
    _write_fastq(r1, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2, [("x/2", "TGCA", "IIII")])

    def _fake_run_tool(cmd, **_kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "mosdepth":
            summary = workdir / "coverage.mosdepth.summary.txt"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text(
                "c1\t4\t16\t7.0\n"
                "c2\t4\t20\t6.5\n"
                "c3\t4\t4\t1.0\n"
                "total\t12\t40\t4.8\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.coverage.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.coverage.run_tool", _fake_run_tool)

    result = filter_by_coverage(
        contigs,
        r1,
        r2,
        None,
        out,
        workdir,
        CoverageFilterConfig(min_mean_coverage=5.0),
    )

    assert result.n_input == 3
    assert result.n_passing == 2
    assert result.n_removed == 1


def test_filter_by_coverage_writes_passing_contigs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Output FASTA contains only contigs passing coverage threshold."""
    contigs = tmp_path / "contigs.fasta"
    r1 = tmp_path / "R1.fastq.gz"
    r2 = tmp_path / "R2.fastq.gz"
    out = tmp_path / "filtered.fasta"
    workdir = tmp_path / "work"

    _write_fasta(contigs, [("c1", "ACGT"), ("c2", "GGGG"), ("c3", "TTTT")])
    _write_fastq(r1, [("x/1", "ACGT", "IIII")])
    _write_fastq(r2, [("x/2", "TGCA", "IIII")])

    def _fake_run_tool(cmd, **_kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "mosdepth":
            summary = workdir / "coverage.mosdepth.summary.txt"
            summary.parent.mkdir(parents=True, exist_ok=True)
            summary.write_text(
                "c1\t4\t16\t8.0\n"
                "c2\t4\t20\t6.0\n"
                "c3\t4\t4\t1.0\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.coverage.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.coverage.run_tool", _fake_run_tool)

    filter_by_coverage(
        contigs,
        r1,
        r2,
        None,
        out,
        workdir,
        CoverageFilterConfig(min_mean_coverage=5.0),
    )

    text = out.read_text(encoding="utf-8")
    assert ">c1" in text
    assert ">c2" in text
    assert ">c3" not in text


# --- dedup.py ---

def test_dedup_config_defaults() -> None:
    """DedupConfig defaults are sensible."""
    cfg = DedupConfig()
    assert cfg.blastn_exec == "blastn"
    assert cfg.makeblastdb_exec == "makeblastdb"
    assert cfg.evalue == 1e-10
    assert cfg.pident_min == 95.0
    assert cfg.min_coverage_fraction == 0.95
    assert cfg.threads == 4


def test_deduplicate_builds_makeblastdb_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """deduplicate_contigs runs makeblastdb with expected arguments."""
    input_fasta = tmp_path / "contigs.fasta"
    output_fasta = tmp_path / "dedup.fasta"
    _write_fasta(input_fasta, [("c1", "ACGT"), ("c2", "ACGA")])

    calls: list[list[str] | str] = []

    def _fake_run_tool(cmd, **_kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.dedup.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.dedup.run_tool", _fake_run_tool)

    deduplicate_contigs(input_fasta, output_fasta, DedupConfig(), workdir=tmp_path / "work")

    makeblastdb_cmd = calls[0]
    assert isinstance(makeblastdb_cmd, list)
    assert makeblastdb_cmd[0] == "makeblastdb"
    assert "-in" in makeblastdb_cmd and str(input_fasta) in makeblastdb_cmd
    assert "-dbtype" in makeblastdb_cmd and "nucl" in makeblastdb_cmd


def test_deduplicate_builds_blastn_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """deduplicate_contigs runs blastn with expected self-search options."""
    input_fasta = tmp_path / "contigs.fasta"
    output_fasta = tmp_path / "dedup.fasta"
    _write_fasta(input_fasta, [("c1", "ACGT"), ("c2", "ACGA")])

    calls: list[list[str] | str] = []

    def _fake_run_tool(cmd, **_kwargs):
        calls.append(cmd)
        if isinstance(cmd, list) and cmd and cmd[0] == "blastn":
            out_path = Path(cmd[cmd.index("-out") + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text("", encoding="utf-8")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.dedup.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.dedup.run_tool", _fake_run_tool)

    deduplicate_contigs(input_fasta, output_fasta, DedupConfig(), workdir=tmp_path / "work")

    blastn_cmd = calls[1]
    assert isinstance(blastn_cmd, list)
    assert blastn_cmd[0] == "blastn"
    assert "-query" in blastn_cmd and str(input_fasta) in blastn_cmd
    assert "-outfmt" in blastn_cmd
    assert "-num_threads" in blastn_cmd


def test_deduplicate_removes_contained_contigs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contained contigs are removed from the deduplicated output."""
    input_fasta = tmp_path / "contigs.fasta"
    output_fasta = tmp_path / "dedup.fasta"
    _write_fasta(
        input_fasta,
        [
            ("c1", "A" * 120),
            ("c2", "A" * 100),
            ("c3", "A" * 90),
        ],
    )

    def _fake_run_tool(cmd, **_kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "blastn":
            out_path = Path(cmd[cmd.index("-out") + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                "c2\tc1\t99.0\t100\t100\t120\t1\t100\t1\t100\t1e-40\t500\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.dedup.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.dedup.run_tool", _fake_run_tool)

    result = deduplicate_contigs(input_fasta, output_fasta, DedupConfig(), workdir=tmp_path / "work")

    assert result.n_removed == 1
    assert result.removed_ids == ["c2"]
    text = output_fasta.read_text(encoding="utf-8")
    assert ">c1" in text and ">c3" in text
    assert ">c2" not in text


def test_deduplicate_keeps_longer_of_mutual_containment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mutual containment retains the longer contig deterministically."""
    input_fasta = tmp_path / "contigs.fasta"
    output_fasta = tmp_path / "dedup.fasta"
    _write_fasta(input_fasta, [("long", "A" * 120), ("short", "A" * 100)])

    def _fake_run_tool(cmd, **_kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "blastn":
            out_path = Path(cmd[cmd.index("-out") + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                "short\tlong\t99.9\t100\t100\t120\t1\t100\t1\t100\t1e-50\t600\n"
                "long\tshort\t99.9\t100\t120\t100\t1\t100\t1\t100\t1e-50\t600\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.dedup.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.dedup.run_tool", _fake_run_tool)

    result = deduplicate_contigs(input_fasta, output_fasta, DedupConfig(), workdir=tmp_path / "work")

    assert result.n_removed == 1
    assert result.removed_ids == ["short"]
    text = output_fasta.read_text(encoding="utf-8")
    assert ">long" in text
    assert ">short" not in text


def test_deduplicate_no_self_hits(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Self-hits are ignored and do not remove any contig."""
    input_fasta = tmp_path / "contigs.fasta"
    output_fasta = tmp_path / "dedup.fasta"
    _write_fasta(input_fasta, [("c1", "AAAA"), ("c2", "TTTT")])

    def _fake_run_tool(cmd, **_kwargs):
        if isinstance(cmd, list) and cmd and cmd[0] == "blastn":
            out_path = Path(cmd[cmd.index("-out") + 1])
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                "c1\tc1\t100.0\t4\t4\t4\t1\t4\t1\t4\t1e-5\t30\n"
                "c2\tc2\t100.0\t4\t4\t4\t1\t4\t1\t4\t1e-5\t30\n",
                encoding="utf-8",
            )
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(
        "nevelib.assembly.dedup.check_tool",
        lambda name, **_k: ToolInfo(name=name, available=True, path=Path(f"/usr/bin/{name}")),
    )
    monkeypatch.setattr("nevelib.assembly.dedup.run_tool", _fake_run_tool)

    result = deduplicate_contigs(input_fasta, output_fasta, DedupConfig(), workdir=tmp_path / "work")

    assert result.n_removed == 0
    assert result.removed_ids == []
    text = output_fasta.read_text(encoding="utf-8")
    assert ">c1" in text and ">c2" in text


# --- CLI ---

def test_assembly_cli_rejects_missing_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """assembly CLI exits with code 1 for missing config path."""
    monkeypatch.setattr("sys.argv", ["nevelib-assembly", "/nonexistent.yaml"])
    with pytest.raises(SystemExit) as exc:
        assembly_cli.main()
    assert exc.value.code == 1


def test_assembly_cli_prints_usage_on_help(monkeypatch: pytest.MonkeyPatch) -> None:
    """assembly CLI exits with code 0 on --help."""
    monkeypatch.setattr("sys.argv", ["nevelib-assembly", "--help"])
    with pytest.raises(SystemExit) as exc:
        assembly_cli.main()
    assert exc.value.code == 0
