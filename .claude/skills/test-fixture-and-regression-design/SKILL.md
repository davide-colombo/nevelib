---
name: test-fixture-and-regression-design
description: "Use when designing or auditing tests for scientific or data-pipeline code; build minimal fixtures with clear invariants and a regression test that would fail before the fix."
license: "MIT"
---

# Test Fixture and Regression Design

## Purpose

Determine whether the test layer for a scientific or data-pipeline change has minimal synthetic fixtures focused on invariants, regression coverage that would have failed before the fix, and clear separation among unit, integration, smoke, and production-scale validation. Detect brittle dependence on large production data, implicit conventions hidden in fixtures, weak assertions, missing valid-empty cases, and absent regression coverage for previously failed behaviors.

## Composition role

Default role: **module**. This skill contributes domain-specific checks and findings.

- **Can be primary when directly selected:** yes. When the task objective is specifically this domain, it owns the report and verdict.
- **Owns a report when composed:** no. Within a larger workflow it reports into the primary skill's schema as a labeled subsection or findings table and emits no second top-level verdict; its verdict becomes a component status that rolls up into the primary verdict.

## When to use

Use before implementing a fix that requires a test, after a fix that needs regression coverage, when proposed tests are too dependent on production data, when fixtures conceal conventions the test should expose, or when a test layer must be re-partitioned across unit, integration, smoke, and production-scale tiers. Apply alongside [`code-review-and-test-audit`](../code-review-and-test-audit/SKILL.md) for general code-and-test review. When composed, one skill is the primary for the task and owns the report and top-level verdict; the others contribute their findings as labeled subsections and emit no second top-level verdict.

## When not to use

Do not use as authorization to implement code changes or to publish results. Do not substitute it for code review, security review, or domain validation. Do not use it to evaluate large-scale benchmark results; those belong in production-scale validation, not in fixture design.

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- The behavior to be tested, including the contract or invariant under test.
- The current test layout and the boundary between unit, integration, smoke, and production-scale tiers.
- Permission to add fixtures, modify tests, or only review.

If the behavior, invariant, or test boundary cannot be established, stop and report. Do not infer test scope from filename or convention.

## Optional inputs

Use when supplied or discoverable within scope:

- Prior failure records for the behavior under test, including reproducer details.
- Existing fixtures and their construction code.
- Schema definitions used by code under test.
- Runtime configuration and environment matrix.

Treat absent evidence as uncertainty, not as proof of adequate coverage.

## Task modes

Choose exactly one mode and state it in the report:

- `FIXTURE_DESIGN_REVIEW`: Evaluate proposed fixtures and tests before implementation.
- `REGRESSION_TEST_DESIGN`: Design a regression test for a specific reproducible defect.
- `COVERAGE_AUDIT`: Inspect the existing test layer for missing or weak coverage of stated invariants.
- `TIER_PARTITION_AUDIT`: Evaluate the boundary among unit, integration, smoke, and production-scale tests.
- `FIXTURE_REDUCTION_AUDIT`: Replace production-data dependency with minimal synthetic fixtures where invariants can be proven.

A mode changes audit emphasis; it does not authorize commit, merge, or release.

## Minimal synthetic fixtures for invariants

For every invariant under test:

- Construct the smallest fixture that exercises the invariant.
- Avoid embedding unrelated data, large records, or domain-irrelevant content.
- Construct fixtures programmatically when their structure can be expressed in code, with deterministic seeds and named constants.
- Document the invariant the fixture exercises and the failure mode it would expose.

A fixture that exists only as a binary blob inherited from production is opaque. Replace it with a constructed equivalent or document why the binary form is necessary.

## Avoiding brittle dependence on large production data

When a test depends on production data:

- Confirm the dependency is required by the invariant (for example, real-world distribution, scale-dependent behavior).
- Confirm the production data is preserved with deterministic identity and version.
- Confirm the test still proves something when the production data is updated or replaced.
- Detect tests that pass only on a specific machine, a specific snapshot, or a specific user's environment.

Production-data-only tests are smoke or production-scale, not unit or integration. Re-tier them when their layer is wrong.

## Explicit coordinate conventions

When the behavior involves positions, intervals, or alignments:

- Encode the coordinate convention (zero-based or one-based) and the interval convention (inclusive or half-open) in the fixture's documented constants.
- Construct fixtures that distinguish convention errors (off-by-one, off-by-end, swapped endpoints).
- Assert against expected coordinates explicitly, not against opaque tool outputs.

A fixture that hides its coordinate convention cannot detect a convention drift.

## Valid-empty versus missing-output behavior

For every behavior whose contract permits a valid-empty result:

- Include a fixture whose correct output is valid-empty.
- Include a fixture whose correct output is missing because the input is missing.
- Include a fixture whose correct output is a sentinel rather than an absent file, when the contract requires a sentinel.
- Assert that the consumer of the output distinguishes these cases.

A test layer that never exercises valid-empty cases cannot detect when valid-empty is misclassified as failure or vice versa.

## Schema and runtime parity

For tests that consume tabular or structured outputs:

- Use a fixture that matches the schema contract, including delimiter, encoding, header, column names, and column order when contractual.
- Assert against the schema, not against tool defaults.
- Include a fixture that violates the schema by a single element and confirm the test would fail.

Cross-reference [`output-contract-and-table-schema-audit`](../output-contract-and-table-schema-audit/SKILL.md) when schema parity is the central concern.

## Deterministic sorting

For tests whose assertions depend on output order:

- Confirm that the producer guarantees a deterministic sort.
- Construct fixtures that would expose non-determinism (tie cases, equal keys, multiple valid orderings).
- Assert against the deterministic order, not against the first order observed in a passing test.

If the producer does not guarantee sort, the test must canonicalize order before assertion.

## Duplicate handling

For tests whose subject must dedupe, merge, or reject duplicates:

- Construct fixtures with duplicate primary keys, near-duplicate keys (whitespace, case), and duplicated payloads under distinct keys.
- Assert the resulting behavior matches the contract (deduplicate, merge, reject, or pass through).

## Controlled-vocabulary failures

For tests on columns whose values come from a controlled vocabulary:

- Construct a fixture with each valid value at least once.
- Construct a fixture with an unknown value to confirm rejection or accepted-with-warning behavior.
- Construct a fixture with vocabulary drift (renamed value, retired value) to confirm detection.

## Boundary conditions

For every input boundary under test:

- Construct fixtures that exercise the minimum and maximum supported value.
- Construct fixtures that exercise off-by-one at each boundary.
- Construct fixtures that exercise empty, single-element, and large-but-bounded inputs.

A fixture set that exercises only the middle of the input space cannot detect boundary errors.

## Resume and checkpoint behavior

For tests that exercise resumable code:

- Construct a fixture state representing an interrupted unit (output present, sentinel absent).
- Construct a fixture state representing a corrupted unit (sentinel present, output partial).
- Construct a fixture state representing a stale unit (sentinel present, output present, but binding to an older input or configuration).
- Assert the resume decision matches the contract under [`resumable-pipeline-design`](../resumable-pipeline-design/SKILL.md).

## Regression tests before or alongside fixes

For every reproducible defect:

- Add a regression test that fails on the unfixed code and passes on the fixed code.
- Confirm the regression test fails for the right reason (correct assertion, correct error class) and not by coincidence.
- Confirm the regression test is named and located so a later contributor finds it when modifying the same behavior.

A fix that ships without a failing-before-fix regression test will silently regress.

## Separation of unit, integration, smoke, and production-scale validation

Define the tiers explicitly:

- `unit test`: Exercises a single function or small composition, uses minimal synthetic fixtures, runs in subseconds, has no external dependencies, and asserts a specific invariant.
- `integration test`: Exercises two or more components together, uses controlled fixtures, may invoke real I/O against temporary paths, and asserts cross-component contracts.
- `smoke test`: Exercises end-to-end behavior on a small fixture, intended as a quick deployability or sanity check.
- `production-scale validation`: Exercises behavior on production-like or production data and is not part of the standard test run.

A test in the wrong tier either runs too rarely to protect contracts or too slowly to run before each change. Re-tier mis-placed tests.

## Explicit statement of what each fixture proves and does not prove

For each fixture, record explicitly:

- The invariant the fixture proves.
- The conditions under which the fixture would fail.
- The conditions under which the fixture would pass for the wrong reason.
- The behaviors the fixture does not exercise.

A fixture that is not accompanied by these statements cannot be evaluated for regression value.

## Audit procedure

1. Restate the objective, selected task mode, scope, and test layer under audit.
2. Enumerate the invariants the test layer is supposed to protect.
3. For each invariant, identify the smallest synthetic fixture sufficient to prove it.
4. Identify production-data dependencies and re-tier or replace them where possible.
5. Inspect coordinate, interval, schema, sort, duplicate, controlled-vocabulary, boundary, and resume coverage.
6. Inspect each fixture's documentation of what it proves and does not prove.
7. Inspect regression coverage for previously reproduced defects.
8. Inspect the tier partition for unit, integration, smoke, and production-scale tests.
9. Classify findings, record commands actually run and evidence unavailable, and select exactly one verdict.

Do not treat a passing test run as proof that the invariant is protected; assess the assertion and fixture together.

## Stop-and-report triggers

Stop before merging or releasing test changes when:

- An invariant has no fixture that would expose its violation.
- A regression test does not fail on the unfixed code.
- A fixture passes by coincidence rather than by asserting the invariant.
- Production-data dependence cannot be replaced and cannot be re-tiered.
- Coordinate, interval, schema, sort, duplicate, vocabulary, boundary, or resume coverage is missing for behavior under change.
- A test sits in the wrong tier and either runs too rarely or too slowly to protect the contract.
- A fixture lacks a stated invariant and failure-mode rationale.
- Required evidence cannot be inspected and the gap prevents a reliable verdict.

Report the trigger, affected invariant or fixture, evidence, and minimum decision or authorization required.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `MODE AND SCOPE`: selected task mode, behavior under test, test layer boundary, allowed scope, and exclusions.
3. `INVARIANT INVENTORY`: each invariant the test layer protects, with the fixture that proves it.
4. `FIXTURE DESIGN`: each fixture's construction, what it proves, what it does not prove, and tier placement.
5. `PRODUCTION-DATA DEPENDENCE`: tests with production-data dependence, justification, and re-tier or replacement recommendation.
6. `COVERAGE OF CRITICAL CASES`: coordinates, schema, sort, duplicates, vocabulary, boundaries, valid-empty, and resume cases.
7. `REGRESSION COVERAGE`: each previously reproduced defect, its regression test, and failing-before-fix evidence.
8. `TIER PARTITION`: unit, integration, smoke, and production-scale assignments and re-tier recommendations.
9. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, checks not run, and impact.
10. `FINDINGS`: blocking findings and non-blocking warnings with location, evidence, consequence, and minimum resolution; write `none` for empty categories.
11. `NEXT STEP`: the minimum design correction, fixture construction, regression-test addition, or re-tier action supported by the verdict.

Do not claim a test layer protects an invariant unless a fixture that would expose the violation has been inspected.

## Allowed actions

- Read source code, test code, fixture construction code, schema definitions, and prior defect records within scope.
- Run local read-only inspection and explicitly authorized safe validation commands.
- Propose fixture constructions, regression tests, and tier re-partitions without applying them unless separately authorized.

## Forbidden actions

- Merge or release tests without inspecting whether they fail for the right reason.
- Treat a passing test as proof of invariant protection.
- Ship a fix without a failing-before-fix regression test for reproducible defects.
- Replace a missing fixture with a snapshot of current behavior captured during the audit.
- Include production data in fixtures when synthetic equivalents exercise the same invariant.
- Expose private paths, restricted identifiers, or sensitive content in fixtures.

## Verdict vocabulary
When composed under another primary skill, report this as a component status under that skill's findings, not as the task's top-level verdict.

- `TEST_DESIGN_READY`: Invariant coverage, fixture design, production-data dependence, critical-case coverage, regression coverage, and tier partition satisfy the selected mode with no remaining warnings.
- `TEST_DESIGN_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking fixture, coverage, regression, or tier findings prevent acceptance.
- `COVERAGE_UNSAFE`: An invariant is unprotected, a fixture passes by coincidence, or a regression test cannot fail on the unfixed code.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe inspection conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested test design, fixture change, or coverage area exceeds authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when the audit itself cannot proceed safely, `COVERAGE_UNSAFE` for demonstrated unprotected invariants, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when each invariant is paired with a fixture that would expose its violation.
