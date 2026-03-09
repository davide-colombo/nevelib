"""CLI entry point for the nevelib assembly module.

Usage:
    nevelib-assembly config.yaml
"""

from __future__ import annotations

import logging
import shutil
import sys
from pathlib import Path

from nevelib._common.compression import CompressionConfig
from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import validate_fasta
from nevelib._common.fastq import validate_fastq
from nevelib.assembly.assemble import AssemblyConfig, assemble_reads
from nevelib.assembly.coverage import CoverageFilterConfig, filter_by_coverage
from nevelib.assembly.dedup import DedupConfig, deduplicate_contigs
from nevelib.assembly.normalize import NormalizeConfig, normalize_pairs


_DEFAULTS: dict = {
    "input": {
        "r1": "",
        "r2": "",
        "singleton": None,
    },
    "output": {
        "dir": "./assembly_output",
    },
    "normalization": {
        "enabled": True,
        "bbnorm": "bbnorm.sh",
        "target_coverage": 100,
        "min_depth": 5,
        "threads": 8,
        "memory": "8g",
        "seed": None,
        "extra_args": None,
    },
    "assembly": {
        "spades": "spades.py",
        "kmers": None,
        "threads": 8,
        "memory": 16,
        "careful": True,
        "only_assembler": False,
        "extra_args": None,
    },
    "coverage_filter": {
        "enabled": True,
        "samtools": "samtools",
        "minimap2": "minimap2",
        "mosdepth": "mosdepth",
        "threads": 8,
        "min_mean_coverage": 5.0,
        "minimap2_preset": "sr",
        "mosdepth_window": 100,
    },
    "deduplication": {
        "enabled": True,
        "blastn": "blastn",
        "makeblastdb": "makeblastdb",
        "evalue": 1e-20,
        "task": "megablast",
        "word_size": 28,
        "perc_identity": 100.0,
        "qcov_hsp_perc": 100.0,
        "max_target_seqs": 100,
        "threads": 8,
        "extra_args": None,
    },
    "compression": {
        "compressor": "pigz",
        "threads": 4,
        "level": 6,
        "fallback": "gzip",
    },
    "validation": {
        "skip_input": False,
        "skip_output": False,
        "strict": True,
    },
}


def _parse_kmers(value: object) -> list[int] | None:
    """Parse k-mer configuration from YAML values."""
    if value is None:
        return None
    if isinstance(value, str):
        tokens = [part.strip() for part in value.split(",") if part.strip()]
        return [int(token) for token in tokens] if tokens else None
    if isinstance(value, (list, tuple)):
        parsed = [int(v) for v in value]
        return parsed or None
    raise ValueError(f"Invalid kmers value: {value!r}")


def _validate_input_fastq(path: Path, label: str, *, min_reads: int = 1) -> None:
    """Validate FASTQ input and raise ValueError on failure."""
    result = validate_fastq(path, check_gzip=True, check_nonempty=True, min_reads=min_reads)
    if not result.valid:
        raise ValueError(f"Invalid {label} FASTQ: " + "; ".join(result.errors))


def main() -> None:
    """Entry point: load config YAML and run assembly pipeline steps."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-assembly <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.assembly")

    try:
        user_cfg = load_config(config_path)
        cfg = merge_defaults(user_cfg, _DEFAULTS)
        validate_required_keys(cfg["input"], ["r1", "r2"], context="input")
    except Exception as exc:
        logger.error("Configuration error: %s", exc)
        sys.exit(1)

    input_r1 = Path(cfg["input"]["r1"])
    input_r2 = Path(cfg["input"]["r2"])
    singleton_raw = cfg["input"].get("singleton")
    input_singleton = Path(singleton_raw) if singleton_raw else None

    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    if not cfg["validation"]["skip_input"]:
        try:
            logger.info("Validating input FASTQ files")
            _validate_input_fastq(input_r1, "r1")
            _validate_input_fastq(input_r2, "r2")
            if input_singleton is not None and input_singleton.exists():
                singleton_result = validate_fastq(
                    input_singleton,
                    check_gzip=True,
                    check_nonempty=False,
                    min_reads=0,
                )
                if not singleton_result.valid:
                    raise ValueError("Invalid singleton FASTQ: " + "; ".join(singleton_result.errors))
        except Exception as exc:
            logger.error("Input validation failed: %s", exc)
            sys.exit(1)

    current_r1 = input_r1
    current_r2 = input_r2

    compression_cfg_raw = cfg.get("compression", {})
    compression_cfg = CompressionConfig(
        compressor=compression_cfg_raw.get("compressor", "pigz"),
        threads=int(compression_cfg_raw.get("threads", 4)),
        level=int(compression_cfg_raw.get("level", 6)),
        fallback=compression_cfg_raw.get("fallback", "gzip"),
    )
    logger.debug("Compression config loaded: %s", compression_cfg)

    norm_cfg_raw = cfg["normalization"]
    if norm_cfg_raw.get("enabled", True):
        norm_dir = output_dir / "normalized"
        norm_r1 = norm_dir / "R1.normalized.fastq.gz"
        norm_r2 = norm_dir / "R2.normalized.fastq.gz"
        norm_cfg = NormalizeConfig(
            bbnorm_exec=norm_cfg_raw["bbnorm"],
            target_coverage=int(norm_cfg_raw["target_coverage"]),
            min_depth=int(norm_cfg_raw["min_depth"]),
            threads=int(norm_cfg_raw["threads"]),
            memory=str(norm_cfg_raw["memory"]),
            seed=(int(norm_cfg_raw["seed"]) if norm_cfg_raw.get("seed") is not None else None),
            extra_args=norm_cfg_raw.get("extra_args"),
        )

        logger.info("Running digital normalization")
        try:
            current_r1, current_r2 = normalize_pairs(
                current_r1,
                current_r2,
                norm_r1,
                norm_r2,
                norm_cfg,
            )
        except Exception as exc:
            logger.error("Normalization failed: %s", exc)
            sys.exit(1)

    asm_cfg_raw = cfg["assembly"]
    try:
        kmers = _parse_kmers(asm_cfg_raw.get("kmers"))
    except ValueError as exc:
        logger.error("Assembly configuration error: %s", exc)
        sys.exit(1)

    asm_cfg = AssemblyConfig(
        spades_exec=asm_cfg_raw["spades"],
        kmers=kmers,
        threads=int(asm_cfg_raw["threads"]),
        memory=int(asm_cfg_raw["memory"]),
        careful=bool(asm_cfg_raw.get("careful", True)),
        only_assembler=bool(asm_cfg_raw.get("only_assembler", False)),
        extra_args=asm_cfg_raw.get("extra_args"),
    )

    spades_dir = output_dir / "spades"
    logger.info("Running de novo assembly")
    try:
        asm_result = assemble_reads(
            current_r1,
            current_r2,
            input_singleton,
            spades_dir,
            asm_cfg,
        )
    except Exception as exc:
        logger.error("Assembly failed: %s", exc)
        sys.exit(1)

    current_fasta = asm_result.scaffolds if asm_result.scaffolds.exists() else asm_result.contigs
    logger.info(
        "Assembly complete: contigs=%d scaffolds=%d",
        asm_result.n_contigs,
        asm_result.n_scaffolds,
    )

    cov_cfg_raw = cfg["coverage_filter"]
    if cov_cfg_raw.get("enabled", True):
        cov_cfg = CoverageFilterConfig(
            samtools_exec=cov_cfg_raw["samtools"],
            minimap2_exec=cov_cfg_raw["minimap2"],
            mosdepth_exec=cov_cfg_raw["mosdepth"],
            threads=int(cov_cfg_raw["threads"]),
            min_mean_coverage=float(cov_cfg_raw["min_mean_coverage"]),
            minimap2_preset=str(cov_cfg_raw["minimap2_preset"]),
            mosdepth_window=int(cov_cfg_raw.get("mosdepth_window", 100)),
        )
        cov_dir = output_dir / "coverage_filter"
        cov_out = cov_dir / "contigs.coverage.filtered.fasta"

        logger.info("Running coverage-based filtering")
        try:
            cov_result = filter_by_coverage(
                current_fasta,
                current_r1,
                current_r2,
                input_singleton,
                cov_out,
                cov_dir,
                cov_cfg,
            )
        except Exception as exc:
            logger.error("Coverage filtering failed: %s", exc)
            sys.exit(1)

        current_fasta = cov_result.output_fasta
        logger.info(
            "Coverage filtering complete: passing=%d removed=%d",
            cov_result.n_passing,
            cov_result.n_removed,
        )

    dedup_cfg_raw = cfg["deduplication"]
    if dedup_cfg_raw.get("enabled", True):
        dedup_cfg = DedupConfig(
            blastn_exec=dedup_cfg_raw["blastn"],
            makeblastdb_exec=dedup_cfg_raw["makeblastdb"],
            evalue=float(dedup_cfg_raw["evalue"]),
            task=str(dedup_cfg_raw.get("task", "megablast")),
            word_size=int(dedup_cfg_raw.get("word_size", 28)),
            perc_identity=float(dedup_cfg_raw.get("perc_identity", 100.0)),
            qcov_hsp_perc=float(dedup_cfg_raw.get("qcov_hsp_perc", 100.0)),
            max_target_seqs=int(dedup_cfg_raw.get("max_target_seqs", 100)),
            threads=int(dedup_cfg_raw["threads"]),
            extra_args=dedup_cfg_raw.get("extra_args"),
        )

        dedup_dir = output_dir / "deduplication"
        dedup_out = dedup_dir / "contigs.deduplicated.fasta"
        workdir = dedup_dir / "work"

        logger.info("Running self-BLAST deduplication")
        try:
            dedup_result = deduplicate_contigs(
                current_fasta,
                dedup_out,
                dedup_cfg,
                workdir=workdir,
            )
        except Exception as exc:
            logger.error("Deduplication failed: %s", exc)
            sys.exit(1)

        current_fasta = dedup_result.output_fasta
        logger.info(
            "Deduplication complete: unique=%d removed=%d",
            dedup_result.n_unique,
            dedup_result.n_removed,
        )

    final_fasta = output_dir / "assembly.final.fasta"
    if current_fasta.resolve() != final_fasta.resolve():
        shutil.copyfile(current_fasta, final_fasta)

    if not cfg["validation"]["skip_output"]:
        out_result = validate_fasta(final_fasta, check_nonempty=False, min_records=0)
        if not out_result.valid:
            for err in out_result.errors:
                logger.error("Output validation: %s", err)
            sys.exit(1)

    logger.info("Assembly pipeline finished. Final FASTA: %s", final_fasta)


if __name__ == "__main__":
    main()
