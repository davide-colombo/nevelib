"""The BLAST calculation contract is usable independently of external adapters."""

import pickle
import subprocess
import sys
import textwrap


def test_hit_calculations_work_without_loading_adapters():
    code = textwrap.dedent("""
        import importlib.abc
        import sys

        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in {'nevelib.search.hits', 'nevelib.search.blast'} or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)

        sys.meta_path.insert(0, BlockAdapters())
        from nevelib.search.hit_calculations import (
            BlastHit, filter_hits, merge_blast_hits_to_regions,
            normalize_blast_strand, select_best_hit_per_query,
        )
        import pandas as pd

        hit = BlastHit('q', 's', 90, 10, 1, 0, 1, 10, 20, 11, 1e-5, 50)
        normalized = normalize_blast_strand([hit])
        assert (normalized[0].sstart, normalized[0].send, normalized[0].strand) == (11, 20, '-')
        assert (hit.sstart, hit.send, hit.strand) == (20, 11, '+')
        assert filter_hits(normalized, min_length=10) == normalized
        assert select_best_hit_per_query(normalized) == normalized
        assert filter_hits([], min_length=10) == []

        frame = pd.DataFrame({'qseqid': ['q', 'q'], 'qstart': [1, 6],
                              'qend': [5, 9], 'bitscore': [20, 20],
                              'evalue': [0.1, 0.1], 'tag': ['a', 'b']}, index=[7, 3])
        before = frame.copy(deep=True)
        regions, mapping = merge_blast_hits_to_regions(frame, payload_cols=['tag'])
        assert regions[['region_start', 'region_end', 'region_length', 'n_collapsed_hits', 'tag']].values.tolist() == [[1, 9, 9, 2, 'b']]
        assert mapping.tolist() == [1.0, 1.0]
        pd.testing.assert_frame_equal(frame, before)
        try:
            filter_hits(frame, min_qcov=0.5)
        except ValueError as exc:
            assert str(exc) == 'min_qcov requires one of DataFrame columns: qcov, qcovhsp, qcovs'
        else:
            raise AssertionError('missing coverage was accepted')
        assert 'nevelib.search.hits' not in sys.modules
    """)
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_compatibility_exports_keep_record_identity_and_pickle_path():
    from nevelib.search import hit_calculations, hits

    for name in (
        'BlastHit', 'normalize_blast_strand', 'filter_hits',
        'select_best_hit_per_query', 'prune_contained_intervals',
        'merge_blast_hits_to_regions', 'filter_hits_by_bitscore_fraction',
    ):
        assert getattr(hits, name) is getattr(hit_calculations, name)
    hit = hits.BlastHit('q', 's', 90, 10, 1, 0, 1, 10, 11, 20, 1e-5, 50)
    assert type(hit).__module__ == 'nevelib.search.hits'
    assert pickle.loads(pickle.dumps(hit)) == hit
