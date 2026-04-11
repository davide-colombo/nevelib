"""Tests for merge_blast_hits_to_regions."""

from __future__ import annotations

import pandas as pd
import pytest

from nevelib.search.hits import merge_blast_hits_to_regions


BLAST_COLUMNS = [
    "qseqid",
    "qstart",
    "qend",
    "sseqid",
    "sstart",
    "send",
    "pident",
    "length",
    "evalue",
    "bitscore",
]


def _blast_df(rows: list[dict[str, object]], index: list[object] | None = None) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=BLAST_COLUMNS, index=index)


def test_empty_input_returns_empty_outputs() -> None:
    df = _blast_df([])

    regions, mapping = merge_blast_hits_to_regions(df)

    assert regions.empty
    assert list(regions.columns) == [
        "region_id",
        "qseqid",
        "region_start",
        "region_end",
        "region_length",
        "n_collapsed_hits",
        "sseqid",
        "sstart",
        "send",
        "pident",
        "length",
        "evalue",
        "bitscore",
    ]
    assert mapping.empty
    assert mapping.dtype == "int64"


def test_single_hit_becomes_single_region() -> None:
    df = _blast_df(
        [
            {
                "qseqid": "contig_1",
                "qstart": 10,
                "qend": 40,
                "sseqid": "virusA",
                "sstart": 100,
                "send": 130,
                "pident": 98.5,
                "length": 31,
                "evalue": 1e-20,
                "bitscore": 250.0,
            }
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df)

    assert regions.to_dict("records") == [
        {
            "region_id": 1,
            "qseqid": "contig_1",
            "region_start": 10,
            "region_end": 40,
            "region_length": 31,
            "n_collapsed_hits": 1,
            "sseqid": "virusA",
            "sstart": 100,
            "send": 130,
            "pident": 98.5,
            "length": 31,
            "evalue": 1e-20,
            "bitscore": 250.0,
        }
    ]
    assert mapping.to_dict() == {0: 1}


def test_overlapping_hits_collapse_into_one_region() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 100, "qend": 180, "sseqid": "s1", "sstart": 1, "send": 81, "pident": 97.0, "length": 81, "evalue": 1e-10, "bitscore": 120.0},
            {"qseqid": "q1", "qstart": 150, "qend": 220, "sseqid": "s2", "sstart": 5, "send": 75, "pident": 96.0, "length": 71, "evalue": 1e-12, "bitscore": 140.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df)

    assert len(regions) == 1
    assert regions.loc[0, "region_start"] == 100
    assert regions.loc[0, "region_end"] == 220
    assert regions.loc[0, "n_collapsed_hits"] == 2
    assert mapping.to_dict() == {0: 1, 1: 1}


def test_non_overlapping_hits_stay_separate_with_zero_gap() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 20, "sseqid": "s1", "sstart": 1, "send": 11, "pident": 99.0, "length": 11, "evalue": 1e-15, "bitscore": 100.0},
            {"qseqid": "q1", "qstart": 25, "qend": 35, "sseqid": "s2", "sstart": 20, "send": 30, "pident": 98.0, "length": 11, "evalue": 1e-14, "bitscore": 95.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df, max_gap_bp=0)

    assert regions["region_id"].tolist() == [1, 2]
    assert mapping.to_dict() == {0: 1, 1: 2}


def test_gap_equal_to_max_gap_collapses_hits() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 100, "qend": 150, "sseqid": "s1", "sstart": 1, "send": 51, "pident": 97.0, "length": 51, "evalue": 1e-20, "bitscore": 110.0},
            {"qseqid": "q1", "qstart": 201, "qend": 240, "sseqid": "s2", "sstart": 60, "send": 99, "pident": 96.0, "length": 40, "evalue": 1e-18, "bitscore": 105.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df, max_gap_bp=50)

    assert len(regions) == 1
    assert regions.loc[0, "region_start"] == 100
    assert regions.loc[0, "region_end"] == 240
    assert mapping.to_dict() == {0: 1, 1: 1}


def test_gap_one_less_than_boundary_does_not_collapse_hits() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 100, "qend": 150, "sseqid": "s1", "sstart": 1, "send": 51, "pident": 97.0, "length": 51, "evalue": 1e-20, "bitscore": 110.0},
            {"qseqid": "q1", "qstart": 201, "qend": 240, "sseqid": "s2", "sstart": 60, "send": 99, "pident": 96.0, "length": 40, "evalue": 1e-18, "bitscore": 105.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df, max_gap_bp=49)

    assert regions["region_id"].tolist() == [1, 2]
    assert mapping.to_dict() == {0: 1, 1: 2}


def test_multiple_groups_never_merge() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 60, "sseqid": "s1", "sstart": 1, "send": 51, "pident": 95.0, "length": 51, "evalue": 1e-8, "bitscore": 80.0},
            {"qseqid": "q2", "qstart": 20, "qend": 70, "sseqid": "s2", "sstart": 5, "send": 55, "pident": 96.0, "length": 51, "evalue": 1e-9, "bitscore": 85.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df, max_gap_bp=100)

    assert regions["qseqid"].tolist() == ["q1", "q2"]
    assert mapping.to_dict() == {0: 1, 1: 2}


def test_representative_hit_uses_highest_bitscore() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 40, "sseqid": "low", "sstart": 1, "send": 31, "pident": 90.0, "length": 31, "evalue": 1e-6, "bitscore": 50.0},
            {"qseqid": "q1", "qstart": 20, "qend": 60, "sseqid": "best", "sstart": 10, "send": 50, "pident": 99.0, "length": 41, "evalue": 1e-20, "bitscore": 200.0},
            {"qseqid": "q1", "qstart": 30, "qend": 70, "sseqid": "mid", "sstart": 15, "send": 55, "pident": 95.0, "length": 41, "evalue": 1e-10, "bitscore": 150.0},
        ]
    )

    regions, _mapping = merge_blast_hits_to_regions(df)

    assert regions.loc[0, "sseqid"] == "best"
    assert regions.loc[0, "bitscore"] == 200.0


def test_representative_tiebreak_uses_lower_evalue() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "worse_eval", "sstart": 1, "send": 41, "pident": 97.0, "length": 41, "evalue": 1e-15, "bitscore": 180.0},
            {"qseqid": "q1", "qstart": 20, "qend": 60, "sseqid": "better_eval", "sstart": 10, "send": 50, "pident": 97.0, "length": 41, "evalue": 1e-20, "bitscore": 180.0},
        ]
    )

    regions, _mapping = merge_blast_hits_to_regions(df)

    assert regions.loc[0, "sseqid"] == "better_eval"


def test_stable_tiebreak_uses_lowest_input_index() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 50, "sseqid": "first", "sstart": 1, "send": 41, "pident": 97.0, "length": 41, "evalue": 1e-20, "bitscore": 180.0},
            {"qseqid": "q1", "qstart": 20, "qend": 60, "sseqid": "second", "sstart": 10, "send": 50, "pident": 97.0, "length": 41, "evalue": 1e-20, "bitscore": 180.0},
        ],
        index=[10, 20],
    )

    regions, _mapping = merge_blast_hits_to_regions(df)

    assert regions.loc[0, "sseqid"] == "first"


def test_payload_cols_restrict_payload_output() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 40, "sseqid": "s1", "sstart": 1, "send": 31, "pident": 94.0, "length": 31, "evalue": 1e-7, "bitscore": 88.0},
        ]
    )

    regions, _mapping = merge_blast_hits_to_regions(df, payload_cols=["sseqid", "pident"])

    assert list(regions.columns) == [
        "region_id",
        "qseqid",
        "region_start",
        "region_end",
        "region_length",
        "n_collapsed_hits",
        "sseqid",
        "pident",
    ]


def test_default_payload_cols_carry_all_non_coordinate_columns() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 40, "sseqid": "s1", "sstart": 1, "send": 31, "pident": 94.0, "length": 31, "evalue": 1e-7, "bitscore": 88.0},
        ]
    )

    regions, _mapping = merge_blast_hits_to_regions(df)

    assert list(regions.columns) == [
        "region_id",
        "qseqid",
        "region_start",
        "region_end",
        "region_length",
        "n_collapsed_hits",
        "sseqid",
        "sstart",
        "send",
        "pident",
        "length",
        "evalue",
        "bitscore",
    ]


def test_invalid_interval_raises_value_error_with_index() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 30, "qend": 10, "sseqid": "s1", "sstart": 1, "send": 21, "pident": 94.0, "length": 21, "evalue": 1e-7, "bitscore": 88.0},
        ],
        index=[42],
    )

    with pytest.raises(ValueError, match="42"):
        merge_blast_hits_to_regions(df)


def test_negative_max_gap_raises_value_error() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 40, "sseqid": "s1", "sstart": 1, "send": 31, "pident": 94.0, "length": 31, "evalue": 1e-7, "bitscore": 88.0},
        ]
    )

    with pytest.raises(ValueError, match="max_gap_bp"):
        merge_blast_hits_to_regions(df, max_gap_bp=-1)


def test_missing_group_column_raises_key_error() -> None:
    df = pd.DataFrame(
        [
            {"qstart": 10, "qend": 40, "sseqid": "s1", "sstart": 1, "send": 31, "pident": 94.0, "length": 31, "evalue": 1e-7, "bitscore": 88.0},
        ]
    )

    with pytest.raises(KeyError, match="qseqid"):
        merge_blast_hits_to_regions(df)


def test_hit_to_region_id_mapping_matches_merged_regions() -> None:
    df = _blast_df(
        [
            {"qseqid": "q1", "qstart": 10, "qend": 30, "sseqid": "a", "sstart": 1, "send": 21, "pident": 91.0, "length": 21, "evalue": 1e-5, "bitscore": 70.0},
            {"qseqid": "q1", "qstart": 25, "qend": 50, "sseqid": "b", "sstart": 10, "send": 35, "pident": 92.0, "length": 26, "evalue": 1e-6, "bitscore": 80.0},
            {"qseqid": "q1", "qstart": 100, "qend": 130, "sseqid": "c", "sstart": 40, "send": 70, "pident": 93.0, "length": 31, "evalue": 1e-7, "bitscore": 90.0},
            {"qseqid": "q2", "qstart": 5, "qend": 15, "sseqid": "d", "sstart": 1, "send": 11, "pident": 94.0, "length": 11, "evalue": 1e-8, "bitscore": 95.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df)

    assert len(mapping) == len(df)
    for region in regions.itertuples(index=False):
        member_hits = df.loc[mapping == region.region_id]
        assert not member_hits.empty
        assert region.region_start == member_hits["qstart"].min()
        assert region.region_end == member_hits["qend"].max()
        assert region.n_collapsed_hits == len(member_hits)


def test_shuffled_input_produces_identical_regions() -> None:
    df = _blast_df(
        [
            {"qseqid": "q2", "qstart": 90, "qend": 120, "sseqid": "s4", "sstart": 1, "send": 31, "pident": 94.0, "length": 31, "evalue": 1e-8, "bitscore": 100.0},
            {"qseqid": "q1", "qstart": 10, "qend": 30, "sseqid": "s1", "sstart": 5, "send": 25, "pident": 99.0, "length": 21, "evalue": 1e-20, "bitscore": 200.0},
            {"qseqid": "q1", "qstart": 25, "qend": 40, "sseqid": "s2", "sstart": 15, "send": 30, "pident": 95.0, "length": 16, "evalue": 1e-10, "bitscore": 150.0},
            {"qseqid": "q2", "qstart": 200, "qend": 240, "sseqid": "s5", "sstart": 50, "send": 90, "pident": 93.0, "length": 41, "evalue": 1e-6, "bitscore": 90.0},
        ],
        index=[40, 10, 20, 30],
    )

    shuffled = df.sample(frac=1, random_state=7)

    regions_a, _mapping_a = merge_blast_hits_to_regions(df)
    regions_b, _mapping_b = merge_blast_hits_to_regions(shuffled)

    pd.testing.assert_frame_equal(regions_a, regions_b)


def test_realistic_viral_fixture_produces_two_regions() -> None:
    df = _blast_df(
        [
            {"qseqid": "scaffold_virus_01", "qstart": 1012, "qend": 1188, "sseqid": "NC_001802.1", "sstart": 440, "send": 616, "pident": 91.3, "length": 177, "evalue": 2e-25, "bitscore": 210.0},
            {"qseqid": "scaffold_virus_01", "qstart": 1160, "qend": 1325, "sseqid": "NC_001802.1", "sstart": 700, "send": 865, "pident": 94.8, "length": 166, "evalue": 1e-40, "bitscore": 260.0},
            {"qseqid": "scaffold_virus_01", "qstart": 2100, "qend": 2255, "sseqid": "NC_039477.1", "sstart": 50, "send": 205, "pident": 88.2, "length": 156, "evalue": 6e-18, "bitscore": 175.0},
        ]
    )

    regions, mapping = merge_blast_hits_to_regions(df)

    assert len(regions) == 2
    assert regions["region_start"].tolist() == [1012, 2100]
    assert regions["region_end"].tolist() == [1325, 2255]
    assert regions.loc[0, "sseqid"] == "NC_001802.1"
    assert regions.loc[0, "bitscore"] == 260.0
    assert mapping.to_dict() == {0: 1, 1: 1, 2: 2}


def test_realistic_host_fixture_gap_merge_respects_threshold() -> None:
    df = _blast_df(
        [
            {"qseqid": "host_scaffold_42", "qstart": 5000, "qend": 5180, "sseqid": "chr1_host", "sstart": 90000, "send": 90180, "pident": 96.5, "length": 181, "evalue": 1e-35, "bitscore": 240.0},
            {"qseqid": "host_scaffold_42", "qstart": 5331, "qend": 5480, "sseqid": "chr1_host", "sstart": 90331, "send": 90480, "pident": 95.9, "length": 150, "evalue": 1e-30, "bitscore": 230.0},
        ]
    )

    merged_regions, merged_mapping = merge_blast_hits_to_regions(df, max_gap_bp=200)
    split_regions, split_mapping = merge_blast_hits_to_regions(df, max_gap_bp=100)

    assert len(merged_regions) == 1
    assert merged_regions.loc[0, "region_start"] == 5000
    assert merged_regions.loc[0, "region_end"] == 5480
    assert merged_mapping.to_dict() == {0: 1, 1: 1}

    assert len(split_regions) == 2
    assert split_mapping.to_dict() == {0: 1, 1: 2}
