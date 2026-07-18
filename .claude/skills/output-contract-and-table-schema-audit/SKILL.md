---
name: output-contract-and-table-schema-audit
description: "Use when a TSV, CSV, or table output must match a schema its producer and consumers share; audit delimiter, encoding, headers, columns, row identity, sorting, and units."
license: "MIT"
---

# Output Contract and Table Schema Audit

## Purpose

Determine whether a generated tabular output and its declared schema contract are mutually consistent, inspectable, and stable enough for downstream consumers to rely on. Detect undeclared columns, ambiguous units or coordinate conventions, inconsistent missing-value handling, unstable sort order, duplicate-row policy gaps, controlled-vocabulary drift, precision loss, and the absence of regression coverage for schema changes.

## Composition role

Default role: **module**. This skill contributes domain-specific checks and findings.

- **Can be primary when directly selected:** yes. When the task objective is specifically this domain, it owns the report and verdict.
- **Owns a report when composed:** no. Within a larger workflow it reports into the primary skill's schema as a labeled subsection or findings table and emits no second top-level verdict; its verdict becomes a component status that rolls up into the primary verdict.

## When to use

Use when designing or changing a tabular output contract, accepting a new table consumer, integrating two stages that exchange tables, diagnosing a downstream parse or interpretation failure, validating produced tables against a declared schema, or auditing whether a schema-change has the regression tests it needs. Use alongside [`pipeline-stage-contract-audit`](../pipeline-stage-contract-audit/SKILL.md) when the table is produced by a specific stage.

## When not to use

Do not use as authorization to modify tables, change schemas, or republish outputs. Do not substitute it for repository-state, code-review, configuration, data-transfer, or domain validation. For Excel workbook integrity (sheets, styles, formulas, data validation), use [`excel-workbook-integrity`](../excel-workbook-integrity/SKILL.md). For sequence-output formats (FASTA, FASTQ, alignment), use [`bioinformatics-sequence-output-audit`](../bioinformatics-sequence-output-audit/SKILL.md). For manifests and provenance, use [`manifest-checksum-and-provenance`](../manifest-checksum-and-provenance/SKILL.md).

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- The identity of the producing component and the identity of each downstream consumer of the table.
- The declared or proposed schema contract: format, delimiter, encoding, headers, columns, row identity, sort order, units, coordinate conventions, missing-value conventions, duplicate policy, controlled vocabularies, and numeric precision.
- Representative produced table or tables when available.

If the producing component, consumer set, or declared schema cannot be established, stop and report. Do not infer the schema from a single example table.

## Optional inputs

Use when supplied or discoverable within scope:

- Schema definitions in code or external schema files.
- Existing schema-change tests, validators, or readers.
- Prior incident records relating to format, header, encoding, or coordinate disagreement.
- Sample input artifacts and expected outputs for valid-empty cases.

Treat absent evidence as uncertainty, not as proof of schema correctness.

## Task modes

Choose exactly one mode and state it in the report:

- `SCHEMA_DESIGN_REVIEW`: Evaluate a proposed table schema before implementation.
- `SCHEMA_AUDIT`: Inspect an implemented schema against code, configuration, and representative produced tables.
- `PRODUCED_TABLE_AUDIT`: Compare a specific produced table against the declared schema contract.
- `SCHEMA_CHANGE_AUDIT`: Evaluate a proposed schema change against existing consumers, regression coverage, and backward-compatibility policy.
- `CONSUMER_PARITY_AUDIT`: Confirm that the producer's declared schema and each consumer's parsing assumptions are mutually consistent.

A mode changes audit emphasis; it does not authorize file changes, republication, or schema-policy changes.

## File-format contract

Specify and verify:

- `file format`: TSV, CSV, Parquet, JSONL, Excel-derived TSV, or other. State the format explicitly; do not infer it from extension.
- `delimiter`: tab, comma, semicolon, pipe, or other. State the exact character and whether it may appear quoted inside fields.
- `quoting rule`: when fields may contain the delimiter, line terminator, or quote character, and how those are escaped.
- `line terminator`: LF, CRLF, or platform-dependent.
- `encoding`: UTF-8, UTF-8 with BOM, Latin-1, or other. State the byte representation.
- `compression`: none, gzip, bgzip, or other. State whether the format is wrapped.
- `file-name rule`: the deterministic mapping from unit of work to file path or name.

A producer that writes Latin-1 while consumers parse UTF-8 corrupts non-ASCII content silently. Record encoding explicitly.

## Header and column contract

For each table, specify:

- `header presence`: whether the first row contains column names. State explicitly; do not rely on convention.
- `column names`: the exact names, case-sensitive, including any whitespace or punctuation.
- `column order`: whether order is contractual or whether consumers must look up by name.
- `column types`: the type of each column and the representation used (for example, integer as decimal digits, float with explicit precision, boolean as `true`/`false` or `0`/`1`, date as ISO 8601).
- `required versus optional columns`: which columns must always appear and which may be omitted.
- `unknown-column policy`: whether additional columns are tolerated, ignored, or rejected by consumers.

A schema that allows reordering must state it explicitly. A schema that fixes order must declare it.

## Row granularity and identity

Specify:

- `row granularity`: what one row represents (one sample, one observation, one record per pair, one record per interval).
- `primary key`: the column or column combination that uniquely identifies a row.
- `composite key rules`: how multi-column keys are constructed and compared.
- `row-identity stability`: whether the same logical record retains the same key across reruns.

A table without an explicit row-identity contract cannot be safely merged, joined, or deduplicated.

## Stable sorting

Specify:

- Whether the table has a contractual sort order.
- The sort keys, sort direction, and tie-breaking rules.
- Whether the sort is required for downstream correctness or only for human inspection.
- Whether the sort is deterministic under reruns with identical inputs.

A table whose sort order is incidental cannot be safely diffed across runs. Record this and report it.

## Units, coordinates, and intervals

Specify:

- `units`: the unit of every numeric column (for example, base pairs, kilobases, reads, counts per million, percent).
- `coordinate convention`: where applicable, whether positions are zero-based or one-based.
- `interval convention`: where applicable, whether intervals are inclusive on both ends, half-open (start inclusive, end exclusive), or another convention.
- `strand or orientation`: where applicable, whether forward/reverse is encoded in the row and how.

Coordinate-convention drift between producer and consumer corrupts every downstream calculation. Record convention explicitly and audit consumer parsers against the same convention.

## Missing-value conventions

Specify:

- The exact representation of a missing value: empty cell, literal `NA`, `NaN`, `null`, `.`, `-`, or another.
- Whether different missing-value tokens carry different meanings (for example, `NA` for not measured versus `0` for measured-and-zero).
- The behavior of consumers when they encounter the missing-value token.
- Whether a missing required field is permitted at all.

Inconsistent missing-value representation is a frequent silent corruption source. Record the contract and audit it.

## Valid-empty table semantics

Specify what a valid-empty result looks like:

- A header-only file with zero data rows.
- An absent file as a meaningful valid-empty signal.
- A sentinel file alongside an absent table.
- Another agreed representation.

The valid-empty representation must be distinguishable from a missing or corrupted table. Without this distinction, downstream consumers cannot decide whether to wait, fail, or proceed.

## Duplicate handling

Specify:

- Whether duplicate rows by primary key are permitted, forbidden, or merged.
- The deduplication rule, if any, including which copy is retained when keys collide.
- Whether the producer guarantees deduplication or whether consumers must perform it.

A table that silently allows duplicates breaks join semantics downstream. Record the policy.

## Controlled vocabulary columns

For columns whose values come from a controlled vocabulary, specify:

- The authoritative source of the vocabulary (an enumeration, an external ontology, a project-local list).
- Whether unknown values are rejected, accepted, or coerced.
- Versioning of the vocabulary and how schema changes are surfaced to consumers.
- Case sensitivity and whitespace handling.

A controlled-vocabulary column whose source can drift without notice will eventually produce silent classification errors. Record the source and audit the producer against it.

## Numeric precision and rounding

Specify:

- The required precision of each numeric column.
- The rounding rule (half-to-even, half-away-from-zero, truncation, or other).
- Whether precision is contractual or advisory.
- Whether floating-point representation is deterministic across platforms.

A consumer that expects fixed decimal precision cannot safely consume a producer that writes platform-default `repr`. Record the contract and audit both ends.

## Downstream consumers

For each downstream consumer:

- Identify which columns it reads.
- Identify any schema assumptions not declared by the producer (for example, expected sort order, specific missing-value token, specific encoding).
- Identify behavior under unknown columns, unknown vocabulary values, missing-value tokens, and valid-empty tables.

Undeclared consumer assumptions are part of the effective schema. Record them and report whether the producer guarantees the assumed property.

## Schema-change tests

For each declared schema element, identify whether a regression test exists that would fail when:

- A required column is renamed or removed.
- Column order changes when order is contractual.
- The delimiter, encoding, or line terminator changes.
- The missing-value token changes.
- The coordinate or interval convention changes.
- The controlled vocabulary loses a value or accepts an unknown value.
- Numeric precision changes.
- The valid-empty representation changes.

A schema without regression coverage is a schema that will drift silently. Record the gaps as findings in this audit's report and hand them to [`test-fixture-and-regression-design`](../test-fixture-and-regression-design/SKILL.md) as a separate later design phase; do not produce that skill's report here.

## Audit procedure

1. Restate the objective, selected task mode, scope, producing component, and consumer set.
2. Inspect the file-format contract against producer code, sample files, and consumer parsers.
3. Inspect header presence, column names, column order, types, and required-versus-optional status against producer code and representative tables.
4. Inspect row granularity, primary key, and identity stability against the producer's record-emission logic and the consumer's join logic.
5. Inspect sort order, sort keys, and tie-breaking against the producer's sort step and representative tables.
6. Inspect units, coordinate conventions, and interval conventions against the producer's emission code and the consumer's parsing code.
7. Inspect missing-value tokens against producer emission and consumer parsing.
8. Inspect valid-empty table semantics against the producer's empty-case path and the consumer's handling.
9. Inspect duplicate handling against the producer's deduplication step and downstream join correctness.
10. Inspect controlled-vocabulary columns against the authoritative vocabulary source and producer/consumer validation.
11. Inspect numeric precision and rounding against producer formatting and consumer parsing.
12. Inspect schema-change tests against each contract element.
13. Classify findings, record commands actually run and evidence unavailable, and select exactly one verdict.

Do not treat a single passing parse on one example table as proof of schema compliance.

## Stop-and-report triggers

Stop before republication, schema change, or downstream use when:

- Producer and consumer disagree on format, encoding, delimiter, or quoting.
- Column names, order, or required-versus-optional status are ambiguous.
- Row identity cannot be determined or duplicates can silently accumulate.
- Units, coordinate conventions, or interval conventions are implicit and material to downstream calculation.
- Missing-value tokens are inconsistent between producer and consumer.
- The valid-empty representation cannot be distinguished from missing or corrupted output.
- Controlled-vocabulary source is undeclared or can drift silently.
- Numeric precision is contractual but rounding behavior is undeclared.
- Schema-change regression tests are absent for material contract elements.
- Required evidence cannot be inspected and the gap prevents a reliable verdict.

Report the trigger, affected contract element, evidence, and minimum decision or authorization required.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `MODE AND SCOPE`: selected task mode, producing component, consumer set, allowed scope, and exclusions.
3. `FILE FORMAT CONTRACT`: format, delimiter, quoting, encoding, line terminator, compression, and file-name rule.
4. `HEADER AND COLUMN CONTRACT`: header presence, column names, order policy, types, required-versus-optional status, and unknown-column policy.
5. `ROW IDENTITY AND SORT`: row granularity, primary key, identity stability, sort keys, and tie-breaking.
6. `UNITS, COORDINATES, AND MISSING VALUES`: units, coordinate and interval convention, strand or orientation when relevant, and missing-value representation.
7. `VALID-EMPTY AND DUPLICATE POLICY`: valid-empty semantics and duplicate handling.
8. `CONTROLLED VOCABULARY AND PRECISION`: vocabulary source and versioning, and numeric precision and rounding.
9. `CONSUMER PARITY`: each consumer, assumed contract elements, and whether the producer guarantees them.
10. `SCHEMA-CHANGE TESTS`: presence or absence of regression coverage per contract element and the impact of gaps.
11. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, checks not run, and impact.
12. `FINDINGS`: blocking findings and non-blocking warnings with location, evidence, consequence, and minimum resolution; write `none` for empty categories.
13. `NEXT STEP`: the minimum design correction, implementation action, validation, or authorization supported by the verdict.

## Allowed actions

- Read producer code, consumer code, schema definitions, sample tables, and prior incident records within scope.
- Run local read-only inspection commands such as schema parsers, file-listing, and byte-level inspection when explicitly safe and authorized.
- Propose schema corrections, regression-test additions, or consumer-parity fixes without applying them unless separately authorized.

## Forbidden actions

- Modify producer code, consumer code, or schema files during an audit.
- Republish or overwrite produced tables to make them match the declared schema.
- Treat a single example table as proof of schema compliance.
- Assume tool defaults (delimiter, encoding, line terminator) without inspection.
- Claim schema-change tests exist without naming them.
- Expose private paths, restricted identifiers, or sensitive content in reports or commands.

## Verdict vocabulary
When composed under another primary skill, report this as a component status under that skill's findings, not as the task's top-level verdict.

- `TABLE_SCHEMA_CONTRACT_READY`: The format, header, column, row-identity, sort, unit/coordinate, missing-value, valid-empty, duplicate, controlled-vocabulary, precision, consumer-parity, and schema-change-test elements satisfy the selected mode with no remaining warnings.
- `TABLE_SCHEMA_CONTRACT_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking schema findings prevent acceptance.
- `SCHEMA_AMBIGUOUS`: One or more contract elements are implicit and the gap materially affects producer/consumer parity or schema-change safety.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe inspection conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested audit, schema change, or table component exceeds authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when the audit itself cannot proceed safely, `SCHEMA_AMBIGUOUS` for demonstrated implicit-contract risk, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when contract elements are explicit and supported by inspected evidence.
