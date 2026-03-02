"""Coverage-based scaffold filtering interfaces.

This module provides the API for read remapping and coverage-aware scaffold
selection after assembly.
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CoverageFilterConfig:
    """Configuration for coverage-based scaffold filtering.

    Attributes:
        threads: Threads used by minimap2/mosdepth.
        preset: Minimap2 preset for read mapping.
        min_mean_coverage: Minimum mean depth threshold.
        window_size: Window size (bp) for shape checks.
        min_windows_for_shape: Minimum windows required to apply shape logic.
        min_window_coverage: Per-window support threshold.
        min_fraction_high_cov: Fraction of supported windows required.
        short_min_mean_coverage: Mean-depth threshold for short contigs.
        minimap2_exec: Minimap2 executable.
        mosdepth_exec: Mosdepth executable.
        extra_minimap2_args: Additional minimap2 CLI args.
        extra_mosdepth_args: Additional mosdepth CLI args.
        tmp_root: Optional temporary directory root.
        qc_enabled: Whether scaffold QC hooks are enabled.
    """

    threads: int = 8
    preset: str = "sr"
    min_mean_coverage: float = 2.0
    window_size: int = 100
    min_windows_for_shape: int | None = None
    min_window_coverage: float | None = None
    min_fraction_high_cov: float | None = None
    short_min_mean_coverage: float | None = None
    minimap2_exec: str = "minimap2"
    mosdepth_exec: str = "mosdepth"
    extra_minimap2_args: list[str] = field(default_factory=list)
    extra_mosdepth_args: list[str] = field(default_factory=list)
    tmp_root: Path | None = None
    qc_enabled: bool = True


def filter_scaffolds_by_coverage(
    scaffolds: Path,
    r1: Path,
    r2: Path,
    singleton: Path | None,
    out_fasta: Path,
    workdir: Path,
    cfg: CoverageFilterConfig,
) -> None:
    """Filter assembled scaffolds using read-mapping coverage metrics.

    Args:
        scaffolds: Input scaffold FASTA.
        r1: Input R1 FASTQ(.gz) for remapping.
        r2: Input R2 FASTQ(.gz) for remapping.
        singleton: Optional singleton FASTQ(.gz) for remapping.
        out_fasta: Output FASTA containing retained scaffolds.
        workdir: Working directory for intermediate files.
        cfg: Coverage filter and tool execution settings.

    Side Effects:
        Writes filtered FASTA and coverage summary artifacts under `workdir`.
    """
    raise NotImplementedError
