"""CLI entry point for the nevelib mapping module.

Usage:
    nevelib-mapping config.yaml
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import validate_fasta
from nevelib.mapping.minimap2 import Minimap2Config, run_minimap2
from nevelib.mapping.alignment_selection import (
    alignment_identity,
    best_hit_per_query,
    filter_paf_records,
    query_coverage,
)
from nevelib.mapping.paf import parse_paf, parse_paf_by_query


_DEFAULTS: dict = {
    "input": {
        "query": "",
        "reference": "",
    },
    "output": {
        "dir": "./mapping_output",
        "paf_filename": "alignments.paf",
        "summary_filename": "alignment_summary.tsv",
    },
    "minimap2": {
        "exec": "minimap2",
        "threads": 4,
        "preset": "asm5",
        "extra_args": None,
        "output_format": "paf",
    },
    "filtering": {
        "min_mapq": None,
        "min_aln_len": None,
        "min_nmatch": None,
        "min_identity": None,
    },
    "validation": {
        "skip_input": False,
        "skip_output": False,
        "strict": True,
    },
}


def main() -> None:
    """Entry point: load config YAML and run minimap2 alignment."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-mapping <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.mapping")

    user_cfg = load_config(config_path)
    cfg = merge_defaults(user_cfg, _DEFAULTS)

    validate_required_keys(cfg["input"], ["query", "reference"], context="input")

    query_fasta = Path(cfg["input"]["query"])
    reference_fasta = Path(cfg["input"]["reference"])

    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    paf_path = output_dir / cfg["output"]["paf_filename"]
    summary_path = output_dir / cfg["output"]["summary_filename"]

    mm2_raw = cfg["minimap2"]
    mm2_cfg = Minimap2Config(
        minimap2_exec=mm2_raw["exec"],
        threads=int(mm2_raw["threads"]),
        preset=mm2_raw.get("preset"),
        extra_args=mm2_raw.get("extra_args"),
        output_format=mm2_raw.get("output_format", "paf"),
    )

    if not cfg["validation"]["skip_input"]:
        logger.info("Validating query FASTA: %s", query_fasta)
        q_result = validate_fasta(query_fasta, check_nonempty=True, min_records=1)
        if not q_result.valid:
            for err in q_result.errors:
                logger.error("Query validation: %s", err)
            sys.exit(1)

        logger.info("Validating reference FASTA: %s", reference_fasta)
        r_result = validate_fasta(reference_fasta, check_nonempty=True, min_records=1)
        if not r_result.valid:
            for err in r_result.errors:
                logger.error("Reference validation: %s", err)
            sys.exit(1)

    logger.info("Running minimap2...")
    run_minimap2(query_fasta, reference_fasta, paf_path, mm2_cfg)
    logger.info("Alignment complete: %s", paf_path)

    records = parse_paf(paf_path)
    grouped = parse_paf_by_query(paf_path)
    logger.info("Parsed %d records across %d query sequences", len(records), len(grouped))

    fcfg = cfg["filtering"]
    filtered = filter_paf_records(
        records,
        min_mapq=fcfg.get("min_mapq"),
        min_aln_len=fcfg.get("min_aln_len"),
        min_nmatch=fcfg.get("min_nmatch"),
        min_identity=fcfg.get("min_identity"),
    )
    logger.info("Retained %d records after filtering", len(filtered))

    best = best_hit_per_query(filtered)

    with summary_path.open("w", encoding="utf-8") as handle:
        columns = [
            "qname",
            "qlen",
            "tname",
            "tlen",
            "nmatch",
            "aln_len",
            "mapq",
            "identity",
            "qcov",
        ]
        handle.write("\t".join(columns) + "\n")

        for qname in sorted(best):
            record = best[qname]
            handle.write(
                "\t".join(
                    [
                        record.qname,
                        str(record.qlen),
                        record.tname,
                        str(record.tlen),
                        str(record.nmatch),
                        str(record.aln_len),
                        str(record.mapq),
                        f"{alignment_identity(record):.4f}",
                        f"{query_coverage(record):.4f}",
                    ]
                )
                + "\n"
            )

    logger.info("Wrote best-hit summary to %s (%d query sequences)", summary_path, len(best))


if __name__ == "__main__":
    main()
