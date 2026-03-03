"""CLI entry point for the nevelib msa module.

Usage:
    nevelib-msa config.yaml
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import iter_fasta_records, validate_fasta
from nevelib.msa.mafft import MafftConfig, run_mafft, run_mafft_seed_and_add
from nevelib.msa.metrics import MetricsConfig, compute_alignment_metrics, parse_fasta_alignment


_DEFAULTS: dict = {
    "input": {
        "fasta": "",
        "add_fasta": None,
    },
    "output": {
        "dir": "./msa_output",
        "alignment_filename": "alignment.fasta",
        "metrics_filename": "alignment_metrics.tsv",
    },
    "mafft": {
        "exec": "mafft",
        "threads": 4,
        "auto": True,
        "extra_args": None,
    },
    "metrics": {
        "enabled": True,
        "occupancy_threshold": 0.60,
        "min_seq_length": 80,
    },
    "validation": {
        "skip_input": False,
        "skip_output": False,
        "strict": True,
    },
}


def main() -> None:
    """Entry point: load config YAML and run MAFFT alignment and metrics."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-msa <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.msa")

    user_cfg = load_config(config_path)
    cfg = merge_defaults(user_cfg, _DEFAULTS)
    validate_required_keys(cfg["input"], ["fasta"], context="input")

    input_fasta = Path(cfg["input"]["fasta"])
    add_fasta_raw = cfg["input"].get("add_fasta")
    add_fasta = Path(add_fasta_raw) if add_fasta_raw else None

    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    alignment_path = output_dir / cfg["output"]["alignment_filename"]
    metrics_path = output_dir / cfg["output"]["metrics_filename"]

    mafft_raw = cfg["mafft"]
    mafft_cfg = MafftConfig(
        mafft_exec=mafft_raw["exec"],
        threads=int(mafft_raw["threads"]),
        auto=bool(mafft_raw.get("auto", True)),
        extra_args=mafft_raw.get("extra_args"),
    )

    if not cfg["validation"]["skip_input"]:
        logger.info("Validating input FASTA: %s", input_fasta)
        result = validate_fasta(input_fasta, check_nonempty=True, min_records=1)
        if not result.valid:
            for err in result.errors:
                logger.error("Validation error: %s", err)
            sys.exit(1)

        if add_fasta is not None:
            logger.info("Validating add FASTA: %s", add_fasta)
            add_result = validate_fasta(add_fasta, check_nonempty=True, min_records=1)
            if not add_result.valid:
                for err in add_result.errors:
                    logger.error("Validation error: %s", err)
                sys.exit(1)

    if add_fasta is not None:
        logger.info("Running MAFFT seed-and-add...")
        run_mafft_seed_and_add(input_fasta, add_fasta, alignment_path, mafft_cfg)
    else:
        logger.info("Running MAFFT...")
        run_mafft(input_fasta, alignment_path, mafft_cfg)

    logger.info("Alignment written to %s", alignment_path)

    metrics_cfg = cfg["metrics"]
    if bool(metrics_cfg.get("enabled", True)):
        logger.info("Computing alignment metrics...")

        aligned = parse_fasta_alignment(alignment_path)

        original_lengths: dict[str, int] = {}
        for rec_id, seq in iter_fasta_records(input_fasta):
            original_lengths[rec_id] = len(seq)
        if add_fasta is not None:
            for rec_id, seq in iter_fasta_records(add_fasta):
                original_lengths[rec_id] = len(seq)

        met_cfg = MetricsConfig(
            occupancy_threshold=float(metrics_cfg["occupancy_threshold"]),
            min_seq_length=int(metrics_cfg.get("min_seq_length", 0)),
        )

        metrics = compute_alignment_metrics(
            aligned,
            met_cfg,
            core_lengths=original_lengths,
        )

        with metrics_path.open("w", encoding="utf-8") as handle:
            handle.write("metric\tvalue\n")
            handle.write(f"n_total\t{metrics.n_total}\n")
            handle.write(f"n_aligned\t{metrics.n_aligned}\n")
            handle.write(f"shared_span_bp\t{metrics.shared_span_bp}\n")
            handle.write(f"shared_span_frac\t{metrics.shared_span_frac:.6f}\n")
            median_id = (
                f"{metrics.median_identity:.6f}"
                if metrics.median_identity is not None
                else "NA"
            )
            handle.write(f"median_identity\t{median_id}\n")
            p10_id = f"{metrics.p10_identity:.6f}" if metrics.p10_identity is not None else "NA"
            handle.write(f"p10_identity\t{p10_id}\n")
            median_len = (
                f"{metrics.median_sequence_length:.6f}"
                if metrics.median_sequence_length is not None
                else "NA"
            )
            handle.write(f"median_sequence_length\t{median_len}\n")
            frac_len = (
                f"{metrics.frac_length_ge_min:.6f}"
                if metrics.frac_length_ge_min is not None
                else "NA"
            )
            handle.write(f"frac_length_ge_min\t{frac_len}\n")

        logger.info("Metrics written to %s", metrics_path)


if __name__ == "__main__":
    main()
