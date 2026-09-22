"""Alignment metrics operate on decoded sequences without FASTA/tool imports."""

import subprocess
import sys
import textwrap

from nevelib.msa.metrics import MetricsConfig, compute_alignment_metrics


def test_alignment_metric_ties_denominators_and_length_precedence():
    sequences = {'b': 'T-', 'a': 'AA'}
    lengths = {'a': 10, 'b': 2, 'not_aligned': 8}
    result = compute_alignment_metrics(
        sequences, MetricsConfig(occupancy_threshold=0.5, min_seq_length=8),
        core_lengths=lengths, original_lengths={'a': 999},
    )
    assert vars(result) == dict(
        n_total=3, n_aligned=2, shared_span_bp=2, shared_span_frac=1.0,
        median_identity=0.5, p10_identity=0.0,
        median_sequence_length=6.0, frac_length_ge_min=0.5,
    )
    assert sequences == {'b': 'T-', 'a': 'AA'}
    assert lengths == {'a': 10, 'b': 2, 'not_aligned': 8}


def test_alignment_metrics_independent_import_and_compatibility():
    code = textwrap.dedent("""
        import importlib.abc
        import sys
        class BlockAdapters(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname in {'nevelib.msa.metrics','nevelib.msa.mafft'} or fullname.startswith('nevelib._common'):
                    raise AssertionError('calculation imported adapter: ' + fullname)
        blocker = BlockAdapters()
        sys.meta_path.insert(0, blocker)
        from nevelib.msa.alignment_metrics import AlignmentMetrics, MetricsConfig, compute_alignment_metrics
        empty = compute_alignment_metrics({}, MetricsConfig(), core_lengths={'a': 4})
        assert empty.n_total == 1 and empty.n_aligned == 0 and empty.median_identity is None
        assert compute_alignment_metrics({'a': 'NN'}, MetricsConfig()).median_identity == 1.0
        try:
            compute_alignment_metrics({'a':'A','b':'AA'}, MetricsConfig())
        except ValueError as exc:
            assert str(exc) == 'Alignment sequences have inconsistent lengths.'
        else:
            raise AssertionError('unequal widths accepted')
        sys.meta_path.remove(blocker)
        from nevelib.msa import metrics
        assert metrics.AlignmentMetrics is AlignmentMetrics
        assert metrics.MetricsConfig is MetricsConfig
        assert metrics.compute_alignment_metrics is compute_alignment_metrics
        assert AlignmentMetrics.__module__ == MetricsConfig.__module__ == 'nevelib.msa.metrics'
    """)
    result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
