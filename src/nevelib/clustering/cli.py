"""CLI entry point for the nevelib clustering module.

Usage:
    nevelib-clustering config.yaml
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import iter_fasta_records, validate_fasta
from nevelib.clustering.mmseqs import MmseqsConfig, run_mmseqs_linclust


_DEFAULTS: dict = {
    "input": {"fasta": ""},
    "output": {"dir": "./clustering_output", "prefix": "linclust"},
    "mmseqs": {
        "exec": "mmseqs",
        "min_seq_id": 0.9,
        "coverage": 0.8,
        "cov_mode": 0,
        "alignment_mode": 3,
        "threads": 4,
        "min_aln_len": 0,
        "split_memory_limit": None,
        "tmp_dir_name": "mmseqs_tmp",
    },
    "resume": False,
    "validation": {
        "skip_input": False,
        "skip_output": False,
        "strict": True,
    },
}


def main() -> None:
    """Entry point: load config YAML and run MMseqs2 clustering."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-clustering <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.clustering")

    user_cfg = load_config(config_path)
    cfg = merge_defaults(user_cfg, _DEFAULTS)
    validate_required_keys(cfg["input"], ["fasta"], context="input")

    input_fasta = Path(cfg["input"]["fasta"])
    output_dir = Path(cfg["output"]["dir"])
    prefix = cfg["output"]["prefix"]
    resume = bool(cfg.get("resume", False))

    output_dir.mkdir(parents=True, exist_ok=True)
    output_prefix = output_dir / prefix
    tmp_dir = output_dir / cfg["mmseqs"]["tmp_dir_name"]

    mcfg = cfg["mmseqs"]
    mmseqs_cfg = MmseqsConfig(
        mmseqs_exec=mcfg["exec"],
        min_seq_id=mcfg["min_seq_id"],
        coverage=mcfg["coverage"],
        cov_mode=mcfg["cov_mode"],
        alignment_mode=mcfg["alignment_mode"],
        threads=mcfg["threads"],
        min_aln_len=mcfg["min_aln_len"],
        split_memory_limit=mcfg.get("split_memory_limit"),
        tmp_dir_name=mcfg["tmp_dir_name"],
    )

    if not cfg["validation"]["skip_input"]:
        logger.info("Validating input FASTA: %s", input_fasta)
        result = validate_fasta(input_fasta, check_nonempty=True, min_records=1)
        if not result.valid:
            for err in result.errors:
                logger.error("Validation error: %s", err)
            sys.exit(1)
        for warn in result.warnings:
            logger.warning("Validation warning: %s", warn)

    all_ids = [record_id for record_id, _ in iter_fasta_records(input_fasta)]
    logger.info("Input contains %d sequences", len(all_ids))

    cluster_tsv: Path | None = None
    if resume:
        from nevelib.clustering.parse import validate_existing_clusters

        cluster_tsv_candidates = [
            output_prefix.parent / f"{output_prefix.name}_cluster.tsv",
            output_prefix.with_suffix(".tsv"),
        ]
        for candidate in cluster_tsv_candidates:
            if candidate.is_file():
                valid, reason = validate_existing_clusters(candidate, all_ids)
                if valid:
                    logger.info("Resuming: existing cluster TSV is valid: %s", candidate)
                    cluster_tsv = candidate
                    break
                logger.warning("Existing cluster TSV invalid (%s), re-running", reason)

    if cluster_tsv is None:
        logger.info("Running MMseqs2 linclust...")
        cluster_tsv = run_mmseqs_linclust(input_fasta, output_prefix, tmp_dir, mmseqs_cfg)
        logger.info("Clustering complete: %s", cluster_tsv)

    from nevelib.clustering.parse import (
        cluster_assignments_to_dataframe,
        parse_mmseqs_clusters,
    )

    assignments = parse_mmseqs_clusters(cluster_tsv, all_ids)
    df = cluster_assignments_to_dataframe(assignments)

    output_tsv = output_dir / "cluster_assignments.tsv"
    df.to_csv(output_tsv, sep="\t", index=False)
    logger.info(
        "Wrote %d assignments (%d clusters) to %s",
        len(df),
        df["cluster_id"].nunique() if not df.empty else 0,
        output_tsv,
    )


if __name__ == "__main__":
    main()
