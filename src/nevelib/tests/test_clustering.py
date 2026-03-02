"""Tests for nevelib.clustering module stubs."""

import pytest

from nevelib.clustering.mmseqs import run_mmseqs_linclust
from nevelib.clustering.parse import assign_cluster_ids, parse_mmseqs_clusters


def test_run_mmseqs_linclust_stub_exists() -> None:
    """clustering.mmseqs exposes run_mmseqs_linclust API."""
    assert callable(run_mmseqs_linclust)
    pytest.skip("Not yet implemented")


def test_parse_mmseqs_clusters_stub_exists() -> None:
    """clustering.parse exposes parse_mmseqs_clusters API."""
    assert callable(parse_mmseqs_clusters)
    pytest.skip("Not yet implemented")


def test_assign_cluster_ids_stub_exists() -> None:
    """clustering.parse exposes assign_cluster_ids API."""
    assert callable(assign_cluster_ids)
    pytest.skip("Not yet implemented")


def test_clustering_cli_requires_config_argument() -> None:
    """clustering CLI validates required config argument."""
    pytest.skip("Not yet implemented")
