"""Tests for nevelib.mapping module stubs."""

import pytest

from nevelib.mapping.minimap2 import run_minimap2
from nevelib.mapping.paf import best_hit_per_query, filter_paf_hits, parse_paf


def test_run_minimap2_stub_exists() -> None:
    """mapping.minimap2 exposes run_minimap2 API."""
    assert callable(run_minimap2)
    pytest.skip("Not yet implemented")


def test_parse_paf_stub_exists() -> None:
    """mapping.paf exposes parse_paf API."""
    assert callable(parse_paf)
    pytest.skip("Not yet implemented")


def test_filter_and_best_hit_stubs_exist() -> None:
    """mapping.paf exposes filtering and best-hit APIs."""
    assert callable(filter_paf_hits)
    assert callable(best_hit_per_query)
    pytest.skip("Not yet implemented")


def test_mapping_cli_requires_config_argument() -> None:
    """mapping CLI validates required config argument."""
    pytest.skip("Not yet implemented")
