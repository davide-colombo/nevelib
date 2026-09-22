"""PAF calculations consume explicit records without loading file/tool adapters."""

import subprocess
import sys
import textwrap

from nevelib.mapping.paf import PafRecord, alignment_identity, best_hit_per_query, query_coverage, target_coverage


def test_paf_calculation_units_ties_and_identity():
    later = PafRecord('q', 20, 5, 15, '-', 'z', 40, 10, 20, 8, 10, 60, {'tp': 'A'})
    first = PafRecord('q', 20, 5, 15, '-', 'a', 40, 10, 20, 8, 10, 60)
    records = [later, first]
    assert (alignment_identity(first), query_coverage(first), target_coverage(first)) == (0.8, 0.5, 0.25)
    assert best_hit_per_query(records)['q'] is first
    assert records == [later, first] and later.tags == {'tp': 'A'}


def test_paf_calculation_independent_import_and_compatibility():
    code = textwrap.dedent("""
        import importlib.abc
        import sys
        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in {'nevelib.mapping.paf','nevelib.mapping.minimap2'} or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)
        blocker = BlockAdapters()
        sys.meta_path.insert(0, blocker)
        from nevelib.mapping.alignment_selection import (
            PafRecord, alignment_identity, query_coverage, target_coverage,
            filter_paf_records, best_hit_per_query,
        )
        record = PafRecord('q',0,0,0,'+','t',0,0,0,0,0,0)
        assert (alignment_identity(record),query_coverage(record),target_coverage(record)) == (0.0,0.0,0.0)
        assert filter_paf_records([record],min_identity=0.0)[0] is record
        assert filter_paf_records([record],min_identity=0.1) == []
        assert best_hit_per_query([]) == {}
        try:
            best_hit_per_query([],metric='unknown')
        except ValueError as exc:
            assert str(exc) == 'Unsupported metric for PafRecord: unknown'
        else:
            raise AssertionError('unknown metric accepted')
        sys.meta_path.remove(blocker)
        from nevelib.mapping import paf
        assert paf.PafRecord is PafRecord
        assert paf.best_hit_per_query is best_hit_per_query
        assert PafRecord.__module__ == 'nevelib.mapping.paf'
    """)
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
