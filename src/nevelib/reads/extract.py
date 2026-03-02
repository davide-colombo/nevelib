"""BAM-to-FASTQ extraction interfaces for the reads module.

This module defines the public API for extracting junction-enriched
read pairs and singletons from coordinate-sorted BAM input.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class InsertSizeFilterConfig:
    """Configuration for optional insert-size outlier filtering.

    Attributes:
        enabled: Enable robust insert-size filtering.
        mad_z: Z-score threshold on MAD-scaled insert sizes.
        min_pairs: Minimum number of clean pairs required to estimate a band.
        percentile: Fallback percentile threshold when robust estimation is unavailable.
    """

    enabled: bool = False
    mad_z: float = 4.0
    min_pairs: int = 200
    percentile: float = 5.0


@dataclass
class ReadExtractionConfig:
    """Configuration for BAM read extraction.

    Attributes:
        threads: Number of samtools worker threads.
        mapq_min: Minimum MAPQ for mapped-read based heuristics.
        split_min_softclip_bp: Minimum soft-clipped length to call split-read evidence.
        insert_size_filter: Settings for TLEN-based outlier filtering.
    """

    threads: int = 8
    mapq_min: int = 0
    split_min_softclip_bp: int = 15
    insert_size_filter: InsertSizeFilterConfig = field(default_factory=InsertSizeFilterConfig)


def extract_unmapped_reads(
    bam: Path,
    r1_out: Path,
    r2_out: Path,
    singleton_out: Path,
    cfg: ReadExtractionConfig,
) -> None:
    """Extract junction-enriched reads from a BAM into FASTQ outputs.

    Args:
        bam: Input coordinate-sorted, indexed BAM file.
        r1_out: Output FASTQ(.gz) path for extracted read1 mates.
        r2_out: Output FASTQ(.gz) path for extracted read2 mates.
        singleton_out: Output FASTQ(.gz) path for orphan/singleton reads.
        cfg: Extraction parameters and filtering behavior.

    Side Effects:
        Writes compressed FASTQ files and intermediate extraction artifacts.

    Raises:
        FileNotFoundError: If the BAM input is missing.
        RuntimeError: If extraction or external tool execution fails.
    """
    raise NotImplementedError
