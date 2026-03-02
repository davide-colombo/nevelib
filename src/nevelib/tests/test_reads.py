"""Tests for nevelib.reads module stubs."""

import pytest

from nevelib.reads.extract import extract_unmapped_reads
from nevelib.reads.qc import run_fastp, run_fastqc


def test_extract_unmapped_reads_stub_exists() -> None:
    """reads.extract exposes extract_unmapped_reads API."""
    assert callable(extract_unmapped_reads)
    pytest.skip("Not yet implemented")


def test_run_fastp_stub_exists() -> None:
    """reads.qc exposes run_fastp API."""
    assert callable(run_fastp)
    pytest.skip("Not yet implemented")


def test_run_fastqc_stub_exists() -> None:
    """reads.qc exposes run_fastqc API."""
    assert callable(run_fastqc)
    pytest.skip("Not yet implemented")


def test_reads_cli_help_exit_code() -> None:
    """reads CLI accepts help flag and exits cleanly."""
    pytest.skip("Not yet implemented")
