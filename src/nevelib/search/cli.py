"""CLI entry point for the nevelib search module.

Usage:
    nevelib-search config.yaml
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from nevelib._common.blast_db import validate_blast_db
from nevelib._common.config import load_config, merge_defaults, validate_required_keys
from nevelib._common.fasta import validate_fasta
from nevelib.search.blast import BlastConfig, run_blastn, run_blastx
from nevelib.search.classify import classify_hits_by_taxonomy
from nevelib.search.hit_calculations import filter_hits, filter_hits_by_bitscore_fraction
from nevelib.search.hits import parse_blast_to_dataframe


_DEFAULTS: dict = {
    "input": {"fasta": ""},
    "output": {"dir": "./search_output"},
    "blast": {
        "program": "blastn",
        "db_prefix": "",
        "evalue": 1e-5,
        "max_target_seqs": 10,
        "perc_identity": None,
        "threads": 4,
        "outfmt_fields": None,
        "extra_args": None,
        "db_type": "nucl",
        "require_taxonomy": False,
    },
    "filtering": {
        "min_pident": None,
        "min_length": None,
        "max_evalue": None,
        "min_bitscore": None,
    },
    "classification": {
        "enabled": False,
        "taxonomy_col": "staxids",
        "rule": "majority",
        "keywords": [],
        "keyword_fallback": False,
        "bitscore_top_fraction": 0.9,
    },
    "validation": {
        "skip_input": False,
        "skip_output": False,
        "strict": True,
    },
}


def main() -> None:
    """Entry point: load config YAML and run BLAST search + filtering."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-search <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )
    logger = logging.getLogger("nevelib.search")

    user_cfg = load_config(config_path)
    cfg = merge_defaults(user_cfg, _DEFAULTS)

    validate_required_keys(cfg["input"], ["fasta"], context="input")
    validate_required_keys(cfg["blast"], ["db_prefix"], context="blast")

    input_fasta = Path(cfg["input"]["fasta"])
    output_dir = Path(cfg["output"]["dir"])
    output_dir.mkdir(parents=True, exist_ok=True)

    blast_cfg = dict(cfg["blast"])
    program = str(blast_cfg.get("program", "blastn")).strip().lower()
    if program not in {"blastn", "blastx"}:
        logger.error("Unsupported BLAST program: %s", program)
        sys.exit(1)

    bcfg = BlastConfig(
        blast_exec=program,
        db_prefix=str(blast_cfg["db_prefix"]),
        evalue=float(blast_cfg["evalue"]),
        max_target_seqs=int(blast_cfg["max_target_seqs"]),
        perc_identity=(None if blast_cfg.get("perc_identity") is None else float(blast_cfg["perc_identity"])),
        threads=int(blast_cfg["threads"]),
        outfmt=6,
        outfmt_fields=blast_cfg.get("outfmt_fields"),
        extra_args=blast_cfg.get("extra_args"),
        db_type=str(blast_cfg.get("db_type", "nucl")),
        require_taxonomy=bool(blast_cfg.get("require_taxonomy", False)),
    )

    if not cfg["validation"]["skip_input"]:
        logger.info("Validating input FASTA: %s", input_fasta)
        fasta_result = validate_fasta(input_fasta, check_nonempty=True)
        if not fasta_result.valid:
            for err in fasta_result.errors:
                logger.error("FASTA validation: %s", err)
            sys.exit(1)

        logger.info("Validating BLAST database: %s", bcfg.db_prefix)
        db_result = validate_blast_db(
            Path(bcfg.db_prefix),
            db_type=bcfg.db_type,
            require_taxonomy=bcfg.require_taxonomy,
        )
        if not db_result.valid:
            for err in db_result.errors:
                logger.error("DB validation: %s", err)
            sys.exit(1)

    raw_output = output_dir / "blast_raw.tsv"
    out_log = output_dir / "blast.out.log"
    err_log = output_dir / "blast.err.log"

    runner = run_blastx if program == "blastx" else run_blastn
    logger.info("Running %s...", program)
    runner(input_fasta, raw_output, bcfg, out_log=out_log, err_log=err_log)
    logger.info("BLAST complete: %s", raw_output)

    df = parse_blast_to_dataframe(raw_output, fields=bcfg.outfmt_fields)
    logger.info("Parsed %d raw hits", len(df))

    fcfg = cfg["filtering"]
    df_filtered = filter_hits(
        df,
        min_pident=fcfg.get("min_pident"),
        min_length=fcfg.get("min_length"),
        max_evalue=fcfg.get("max_evalue"),
        min_bitscore=fcfg.get("min_bitscore"),
    )

    filtered_output = output_dir / "blast_filtered.tsv"
    df_filtered.to_csv(filtered_output, sep="\t", index=False)
    logger.info("Wrote %d filtered hits to %s", len(df_filtered), filtered_output)

    c_cfg = cfg.get("classification", {}) or {}
    if bool(c_cfg.get("enabled", False)) and not df_filtered.empty:
        logger.info("Running taxonomy classification...")
        frac = float(c_cfg.get("bitscore_top_fraction", 0.9))
        to_classify = filter_hits_by_bitscore_fraction(df_filtered, top_fraction=frac)
        classified = classify_hits_by_taxonomy(
            to_classify,
            taxonomy_col=str(c_cfg.get("taxonomy_col", "staxids")),
            rule=str(c_cfg.get("rule", "majority")),
            keywords=list(c_cfg.get("keywords", [])),
            keyword_fallback=bool(c_cfg.get("keyword_fallback", False)),
        )

        out_cls = output_dir / "classification.tsv"
        rows = [
            {
                "qseqid": item.query_id,
                "classification": item.classification,
                "reason": item.reason,
                "top_hit_taxon": item.top_hit_taxon,
                "keyword_match": item.keyword_match,
            }
            for item in classified
        ]
        import pandas as pd

        pd.DataFrame(rows).to_csv(out_cls, sep="\t", index=False)
        logger.info("Wrote %d classifications to %s", len(rows), out_cls)


if __name__ == "__main__":
    main()
