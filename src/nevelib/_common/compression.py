"""Canonical compression and decompression for all nevelib modules.

Every module that writes compressed files (FASTQ, etc.) delegates to the
functions in this module so that the compression format is consistent
across the entire library. This prevents subtle incompatibilities between
tools that use different gzip variants (for example bgzf vs standard gzip).

Default compressor: pigz (falls back to gzip if pigz is not available).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile

from nevelib._common.toolrun import check_tool, run_tool


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


def _resolve_compressor(cfg: CompressionConfig) -> str:
    """Resolve primary compressor and fallback executable names."""
    primary = check_tool(cfg.compressor)
    if primary.available:
        return str(primary.path or cfg.compressor)

    fallback = check_tool(cfg.fallback)
    if fallback.available:
        return str(fallback.path or cfg.fallback)

    raise RuntimeError(
        f"Neither primary compressor '{cfg.compressor}' nor fallback '{cfg.fallback}' is available."
    )


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
    config = cfg or CompressionConfig()

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    compressor = _resolve_compressor(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if Path(compressor).name.startswith("pigz"):
        cmd = (
            f"{compressor} -c -p {int(config.threads)} -{int(config.level)} "
            f"< '{input_path}' > '{output_path}'"
        )
    else:
        cmd = f"{compressor} -c -{int(config.level)} < '{input_path}' > '{output_path}'"

    run_tool(cmd, check=True)
    return output_path


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
    config = cfg or CompressionConfig()

    if not input_path.exists():
        raise FileNotFoundError(input_path)

    compressor = _resolve_compressor(config)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if Path(compressor).name.startswith("pigz"):
        cmd = f"{compressor} -d -c -p {int(config.threads)} < '{input_path}' > '{output_path}'"
    else:
        cmd = f"{compressor} -d -c < '{input_path}' > '{output_path}'"

    run_tool(cmd, check=True)
    return output_path


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
    if not path.exists():
        raise FileNotFoundError(path)

    with path.open("rb") as handle:
        header = handle.read(18)

    if len(header) < 10:
        raise ValueError(f"Not a valid gzip archive (header too short): {path}")

    if header[:2] != b"\x1f\x8b":
        raise ValueError(f"Not a gzip file: {path}")

    flg = header[3]
    has_extra = bool(flg & 0x04)

    if has_extra and len(header) >= 16:
        # BGZF stores the BC subfield in the gzip extra section.
        xlen = int.from_bytes(header[10:12], byteorder="little", signed=False)
        if xlen >= 6 and header[12:14] == b"BC":
            return "bgzf"

    return "gzip"


def recompress_if_bgzf(input_path: Path, output_path: Path, cfg: CompressionConfig | None = None) -> Path:
    """If the input is bgzf-compressed, recompress it as standard gzip.

    This is the canonical fix for bgzf/gzip incompatibilities when tools
    disagree on accepted compression details. If input is already standard
    gzip, it is copied unchanged.

    Args:
        input_path: Path to the potentially bgzf-compressed file.
        output_path: Path to write the canonical gzip output.
        cfg: Compression configuration. Uses defaults if None.

    Returns:
        Path to the output file (always standard gzip).
    """
    variant = validate_gzip(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if variant == "gzip":
        shutil.copyfile(input_path, output_path)
        return output_path

    if variant != "bgzf":
        raise ValueError(f"Unsupported gzip variant '{variant}' for {input_path}")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_plain = Path(tmp_dir) / "recompress.tmp"
        decompress(input_path, tmp_plain, cfg)
        compress(tmp_plain, output_path, cfg)

    return output_path
