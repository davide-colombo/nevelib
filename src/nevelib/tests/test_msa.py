"""Tests for nevelib.msa module stubs."""

import pytest

from nevelib.msa.mafft import run_mafft, run_mafft_seed_and_add
from nevelib.msa.metrics import compute_alignment_metrics, parse_fasta_alignment


def test_run_mafft_stub_exists() -> None:
    """msa.mafft exposes run_mafft API."""
    assert callable(run_mafft)
    pytest.skip("Not yet implemented")


def test_run_mafft_seed_and_add_stub_exists() -> None:
    """msa.mafft exposes run_mafft_seed_and_add API."""
    assert callable(run_mafft_seed_and_add)
    pytest.skip("Not yet implemented")


def test_parse_and_compute_metrics_stubs_exist() -> None:
    """msa.metrics exposes parse/compute metric APIs."""
    assert callable(parse_fasta_alignment)
    assert callable(compute_alignment_metrics)
    pytest.skip("Not yet implemented")


def test_msa_cli_requires_config_argument() -> None:
    """msa CLI validates required config argument."""
    pytest.skip("Not yet implemented")
