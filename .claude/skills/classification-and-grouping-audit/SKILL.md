---
name: classification-and-grouping-audit
description: "Use when clustering or classification outputs will be consumed or compared; audit grouping objective, thresholds, determinism, over-merge/over-split risk, and interpretation limits."
license: "MIT"
---

# Classification and Grouping Audit

## Purpose

Determine whether a clustering, grouping, classification, label-assignment, or variant-splitting procedure has an explicit grouping objective, well-defined input units, defensible thresholds, deterministic behavior, documented tie-breaking, transparent connected-component or merging logic, an inspectable representative-selection rule, an explicit singleton or outlier policy, sensitivity evidence at material thresholds, an old-versus-new comparison when applicable, preserved record identity across runs, diagnostic artifacts for human review, stable sorting and label assignment, no metadata leakage in labels, and a clear separation between algorithmic groups and biological or scientific interpretation.

## Composition role

Default role: **module**. This skill contributes domain-specific checks and findings.

- **Can be primary when directly selected:** yes. When the task objective is specifically this domain, it owns the report and verdict.
- **Owns a report when composed:** no. Within a larger workflow it reports into the primary skill's schema as a labeled subsection or findings table and emits no second top-level verdict; its verdict becomes a component status that rolls up into the primary verdict.

## When to use

Use before downstream decisions consume cluster, group, or classification outputs; before a new grouping result replaces a prior result; when a grouping algorithm is being parameterized or changed; when over-merging or over-splitting is suspected; when reviewers must compare an old grouping to a new grouping; or when an automatically produced grouping is being framed as a biological conclusion. Apply alongside [`scientific-data-integrity-audit`](../scientific-data-integrity-audit/SKILL.md) when the grouping informs a scientific claim, [`bioinformatics-sequence-output-audit`](../bioinformatics-sequence-output-audit/SKILL.md) when the input is sequences, [`output-contract-and-table-schema-audit`](../output-contract-and-table-schema-audit/SKILL.md) when the output is tabular, and [`agent-output-verification-and-claim-audit`](../agent-output-verification-and-claim-audit/SKILL.md) when an agent report summarizes grouping behavior. When composed, one skill is the primary for the task and owns the report and top-level verdict; the others contribute their findings as labeled subsections and emit no second top-level verdict.

## When not to use

Do not use as authorization to publish, share, or act on grouping results. Do not substitute it for statistical methodology review or peer review. Do not use it to evaluate file-format details independent of grouping; defer to schema or sequence audits. Do not use it to evaluate scientific interpretation in isolation; defer to `scientific-data-integrity-audit`.

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- The grouping algorithm, its input set, and its declared output.
- The downstream consumer set and the assumptions each consumer makes about groups.
- Permission boundaries: whether parameters may be changed and whether comparison runs may be invoked.

If the algorithm, input set, output, or consumer set cannot be established, stop and report.

## Optional inputs

Use when supplied or discoverable within scope:

- Prior grouping outputs for comparison.
- Threshold rationale documents and sensitivity-analysis records.
- Diagnostic artifacts used in prior review.
- Reference labels or hand-curated groupings for evaluation.

Treat absent evidence as uncertainty, not as proof that grouping is correct.

## Task modes

Choose exactly one mode and state it in the report:

- `GROUPING_OBJECTIVE_REVIEW`: Evaluate the stated grouping objective and whether the algorithm matches it.
- `THRESHOLD_AND_SENSITIVITY_AUDIT`: Inspect threshold choices, tie-breaking, and threshold sensitivity.
- `DETERMINISM_AUDIT`: Inspect whether grouping is reproducible across reruns under identical inputs.
- `OLD_VS_NEW_COMPARISON_AUDIT`: Compare a new grouping output to a prior result, classifying merges, splits, retentions, and reassignments.
- `REPRESENTATIVE_SELECTION_AUDIT`: Inspect the representative or label-assignment rule.
- `INTERPRETATION_BOUNDARY_AUDIT`: Inspect the separation between algorithmic grouping and biological or scientific interpretation.

A mode changes audit emphasis; it does not authorize parameter changes, publication, or downstream action.

## Grouping objective

State explicitly:

- The objective the grouping must satisfy (for example, partition by identity at a threshold, partition by clustering of a similarity graph, classify by trained model).
- The granularity of the desired group (one group per input, one group per latent class, one group per equivalence class).
- The downstream decision the grouping supports.
- The acceptable error modes (over-merging tolerated, over-splitting tolerated, neither tolerated).

A grouping algorithm whose objective is implicit cannot be evaluated for correctness.

## Input units

For the input to the grouping:

- Document what one input unit is (one sequence, one record, one observation, one sample).
- Confirm the input set is enumerated and stable for the duration of the grouping.
- Confirm input units have stable identifiers across runs.
- Detect input units that drift in identity (renamed, reordered, regenerated) between runs.

Inputs whose identity drifts cannot support old-versus-new comparison.

## Identity, coverage, and distance thresholds

For every threshold the algorithm uses:

- Record the threshold value, the comparison direction, the unit, and the measure.
- Record the rationale (calibration, prior literature, sensitivity analysis, domain practice).
- Confirm the threshold is applied consistently across the run.
- Detect thresholds whose only rationale is "the value that produced the desired result".

A threshold without rationale is an assumption masquerading as evidence.

## Deterministic grouping

For each grouping run:

- Confirm the algorithm produces identical groups under identical inputs and parameters.
- Confirm random seeds are recorded and applied where the algorithm uses randomness.
- Confirm parallel or distributed execution does not introduce nondeterministic ordering.
- Detect dependence on hardware, locale, or transient system state.

A nondeterministic grouping cannot be audited or reproduced.

## Tie-breaking rules

When grouping decisions can produce ties:

- Document the tie-breaking rule (lexicographic on input identifier, fixed priority order, first observed).
- Confirm tie-breaking is applied consistently.
- Detect ties resolved by run-time ordering accidents.

Tie-breaking accidents corrupt comparisons across runs.

## Connected-component behavior

For graph-based or transitive grouping:

- Document the edge-construction rule and the edge-existence threshold.
- Document the connected-component rule (transitive closure, single-link, complete-link, density-based).
- Detect transitivity that allows weak edges to merge otherwise distinct groups.
- Detect connected components that include records the consumer would consider distinct.

A connected-component rule that hides transitivity is a hidden contract.

## Representative selection

For each group, document the representative-selection rule:

- Length-based, quality-based, centrality-based, centroid-based, first-observed, or other.
- The tie-breaking rule when multiple records satisfy the primary rule.
- The traceability of the representative back to its source record.
- Whether representative selection is stable across reruns under identical inputs.

A representative selected by ordering accident is not stable across runs.

## Over-merging risk

For each grouping objective:

- Identify the conditions under which two distinct latent classes would be merged.
- Quantify or describe the false-merge rate under the chosen threshold or parameter.
- Document the consumer's tolerance for over-merging.
- Recommend diagnostic artifacts that expose over-merging.

A grouping that hides its over-merging behavior is unsafe.

## Over-splitting risk

For each grouping objective:

- Identify the conditions under which one latent class would be split.
- Quantify or describe the false-split rate under the chosen threshold or parameter.
- Document the consumer's tolerance for over-splitting.
- Recommend diagnostic artifacts that expose over-splitting.

Over-splitting inflates apparent diversity. Record and report.

## Singleton and outlier policy

For records that do not satisfy any group's membership rule:

- Document whether they are emitted as singleton groups, assigned to a special outlier label, or excluded from output.
- Document the consumer's interpretation of singletons or outliers.
- Detect silent exclusion that hides records from downstream consumers.

A silent-exclusion policy converts data into apparent absence.

## Threshold sensitivity

For the chosen thresholds and parameters:

- Inspect grouping behavior at adjacent threshold values.
- Record group-count changes, merge events, and split events as thresholds change.
- Identify thresholds at sharp transitions in grouping behavior.
- Document the consumer's tolerance for sensitivity.

A grouping whose sensitivity is unmeasured cannot defend its parameter choice.

## Old-versus-new output comparison

When a new grouping replaces a prior result:

- Map each new group to the prior groups whose records overlap with it.
- Classify each new group as retained (same composition), merged (combines multiple prior groups), split (subset of one prior group), or reshuffled.
- Identify records that changed group membership and the magnitude of the change.
- Quantify the disagreement between old and new groupings (for example, by adjusted Rand index when defined, by record-level membership change rates, or by a project-specific comparison metric).

Without an old-versus-new comparison, consumers cannot trust that prior decisions still apply.

## Preservation of IDs, sequences, and records

Across grouping runs:

- Confirm input identifiers are preserved in output records.
- Confirm sequences or content payloads are not silently modified.
- Confirm record metadata is preserved.
- Cross-reference [`bioinformatics-sequence-output-audit`](../bioinformatics-sequence-output-audit/SKILL.md) when inputs are sequences.

A grouping that loses IDs or rewrites content cannot be traced back to source.

## Diagnostic artifacts for human review

For each grouping output, recommend or inspect diagnostic artifacts that support review:

- Group-size distribution.
- Edge or distance distribution within and between groups.
- Lists of merges, splits, retentions, and reshuffles relative to the prior run.
- Representative records and their group membership.
- Cases at threshold boundaries that a reviewer should inspect.

A grouping without diagnostic artifacts forces reviewers to reverse-engineer the algorithm.

## Stable sorting and label assignment

For the grouping's output:

- Confirm groups are emitted in a deterministic order.
- Confirm labels are assigned by a stable rule (lexicographic on representative, lexicographic on input identifier, fixed numeric scheme).
- Detect label assignment that depends on run-time ordering accidents.

Unstable labels cannot be referenced across runs.

## No metadata leakage in labels

Inspect labels for leakage:

- Detect labels that embed private machine paths, host names, run identifiers, or environment-specific strings.
- Detect labels that leak sample-level metadata not intended for the consumer.
- Recommend labels constructed only from the algorithm's intended output.

A label that carries unrelated metadata is a covert channel.

## Clear separation of algorithmic grouping from biological or scientific interpretation

State explicitly:

- The grouping output is an algorithmic partition under the chosen objective, threshold, and tie-breaking.
- The biological or scientific interpretation of a group requires additional evidence and is not produced by the algorithm.
- Consumers and downstream documents must distinguish algorithmic groups from named biological entities.
- Cross-reference [`scientific-data-integrity-audit`](../scientific-data-integrity-audit/SKILL.md) when interpretation claims are involved.

A report that conflates algorithmic groups with biological entities overclaims.

## Audit procedure

1. Restate the objective, selected task mode, scope, algorithm identity, input set, and consumer set.
2. Inspect the grouping objective and whether the algorithm matches it.
3. Inspect input units, identifiers, thresholds, tie-breaking, connected-component behavior, and representative-selection rules.
4. Inspect determinism, including random seed handling and parallel-execution behavior.
5. Inspect over-merging risk, over-splitting risk, singleton policy, and threshold sensitivity.
6. Compare the new grouping output to the prior result when applicable.
7. Inspect ID, sequence, and record preservation.
8. Inspect diagnostic artifacts, label stability, and label-content hygiene.
9. Inspect separation between algorithmic grouping and biological or scientific interpretation.
10. Classify findings, record commands actually run and evidence unavailable, and select exactly one verdict.

Do not treat a passing grouping run as proof of contract or scientific correctness.

## Stop-and-report triggers

Stop before downstream consumption, comparison, or publication when:

- The grouping objective is implicit and the algorithm's behavior cannot be evaluated against it.
- Input units lack stable identifiers across runs.
- Thresholds lack rationale and materially affect the grouping.
- The algorithm is nondeterministic or its random-seed handling is undocumented.
- Tie-breaking depends on run-time ordering accidents.
- Connected-component or merging behavior is transitive in a way the contract does not state.
- Representative selection is unstable across reruns.
- Over-merging or over-splitting cannot be characterized.
- Singletons or outliers are silently excluded.
- Threshold sensitivity is unmeasured at material parameter values.
- Old-versus-new comparison is required and cannot be inspected.
- IDs, sequences, or records are not preserved.
- Diagnostic artifacts required for review are absent.
- Labels embed metadata or are unstable across runs.
- Algorithmic groups are framed as biological entities without independent evidence.
- Required evidence cannot be inspected and the gap prevents a reliable verdict.

Report the trigger, affected groups or records, evidence, and minimum decision or authorization required.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `MODE AND SCOPE`: selected task mode, algorithm identity, input set, consumer set, allowed scope, and exclusions.
3. `GROUPING OBJECTIVE AND INPUTS`: stated objective, input-unit definition, identifier stability, and consumer interpretation.
4. `THRESHOLDS AND TIE-BREAKING`: thresholds, rationale, comparison direction, tie-breaking, and connected-component behavior.
5. `DETERMINISM`: random seeds, parallel-execution evidence, and reproducibility across reruns.
6. `RISK ANALYSIS`: over-merging, over-splitting, singleton/outlier policy, and threshold sensitivity.
7. `OLD VERSUS NEW COMPARISON`: per-group classification (retained, merged, split, reshuffled), record-level changes, and quantitative disagreement; write `none` when not applicable.
8. `REPRESENTATIVE SELECTION AND PRESERVATION`: representative rule, traceability, ID/sequence/record preservation.
9. `DIAGNOSTICS AND LABELS`: diagnostic-artifact inventory, label stability, and label-content hygiene.
10. `INTERPRETATION BOUNDARY`: separation of algorithmic groups from biological or scientific interpretation.
11. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, checks not run, and impact.
12. `FINDINGS`: blocking findings and non-blocking warnings with location, evidence, consequence, and minimum resolution; write `none` for empty categories.
13. `NEXT STEP`: the minimum correction, evidence acquisition, parameter revision, or authorization supported by the verdict.

Do not claim a grouping output is reliable or comparable to a prior result unless the supporting evidence was actually inspected.

## Allowed actions

- Read the algorithm code, configuration, input set, prior outputs, and diagnostic artifacts within scope.
- Run local read-only inspection commands and explicitly authorized safe validation commands.
- Inspect representative subsamples when full enumeration is infeasible, and report the sampling boundary.
- Propose threshold revisions, tie-breaking changes, diagnostic-artifact additions, or representative-selection rule changes without applying them unless separately authorized.

## Forbidden actions

- Modify algorithm code, parameters, or outputs during the audit.
- Treat a passing grouping run as proof of contract or scientific correctness.
- Conflate algorithmic groups with biological or scientific entities.
- Frame singletons or outliers as biological absence without independent evidence.
- Use labels that embed private machine paths, host names, run identifiers, or unrelated metadata.
- Expose private paths, restricted identifiers, or sensitive content in reports or commands.

## Verdict vocabulary
When composed under another primary skill, report this as a component status under that skill's findings, not as the task's top-level verdict.

- `GROUPING_AUDIT_READY`: Objective, inputs, thresholds, determinism, risk analysis, comparison, representative selection, diagnostics, labels, and interpretation-boundary elements satisfy the selected mode with no remaining warnings.
- `GROUPING_AUDIT_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking objective, threshold, determinism, comparison, representative, diagnostic, or interpretation findings prevent acceptance.
- `GROUPING_UNSAFE`: Nondeterminism, transitive merging, unmeasured sensitivity, lost IDs, or interpretation overclaim make the grouping unsafe for downstream consumption.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe inspection conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested audit, parameter change, or grouping component exceeds authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when the audit itself cannot proceed safely, `GROUPING_UNSAFE` for demonstrated unsafe behavior, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when the inspected evidence supports each contract element.
