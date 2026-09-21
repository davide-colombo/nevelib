# Rank numeric representatives once per merge

Status: done
Opened: 2026-09-21
Baseline: 044aa9dad93d0b278883bb7604b8c156ad176720, clean master; working branch
codex/057-merge-representative-selection. Local development only.

## Objective and authority

The owner authorized the next increment after the nexteveApp host-calculation
profile. Remove repeated per-region representative sorting where ranking is
equivalent, preserving both outputs of merge_blast_hits_to_regions. Follow
AGENTS.md, the project profile, source/test guidance, docs/contracts.md and
docs/architecture.md. No commit of this new increment, dependency change,
integration, release, remote or production action is authorized.

## Interface and invariants

Input is the existing DataFrame plus unchanged column selectors and max_gap_bp.
The coordinate sweep and gap rule are unchanged. Output is the same ordered
region DataFrame and original-index-aligned Series, including duplicate indices,
payload types, missing values and the current nonempty mapping dtype. The three
nexteveApp annotation finalizers are direct consumers; their configuration,
coherence overrides, logging and serialization remain unchanged.

After grouping completes, when there are multiple regions and both ranking
columns have real NumPy numeric/bool dtypes, sort the existing coordinate-ordered
work once by score descending, evalue ascending and original index ascending.
Keep ranks outside the DataFrame. Select each region's smallest rank and retrieve
that row through the same DataFrame-to-Series boundary. Stable complete ties use
existing coordinate order, including duplicate original indices.

Retain the existing region-local sort for object, categorical, extension, complex
or otherwise unsupported ranking dtypes, and for a single region. Do not rank
before the sweep: error precedence must remain intact. Do not normalize indices,
mapping dtypes, missing groups, input errors or payload values. Global sorting
arbitrary objects can compare values from different regions that baseline never
compared, so an unrestricted global sort is explicitly rejected.

## Scope and sequence

Allowed nevelib edits: src/nevelib/search/hits.py,
src/nevelib/tests/test_merge_blast_hits_to_regions.py and this plan. nexteveApp
Task 057 owns cross-project records and validation; its runtime remains unchanged.

1. Add hand-computed characterization for missing ranks, duplicate/string/tuple
   indices, payload/extension dtypes and unsupported-score fallback. Run against
   baseline; behavior-preserving characterization is expected to pass before and
   after. Existing focused baseline is 59 passed.
2. Implement only numeric pre-ranking and the representative lookup. Leave region
   grouping, IDs, payload construction and mapping assignment unchanged.
3. Run focused and full nevelib suites in the existing inspected .venv environment;
   repeat focused tests in the nexteve-app consumer environment. Differentially
   compare both outputs, dtypes and exceptions with the Git baseline across a
   deterministic bounded input matrix. No retained duplicate reference code.
4. Run nexteveApp's focused annotation/downstream suite and the unchanged Task 056
   harness against this checkout. Compare output digest and unprofiled before/after
   timings, accounting for profiler overhead and synthetic-workload limits.
5. Independently review actual diff and tests; rerun focused checks and benchmark.
   Close both projects' records and leave both diffs uncommitted.

## Validation and recovery

From nevelib, use PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q
-p no:cacheprovider --basetemp=<fresh-scratch> with focused files
src/nevelib/tests/test_merge_blast_hits_to_regions.py and test_search.py, then
src/nevelib/tests for the full suite. The existing environment is Python 3.14.7,
pandas 3.0.1. Consumer tests use conda run -n nexteve-app python with the same
pytest isolation options. Source lookup must resolve to the inspected checkouts.
All scratch and measurement reports go under the task's configured external data
root, never into either repository. No wall-time threshold enters correctness
tests. Require identical outputs/errors, meaningful measured benefit, unchanged
consumer behavior, git diff --check and independent PASS. Corrections remain
within this diff; no reset, cleanup or environment mutation.

## Progress

- [x] 2026-09-21: Clean baseline, branch and declared environment verified; focused
  suite 59 passed. Fresh consumer benchmark median 0.402862 s.
- [x] 2026-09-21: Added 21 characterization cases; all 80 focused tests passed
  before runtime changes and after implementation in .venv. They also pass in
  the nexteve-app environment (pandas 2.2.2).
- [x] 2026-09-21: Both environments matched baseline across 1,600 deterministic
  cases each: 1,455 equal DataFrame/Series pairs and 145 equal error type/messages,
  with no input mutation. Full nevelib suite: 311 passed. Consumer suite: 156 passed.
- [x] 2026-09-21: Host benchmark median decreased from 0.402862 s to 0.178816 s;
  independent rerun median 0.178939 s. All output digests match.
- [x] 2026-09-21: Independent review found no material issue, reran 80 focused
  tests and the 1,600-case differential matrix, and verified the benchmark.
  Both diff checks pass; all changes remain unstaged and uncommitted.

## Discoveries and decisions

- Independent trace found baseline success for incomparable object scores in
  separate regions and ignored missing-group rows with unhashable scores.
  Preserve these paths through the original local-sort fallback.
- Do not add ranking columns or normalize existing float64 region assignments.
- Measurement-driven optimization is the intended change; no scientific result
  should fail baseline characterization. Performance is measured separately.

## Outcome

Numeric workloads with multiple regions now rank once, replacing repeated local
representative sorts. Both public outputs, exceptions and consumers remain
consistent with the tested baseline. Only this source function, its focused tests
and this plan changed in nevelib. No version or dependency change was made.

The measured synthetic host workload uses about 56% less unprofiled wall time
(approximately 2.25 times as fast). This is not a production or hardware-counter
claim; other ranking dtypes retain the original path. The full scientific
nexteveApp suite was not run, only the ten-module consumer selection.

The next action is a separately authorized commit of the coordinated changes,
then whole-series review before integration or release. No further optimization
is included in this increment.
