"""Generic containment decisions must not require FASTA or tool adapters."""

import subprocess
import sys
import textwrap

import pytest

from nevelib.assembly.dedup import _select_contigs_to_remove


@pytest.mark.parametrize('rows,expected', [
    ([], set()),
    ([('a', 5, 'a', 5)], set()),
    ([('a', 5, 'b', 4)], set()),
    ([('a', 5, 'b', 5)], {'a'}),
    ([('a', 5, 'b', 6)], {'a'}),
    ([('a', 5, 'unknown', 6), ('unknown', 5, 'a', 6)], set()),
    ([('a', 5, 'b', 5), ('b', 5, 'a', 5)], {'a', 'b'}),
])
def test_containment_selection_preserves_decisions_and_inputs(rows, expected):
    original = list(rows)
    known = {'a', 'b'}
    assert _select_contigs_to_remove(rows, known_ids=known) == expected
    assert rows == original
    assert known == {'a', 'b'}


def test_containment_owner_is_independent_and_adapter_delegates():
    code = textwrap.dedent("""
        import importlib.abc
        import sys
        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname == 'nevelib.assembly.dedup' or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)
        blocker = BlockAdapters()
        sys.meta_path.insert(0, blocker)
        from nevelib.assembly.contig_selection import _select_contigs_to_remove
        assert _select_contigs_to_remove([('a', 5, 'b', 5)], known_ids={'a', 'b'}) == {'a'}
        sys.meta_path.remove(blocker)
        from nevelib.assembly import dedup
        assert dedup._select_contigs_to_remove is _select_contigs_to_remove
    """)
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
