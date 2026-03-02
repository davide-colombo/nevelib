"""CLI entry point for the nevelib reads module.

Usage:
    nevelib-reads config.yaml
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nevelib._common.bam import validate_bam
from nevelib._common.compression import CompressionConfig
from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fastq import run_fastq_qc, validate_fastq, validate_paired_fastq
from nevelib.reads.extract import ExtractionConfig, extract_reads_from_bam
from nevelib.reads.qc import FastQCConfig, TrimmingConfig, run_fastp, run_fastqc


_DEFAULTS: dict = {
    "input": {"bam": ""},
    "output": {"dir": "./reads_output"},
    "extraction": {
        "samtools": "samtools",
        "threads": 8,
        "extract_unmapped": True,
        "extract_supplementary": False,
        "include_secondary": False,
        "mapq_min": 0,
    },
    "trimming": {
        "enabled": True,
        "fastp": "fastp",
        "threads": 8,
        "qualified_quality_phred": 20,
        "min_length": 50,
        "detect_adapter_for_pe": True,
        "extra_args": None,
    },
    "qc": {
        "enabled": True,
        "tool": "fastqc",
        "fastqc": "fastqc",
        "threads": 4,
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


def main() -> None:
    """Entry point: load config YAML and run BAM-to-FASTQ workflow."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-reads <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.reads")

    user_cfg = load_config(config_path)
    cfg = merge_defaults(user_cfg, _DEFAULTS)
    validate_required_keys(cfg["input"], ["bam"], context="input")

    input_bam = Path(cfg["input"]["bam"])
    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    comp_raw = cfg["compression"]
    compression_cfg = CompressionConfig(
        compressor=comp_raw["compressor"],
        threads=int(comp_raw["threads"]),
        level=int(comp_raw["level"]),
        fallback=comp_raw["fallback"],
    )

    extraction_raw = cfg["extraction"]
    extraction_cfg = ExtractionConfig(
        samtools_exec=extraction_raw["samtools"],
        threads=int(extraction_raw["threads"]),
        extract_unmapped=bool(extraction_raw.get("extract_unmapped", True)),
        extract_supplementary=bool(extraction_raw.get("extract_supplementary", False)),
        include_secondary=bool(extraction_raw.get("include_secondary", False)),
        mapq_min=int(extraction_raw.get("mapq_min", 0)),
    )

    if not cfg["validation"]["skip_input"]:
        logger.info("Validating BAM input: %s", input_bam)
        bam_result = validate_bam(input_bam, require_sorted=True, require_index=True, run_quickcheck=True)
        if not bam_result.valid:
            for err in bam_result.errors:
                logger.error("BAM validation: %s", err)
            sys.exit(1)
        for warning in bam_result.warnings:
            logger.warning("BAM validation warning: %s", warning)

    logger.info("Extracting reads from BAM...")
    extraction = extract_reads_from_bam(
        bam=input_bam,
        output_dir=output_dir,
        cfg=extraction_cfg,
        compression_cfg=compression_cfg,
    )
    logger.info(
        "Extraction complete: paired=%d singleton=%d total=%d",
        extraction.paired_count,
        extraction.singleton_count,
        extraction.total_extracted,
    )

    active_r1 = extraction.r1
    active_r2 = extraction.r2
    singleton = extraction.singleton

    trimming_raw = cfg["trimming"]
    if bool(trimming_raw.get("enabled", True)):
        logger.info("Running fastp trimming...")
        trimming_cfg = TrimmingConfig(
            fastp_exec=trimming_raw["fastp"],
            threads=int(trimming_raw["threads"]),
            qualified_quality_phred=int(trimming_raw["qualified_quality_phred"]),
            min_length=int(trimming_raw["min_length"]),
            detect_adapter_for_pe=bool(trimming_raw.get("detect_adapter_for_pe", True)),
            extra_args=trimming_raw.get("extra_args"),
        )

        trimmed_dir = output_dir / "trimmed"
        trimmed_dir.mkdir(parents=True, exist_ok=True)

        trim_result = run_fastp(
            active_r1,
            active_r2,
            trimmed_dir / "trimmed_R1.fq.gz",
            trimmed_dir / "trimmed_R2.fq.gz",
            trimming_cfg,
            output_dir=trimmed_dir,
            out_log=trimmed_dir / "fastp.stdout.log",
            err_log=trimmed_dir / "fastp.stderr.log",
        )
        active_r1 = trim_result.r1
        active_r2 = trim_result.r2
        logger.info(
            "Trimming complete: reads_before=%d reads_after=%d",
            trim_result.reads_before,
            trim_result.reads_after,
        )

    qc_raw = cfg["qc"]
    if bool(qc_raw.get("enabled", True)):
        qc_tool = str(qc_raw.get("tool", "fastqc")).strip().lower()
        qc_threads = int(qc_raw.get("threads", 4))

        if qc_tool == "fastqc":
            logger.info("Running FastQC reports...")
            fastqc_cfg = FastQCConfig(
                fastqc_exec=qc_raw.get("fastqc", "fastqc"),
                threads=qc_threads,
            )
            qc_inputs = [active_r1, active_r2]
            if singleton is not None and singleton.exists():
                qc_inputs.append(singleton)
            reports = run_fastqc(
                qc_inputs,
                output_dir / "fastqc",
                fastqc_cfg,
                out_log=output_dir / "fastqc" / "fastqc.stdout.log",
                err_log=output_dir / "fastqc" / "fastqc.stderr.log",
            )
            logger.info("FastQC complete: %d report(s)", len(reports))
        elif qc_tool == "fastp":
            logger.info("Running fastp QC summary...")
            report = run_fastq_qc(
                active_r1,
                active_r2,
                output_dir=output_dir / "fastp_qc",
                tool="fastp",
                threads=qc_threads,
            )
            logger.info("fastp QC report: %s", report.report_path)
        else:
            logger.error("Unsupported qc.tool value: %s", qc_tool)
            sys.exit(1)

    if not cfg["validation"]["skip_output"]:
        logger.info("Validating output FASTQ files...")
        r1_res, r2_res = validate_paired_fastq(
            active_r1,
            active_r2,
            check_sync=False,
            check_nonempty=False,
            check_gzip=True,
        )
        if not r1_res.valid or not r2_res.valid:
            for err in r1_res.errors + r2_res.errors:
                logger.error("Output FASTQ validation: %s", err)
            sys.exit(1)

        if singleton is not None and singleton.exists():
            s_res = validate_fastq(singleton, check_nonempty=False, check_gzip=True)
            if not s_res.valid:
                for err in s_res.errors:
                    logger.error("Singleton FASTQ validation: %s", err)
                sys.exit(1)

    logger.info("Reads pipeline complete.")


if __name__ == "__main__":
    main()
