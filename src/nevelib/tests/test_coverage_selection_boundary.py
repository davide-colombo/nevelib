"""Coverage policy is independent of mapping tools and publication."""

import subprocess
import sys
import textwrap

import pytest


def test_coverage_table_contract_before_and_after_extraction(tmp_path):
    from nevelib.assembly.coverage import _write_coverage_tsv

    records = [('b', 'AC'), ('a', 'ACG'), ('missing', 'A')]
    coverage = {'a': (3, 6, 2.0), 'b': (2, 1, 0.5)}
    path = tmp_path / 'coverage.tsv'
    _write_coverage_tsv(records, coverage, path, min_mean_coverage=2.0)
    assert path.read_text() == (
        'contig_id\tlength\tbases\tmean_coverage\tpass\n'
        'b\t2\t1\t0.500000\tfalse\n'
        'a\t3\t6\t2.000000\ttrue\n'
        'missing\t1\t0\t0.000000\tfalse\n'
    )
    _write_coverage_tsv(records, None, path, min_mean_coverage=2.0, force_pass=True)
    assert path.read_text().splitlines()[1:] == [
        'b\t2\t0\t0.000000\ttrue', 'a\t3\t0\t0.000000\ttrue',
        'missing\t1\t0\t0.000000\ttrue',
    ]


@pytest.mark.parametrize('coverage,threshold,unmapped,passing', [
    ({}, 2.0, True, []),
    ({'a': (2, 0, 0.0)}, 2.0, True, []),
    ({'a': (2, -2, -1.0)}, 2.0, True, []),
    ({'a': (2, 4, 2.0)}, 2.0, False, ['a']),
    ({'a': (2, 4, 2.0)}, 0.0, False, ['a', 'b']),
    ({'b': (3, 9, 3.0), 'a': (2, 4, 2.0)}, 2.0, False, ['a', 'b']),
    ({'a': (2, 0, float('nan'))}, 2.0, False, []),
])
def test_coverage_decisions_and_nonmutation(coverage, threshold, unmapped, passing):
    from nevelib.assembly.coverage_selection import coverage_is_unmapped, select_covered_records

    records = [('a', 'AC'), ('b', 'ACG')]
    original = dict(coverage)
    assert coverage_is_unmapped(records, coverage) is unmapped
    assert [item[0] for item in select_covered_records(records, coverage, threshold)] == passing
    assert records == [('a', 'AC'), ('b', 'ACG')]
    assert coverage == original


def test_coverage_calculations_do_not_import_adapters():
    code = textwrap.dedent("""
        import importlib.abc
        import sys
        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'nevelib.assembly.coverage' or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)
        sys.meta_path.insert(0, BlockAdapters())
        from nevelib.assembly.coverage_selection import coverage_is_unmapped, select_covered_records, coverage_rows
        assert coverage_is_unmapped([], {})
        assert select_covered_records([], {}, 2) == []
        assert list(coverage_rows([], {}, min_mean_coverage=2)) == []
        assert list(coverage_rows([('a', 'AC')], None, min_mean_coverage=2, force_pass=True)) == [('a', 2, 0, 0.0, True)]
    """)
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
