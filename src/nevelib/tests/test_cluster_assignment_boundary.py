"""Decoded cluster pairs have a deterministic, adapter-independent contract."""

import subprocess
import sys
import textwrap

import pytest

from nevelib.clustering.parse import parse_mmseqs_clusters


@pytest.mark.parametrize('text,ids,expected', [
    ('z\tb\na\tc\n', ['c', 'b', 'a', 'missing', 'a'],
     [('a', 1, True, 'a'), ('c', 1, False, 'a'), ('b', 2, False, 'z'), ('missing', 3, True, 'missing')]),
    ('ignored\tother\n', ['b', 'a'], [('a', 1, True, 'a'), ('b', 2, True, 'b')]),
    ('', [], []),
])
def test_parser_assignment_oracle(tmp_path, text, ids, expected):
    path = tmp_path / 'clusters.tsv'
    path.write_text(text)
    original = list(ids)
    assignments = parse_mmseqs_clusters(path, ids)
    assert [(a.sequence_id, a.cluster_id, a.is_representative, a.representative_id) for a in assignments] == expected
    assert ids == original


def test_conflicting_membership_error(tmp_path):
    path = tmp_path / 'clusters.tsv'
    path.write_text('z\tb\na\tb\n')
    with pytest.raises(ValueError, match="Sequence ID 'b' appears in multiple clusters: 'a' and 'z'."):
        parse_mmseqs_clusters(path, ['b'])


def test_assignment_calculation_is_independent_and_compatible():
    code = textwrap.dedent("""
        import importlib.abc
        import sys
        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in {'nevelib.clustering.parse', 'nevelib.clustering.mmseqs'} or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)
        blocker = BlockAdapters()
        sys.meta_path.insert(0, blocker)
        from nevelib.clustering.assignments import ClusterAssignment, assign_cluster_pairs, cluster_assignments_to_dataframe
        pairs = [('b', 'c')]
        ids = ['c', 'a']
        result = assign_cluster_pairs(pairs, ids)
        assert [(r.sequence_id,r.cluster_id,r.representative_id) for r in result] == [('c',1,'b'),('a',2,'a')]
        assert pairs == [('b','c')] and ids == ['c','a']
        frame = cluster_assignments_to_dataframe(result)
        assert frame.sequence_id.tolist() == ['c','a']
        assert str(frame.cluster_id.dtype) == 'int64'
        assert str(frame.is_representative.dtype) == 'bool'
        assert cluster_assignments_to_dataframe([]).columns.tolist() == ['sequence_id','cluster_id','is_representative','representative_id']
        sys.meta_path.remove(blocker)
        from nevelib.clustering import parse
        assert parse.ClusterAssignment is ClusterAssignment
        assert parse.cluster_assignments_to_dataframe is cluster_assignments_to_dataframe
        assert ClusterAssignment.__module__ == 'nevelib.clustering.parse'
    """)
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
