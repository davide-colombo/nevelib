"""Canonical compression and decompression for all nevelib modules.

Every module that writes compressed files (FASTQ, etc.) delegates to the
functions in this module so that the compression format is consistent
across the entire library.  This prevents subtle incompatibilities between
tools that use different gzip variants (e.g. bgzf vs standard gzip).

Default compressor: pigz (falls back to gzip if pigz is not available).
"""

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CompressionConfig:
    """Configuration for compression behavior.

    Attributes:
        compressor: Name or path of the compressor binary (default: pigz).
        threads: Number of threads for parallel compression (default: 4).
        level: Compression level 1-9 (default: 6).
        fallback: Fallback compressor if primary is not found (default: gzip).
    """

    compressor: str = "pigz"
    threads: int = 4
    level: int = 6
    fallback: str = "gzip"


def compress(input_path: Path, output_path: Path, cfg: CompressionConfig | None = None) -> Path:
    """Compress a file using the configured compressor.

    Args:
        input_path: Path to the uncompressed input file.
        output_path: Path to write the compressed output.
        cfg: Compression configuration. Uses defaults if None.

    Returns:
        Path to the compressed output file.

    Raises:
        FileNotFoundError: If input_path does not exist.
        RuntimeError: If neither the primary nor fallback compressor is available.
    """
    raise NotImplementedError


def decompress(input_path: Path, output_path: Path, cfg: CompressionConfig | None = None) -> Path:
    """Decompress a gzip-compressed file using the configured compressor.

    Args:
        input_path: Path to the compressed input file.
        output_path: Path to write the decompressed output.
        cfg: Compression configuration. Uses defaults if None.

    Returns:
        Path to the decompressed output file.

    Raises:
        FileNotFoundError: If input_path does not exist.
        RuntimeError: If decompression fails.
    """
    raise NotImplementedError


def validate_gzip(path: Path) -> str:
    """Check gzip integrity and identify the compression variant.

    Args:
        path: Path to the gzip-compressed file.

    Returns:
        A string identifying the variant: 'gzip', 'bgzf', or 'unknown'.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If the file is not a valid gzip archive.
    """
    raise NotImplementedError


def recompress_if_bgzf(input_path: Path, output_path: Path, cfg: CompressionConfig | None = None) -> Path:
    """If the input is bgzf-compressed, recompress it as standard gzip.

    This is the canonical fix for the bgzf/gzip incompatibility between
    samtools (which writes bgzf) and tools like SPAdes (which expect gzip).
    If the input is already standard gzip, it is copied as-is.

    Args:
        input_path: Path to the potentially bgzf-compressed file.
        output_path: Path to write the canonical gzip output.
        cfg: Compression configuration. Uses defaults if None.

    Returns:
        Path to the output file (always standard gzip).
    """
    raise NotImplementedError
