"""Tests for nevelib._common utility stubs."""

import pytest

from nevelib._common.bam import validate_bam
from nevelib._common.compression import compress, decompress
from nevelib._common.config import load_config
from nevelib._common.fasta import validate_fasta
from nevelib._common.fastq import validate_fastq
from nevelib._common.sentinel import run_step
from nevelib._common.toolrun import check_tool


def test_validate_fastq_rejects_missing_file() -> None:
    """validate_fastq raises FileNotFoundError for non-existent path."""
    assert callable(validate_fastq)
    pytest.skip("Not yet implemented")


def test_validate_fasta_rejects_empty_file() -> None:
    """validate_fasta fails on an empty FASTA file."""
    assert callable(validate_fasta)
    pytest.skip("Not yet implemented")


def test_compression_roundtrip() -> None:
    """compress then decompress produces identical content."""
    assert callable(compress)
    assert callable(decompress)
    pytest.skip("Not yet implemented")


def test_validate_bam_detects_missing_index() -> None:
    """validate_bam reports missing .bai index."""
    assert callable(validate_bam)
    pytest.skip("Not yet implemented")


def test_check_tool_returns_unavailable_for_nonexistent_binary() -> None:
    """check_tool returns available=False for a fake binary."""
    assert callable(check_tool)
    pytest.skip("Not yet implemented")


def test_sentinel_and_config_stubs_exist() -> None:
    """run_step and load_config APIs are present for common infrastructure."""
    assert callable(run_step)
    assert callable(load_config)
    pytest.skip("Not yet implemented")
