"""Tests for nevelib.search module stubs."""

import pytest

from nevelib.search.blast import run_blastn, run_blastx
from nevelib.search.classify import classify_hits_by_taxonomy
from nevelib.search.hits import filter_hits, parse_blast_tabular, prune_contained_intervals


def test_run_blastn_stub_exists() -> None:
    """search.blast exposes run_blastn API."""
    assert callable(run_blastn)
    pytest.skip("Not yet implemented")


def test_run_blastx_stub_exists() -> None:
    """search.blast exposes run_blastx API."""
    assert callable(run_blastx)
    pytest.skip("Not yet implemented")


def test_parse_and_filter_hits_stubs_exist() -> None:
    """search.hits exposes parse/filter/prune APIs."""
    assert callable(parse_blast_tabular)
    assert callable(filter_hits)
    assert callable(prune_contained_intervals)
    pytest.skip("Not yet implemented")


def test_classify_hits_by_taxonomy_stub_exists() -> None:
    """search.classify exposes taxonomy classification API."""
    assert callable(classify_hits_by_taxonomy)
    pytest.skip("Not yet implemented")


def test_search_cli_requires_config_argument() -> None:
    """search CLI validates required config argument."""
    pytest.skip("Not yet implemented")
