"""Digital normalization interfaces for assembly inputs.

This module exposes paired-end normalization entry points aligned with the
original Stage 01 normalization behavior.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class NormalizationConfig:
    """Configuration for read normalization.

    Attributes:
        normalizer_exec: Normalizer executable (for example `bbnorm.sh`).
        threads: Number of threads for normalization.
        java_xmx_gb: Java heap upper bound in GB for BBTools workflows.
        target_coverage: Desired target coverage for downsampling.
        pigz_exec: Compression/decompression executable.
        pigz_threads: Number of threads for pigz.
        extra_args: Additional normalizer CLI arguments.
        tmp_root: Optional temporary directory root.
    """

    normalizer_exec: str = "bbnorm.sh"
    threads: int = 16
    java_xmx_gb: int = 16
    target_coverage: int | None = 10
    pigz_exec: str = "pigz"
    pigz_threads: int = 4
    extra_args: list[str] = field(default_factory=list)
    tmp_root: Path | None = None


def normalize_pairs(
    r1: Path,
    r2: Path,
    out_r1: Path,
    out_r2: Path,
    cfg: NormalizationConfig,
) -> None:
    """Run digital normalization on a paired FASTQ dataset.

    Args:
        r1: Input R1 FASTQ(.gz).
        r2: Input R2 FASTQ(.gz).
        out_r1: Output normalized R1 FASTQ(.gz).
        out_r2: Output normalized R2 FASTQ(.gz).
        cfg: Normalization tool and runtime settings.

    Side Effects:
        Writes normalized paired FASTQ outputs.
    """
    raise NotImplementedError
