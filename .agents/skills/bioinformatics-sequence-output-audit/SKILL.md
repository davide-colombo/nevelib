---
name: bioinformatics-sequence-output-audit
description: "Use when a FASTA, FASTQ, or alignment output feeds a downstream stage or deliverable; audit parseability, unique IDs, header contract, alphabet, gaps, coordinates, and strand."
license: "MIT"
---

# Bioinformatics Sequence Output Audit

## Purpose

Determine whether a sequence artifact is parseable under the declared format, has unique and contractual identifiers, uses a defined alphabet and gap/casing semantics, preserves length and orientation constraints, maintains identity through transformations, and supports source-to-output traceability. Detect malformed headers, ID collisions, metadata leakage in identifiers, alphabet violations, alignment-versus-unaligned drift, off-by-one extraction errors, lost strand information, duplicate sequences masquerading as distinct records, and broken provenance from source bytes to final output.

## Composition role

Default role: **module**. This skill contributes domain-specific checks and findings.

- **Can be primary when directly selected:** yes. When the task objective is specifically this domain, it owns the report and verdict.
- **Owns a report when composed:** no. Within a larger workflow it reports into the primary skill's schema as a labeled subsection or findings table and emits no second top-level verdict; its verdict becomes a component status that rolls up into the primary verdict.

## When to use

Use when a FASTA, FASTQ, aligned FASTA, multiple-sequence-alignment output, sequence extraction output, or sequence-classification review artifact will be consumed by a downstream stage, included in a deliverable, used for variant or grouping decisions, or compared against a prior version. Use alongside [`output-contract-and-table-schema-audit`](../output-contract-and-table-schema-audit/SKILL.md) when an accompanying table describes the sequences, and alongside [`manifest-checksum-and-provenance`](../manifest-checksum-and-provenance/SKILL.md) when a manifest describes the sequence set. When composed, one skill is the primary for the task and owns the report and top-level verdict; the others contribute their findings as labeled subsections and emit no second top-level verdict.

## When not to use

Do not use as authorization to modify sequences, re-emit headers, or republish artifacts. Do not substitute it for repository-state, code-review, environment, configuration, or domain validation. Do not use it to evaluate clustering or variant-grouping decisions; defer to [`classification-and-grouping-audit`](../classification-and-grouping-audit/SKILL.md). Do not use it to evaluate the scientific interpretation of sequences; defer to [`scientific-data-integrity-audit`](../scientific-data-integrity-audit/SKILL.md).

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- The sequence artifact under audit, its declared format, and its expected role.
- The producing component and its declared contract.
- The downstream consumer set and the assumptions each consumer makes.

If the artifact, format, producer, or consumer set cannot be established, stop and report. Do not infer format from extension.

## Optional inputs

Use when supplied or discoverable within scope:

- Source records or upstream extraction inputs.
- Reference identifiers used to extract or align sequences.
- Prior versions of the artifact for comparison.
- Schema or header convention documents.

Treat absent evidence as uncertainty, not as proof of correctness.

## Task modes

Choose exactly one mode and state it in the report:

- `SEQUENCE_FORMAT_AUDIT`: Inspect format parseability, header contract, alphabet, gaps, and casing.
- `SEQUENCE_IDENTITY_AUDIT`: Inspect unique IDs, ID preservation through transformations, and metadata-in-identifier hygiene.
- `EXTRACTION_OUTPUT_AUDIT`: Inspect coordinate-based extraction, flanking-sequence handling, and strand or orientation correctness.
- `ALIGNMENT_OUTPUT_AUDIT`: Inspect aligned-versus-unaligned expectations, gap usage, length agreement, and column-level invariants.
- `CLASSIFICATION_REVIEW_AUDIT`: Inspect sequence-classification or curation-review artifacts (grouping, labeling, representative selection) at the output level.
- `PROVENANCE_AUDIT`: Inspect source-to-output traceability of sequences through transformations.

A mode changes audit emphasis; it does not authorize file changes, re-emission, or publication.

## Parseability

Inspect that the artifact parses under the declared format:

- Confirm the declared format (FASTA, FASTQ, aligned FASTA, FASTQ-quality variant) is the actual format.
- Confirm record boundaries, line terminators, and encoding agree with the format.
- Confirm zero-length records, malformed quality lines, missing identifier lines, and stray content are absent.
- Confirm the number of records matches an independently enumerated count.

Do not declare an artifact parseable from a single sampled record. Enumerate.

## Unique sequence IDs

For each sequence:

- Confirm the identifier line begins with the format-appropriate prefix and contains the expected identifier substring.
- Confirm identifiers are unique across the artifact, with the project's normalization rule applied (case-sensitive or case-insensitive, whitespace policy).
- Detect duplicate identifiers, prefix collisions, and identifiers that differ only by trailing whitespace.
- Detect identifiers reused across runs or files when the consumer expects global uniqueness.

ID collisions silently corrupt joins, comparisons, and lookups. Record uniqueness explicitly.

## Header contract

Inspect the header beyond the identifier:

- Record the contractual fields beyond the identifier and their delimiter.
- Confirm consumers parse only the contractual fields and do not depend on header-internal whitespace, ordering, or formatting accidents.
- Confirm the producer does not embed nested or unrelated metadata in the header.

A header without an explicit contract becomes a hidden schema.

## No nested or unexpected metadata leakage

For each header:

- Detect embedded paths, machine names, internal run identifiers, raw configuration excerpts, or unrelated identifier fragments.
- Detect identifiers that include user names, host names, or environment-specific strings.
- Detect metadata that leaks restricted information into deliverables.

Headers that leak metadata exfiltrate information when the artifact is shared. Recommend redaction or restructure.

## Sequence alphabet

For each sequence:

- Confirm the alphabet matches the declared molecule (DNA, RNA, protein, ambiguous nucleotide, gap-aware variant).
- Detect characters outside the declared alphabet.
- Detect mixed-case usage when case is semantically meaningful (for example, soft-masking).
- Detect ambiguity codes (IUPAC) in records that should not contain them, or absence of ambiguity codes where they are required.

An alphabet violation either indicates corrupted upstream data or a header-versus-content mismatch.

## Gap characters when aligned output is expected

For aligned-output artifacts:

- Confirm gap characters use the contractual symbol (typically `-` or `.`).
- Confirm gap usage agrees across all records (same alphabet of gap symbols).
- Confirm aligned records have identical length.
- Detect leading or trailing gap-only columns that may indicate trimming inconsistencies.

For unaligned-output artifacts, confirm gap characters are absent.

## Aligned versus unaligned expectations

Confirm that the artifact's aligned or unaligned status matches the producer's declared mode and the consumer's expectation:

- An aligned artifact must have constant per-record length and a contractual gap symbol.
- An unaligned artifact must have variable per-record length and no gap symbol.
- Detect artifacts that contain a mix of aligned and unaligned records, which is unsafe by default.

## Sequence length constraints

For each sequence:

- Record minimum, maximum, and median length.
- Compare against the producer's contract (for example, "all sequences fall within `[L_min, L_max]`").
- Detect zero-length records, outlier-short and outlier-long records, and records whose length contradicts an extraction coordinate.

A length constraint that the consumer relies on must be honored by the producer.

## Casing semantics

When casing is meaningful in the artifact's format:

- Confirm uppercase, lowercase, or mixed case follows the project's convention (for example, lowercase for soft-masked bases, uppercase for confident bases).
- Detect case drift between producer and consumer.

When casing is not meaningful, confirm consumers do not depend on it.

## Reverse-complement handling

When sequences are extracted from a directional reference:

- Confirm strand or orientation per record matches the declared rule.
- Confirm reverse-complement transformations were applied consistently and only when the rule requires them.
- Detect records that retain forward-strand sequence when reverse-strand was required, or vice versa.

A silent strand flip corrupts every downstream sequence comparison.

## Coordinate extraction

For extraction outputs:

- Confirm extracted sequence corresponds to the declared interval on the reference.
- Confirm zero-based versus one-based and inclusive-versus-half-open conventions match the upstream contract and downstream consumer.
- Detect off-by-one at start, end, or both.
- Detect interval boundaries that exceed the reference length.

Cross-reference [`output-contract-and-table-schema-audit`](../output-contract-and-table-schema-audit/SKILL.md) when the coordinates are also recorded in a table.

## Flanking sequence extraction

When the artifact includes flanking regions:

- Confirm flank length on each side matches the declared rule.
- Confirm flanks are extracted from the same reference as the core sequence.
- Confirm flanks respect reference boundaries (truncated rather than wrapped at chromosome ends).
- Confirm the consumer knows where the core sequence begins and ends inside the extracted record.

A flanking artifact whose core boundary is implicit is a coordinate accident waiting to happen.

## Strand and orientation conventions

For directional artifacts:

- Record the strand convention used by the producer.
- Confirm consumer parsers agree.
- Detect implicit conventions ("all sequences are forward strand") that are not declared anywhere.

## Grouping and variant labels

When the artifact carries grouping, variant, or cluster labels in headers, sidecars, or accompanying tables:

- Confirm labels are unique within the declared scope.
- Confirm labels are stable across reruns under the same input.
- Confirm consumers map labels back to the producing algorithm under [`classification-and-grouping-audit`](../classification-and-grouping-audit/SKILL.md).

## Duplicate sequence handling

For each artifact:

- Identify duplicate sequences (identical content under the declared canonicalization rule).
- Identify near-duplicate sequences when the producer's contract requires deduplication at a tolerance.
- Confirm the producer's duplicate policy (collapse, keep all, keep representative) matches the consumer's expectation.

Duplicate sequences masquerading as distinct records inflate downstream counts.

## ID preservation across transformations

When the artifact is the result of one or more transformations:

- Confirm IDs are preserved through extraction, filtering, alignment, grouping, and reformatting.
- Detect transformations that rewrite IDs without recording a mapping.
- Detect transformations that drop IDs and re-emit synthetic identifiers without traceable mapping.

Lost IDs break source-to-output traceability and corrupt any downstream join.

## Source-to-output traceability

For each sequence:

- Trace identity back to the source record (read identifier, sample identifier, source database accession).
- Confirm intermediate transformations are recorded in the manifest, header, or sidecar.
- Detect chains that cannot be inspected from current artifacts.

Cross-reference [`manifest-checksum-and-provenance`](../manifest-checksum-and-provenance/SKILL.md) when manifests cover the chain.

## Representative sequence selection

When the artifact carries representative-sequence selections for clusters or groups:

- Confirm the representative-selection rule (longest, highest-quality, centroid, first observed).
- Confirm the rule is applied consistently across groups.
- Confirm the representative's identifier is traceable to the original record.

A representative selection without a recorded rule cannot be reproduced or reviewed.

## Audit procedure

1. Restate the objective, selected task mode, scope, artifact identity, and producer/consumer set.
2. Confirm parseability and enumerate record counts.
3. Inspect unique IDs and header contract.
4. Inspect alphabet, gap, casing, and aligned-versus-unaligned status.
5. Inspect length constraints and detect outliers.
6. Inspect strand/orientation, coordinate extraction, and flanking-sequence rules.
7. Inspect grouping/variant labels and duplicate handling.
8. Inspect ID preservation through transformations.
9. Inspect source-to-output traceability.
10. Inspect representative-sequence selection when applicable.
11. Classify findings, record commands actually run and evidence unavailable, and select exactly one verdict.

Do not treat a single passing parse on one record as proof of artifact-wide correctness.

## Stop-and-report triggers

Stop before downstream use, republication, or sharing when:

- The declared format does not match the actual format.
- Sequence IDs are not unique under the declared normalization rule.
- Headers leak unrelated or restricted metadata.
- Alphabet, gap, casing, or aligned-versus-unaligned status violates the contract.
- Coordinate extraction or flanking rules are inconsistent with upstream conventions.
- Strand or orientation is implicit and material to the consumer.
- Duplicates are present when the contract requires deduplication.
- IDs are lost in a transformation without a recorded mapping.
- Source-to-output traceability is broken.
- A representative-selection rule cannot be inspected.
- Required evidence cannot be inspected and the gap prevents a reliable verdict.

Report the trigger, affected records, evidence, and minimum decision or authorization required.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `MODE AND SCOPE`: selected task mode, artifact identity, producer, consumer set, allowed scope, and exclusions.
3. `FORMAT AND PARSEABILITY`: declared format, record count, line terminator, encoding, and parseability evidence.
4. `IDENTIFIER CONTRACT`: uniqueness, header contract, and metadata-leakage findings.
5. `ALPHABET, GAPS, CASING, AND ALIGNMENT`: per-format adherence and aligned-versus-unaligned consistency.
6. `LENGTHS AND COORDINATES`: length distribution, coordinate convention, extraction correctness, and flanking-sequence rules.
7. `STRAND AND ORIENTATION`: convention used, agreement across consumers, and reverse-complement evidence.
8. `GROUPING, DUPLICATES, AND ID PRESERVATION`: label uniqueness, duplicate policy, and ID preservation through transformations.
9. `SOURCE-TO-OUTPUT TRACEABILITY`: per-record provenance evidence.
10. `REPRESENTATIVE SELECTION`: rule, application, and traceability when applicable; write `none` otherwise.
11. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, checks not run, and impact.
12. `FINDINGS`: blocking findings and non-blocking warnings with location, evidence, consequence, and minimum resolution; write `none` for empty categories.
13. `NEXT STEP`: the minimum correction, evidence acquisition, or authorization supported by the verdict.

Do not claim sequence-artifact properties were validated unless the supporting evidence was actually inspected.

## Allowed actions

- Read the artifact, accompanying manifests, headers, sidecars, and producer code within scope.
- Run local read-only inspection commands (record counts, alphabet checks, length distributions, header parses) when explicitly safe and authorized.
- Inspect representative subsamples when artifact-wide enumeration is infeasible, and report the sampling boundary.
- Propose corrections without applying them unless separately authorized.

## Forbidden actions

- Modify sequences, headers, or accompanying records during the audit.
- Treat a single sampled record as artifact-wide evidence.
- Assume tool defaults for format, alphabet, gap symbol, or coordinate convention.
- Hardcode private project names, private population names, or private current results into the audit.
- Expose private paths, restricted identifiers, or sensitive content in reports or commands.

## Verdict vocabulary
When composed under another primary skill, report this as a component status under that skill's findings, not as the task's top-level verdict.

- `SEQUENCE_OUTPUT_READY`: Format, identifiers, header contract, alphabet, gaps, casing, alignment status, lengths, coordinates, strand, grouping, duplicates, ID preservation, traceability, and representative selection satisfy the selected mode with no remaining warnings.
- `SEQUENCE_OUTPUT_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking format, identifier, alphabet, coordinate, strand, duplicate, ID, or provenance findings prevent acceptance.
- `SEQUENCE_OUTPUT_UNSAFE`: Identifier collisions, metadata leakage, strand or coordinate drift, alphabet violations, or broken provenance make the artifact unsafe for downstream use.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe inspection conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested audit, artifact change, or sequence component exceeds authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when the audit itself cannot proceed safely, `SEQUENCE_OUTPUT_UNSAFE` for demonstrated unsafe content, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when the inspected evidence supports each contract element.
