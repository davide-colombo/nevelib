"""Tests for nevelib.assembly module stubs."""

import pytest

from nevelib.assembly.assemble import assemble_reads
from nevelib.assembly.coverage import filter_scaffolds_by_coverage
from nevelib.assembly.dedup import deduplicate_scaffolds
from nevelib.assembly.normalize import normalize_pairs


def test_normalize_pairs_stub_exists() -> None:
    """assembly.normalize exposes normalize_pairs API."""
    assert callable(normalize_pairs)
    pytest.skip("Not yet implemented")


def test_assemble_reads_stub_exists() -> None:
    """assembly.assemble exposes assemble_reads API."""
    assert callable(assemble_reads)
    pytest.skip("Not yet implemented")


def test_filter_scaffolds_by_coverage_stub_exists() -> None:
    """assembly.coverage exposes filter_scaffolds_by_coverage API."""
    assert callable(filter_scaffolds_by_coverage)
    pytest.skip("Not yet implemented")


def test_deduplicate_scaffolds_stub_exists() -> None:
    """assembly.dedup exposes deduplicate_scaffolds API."""
    assert callable(deduplicate_scaffolds)
    pytest.skip("Not yet implemented")


def test_assembly_cli_requires_config_argument() -> None:
    """assembly CLI validates required config argument."""
    pytest.skip("Not yet implemented")
