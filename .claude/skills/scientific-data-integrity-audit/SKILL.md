---
name: scientific-data-integrity-audit
description: "Use when a scientific artifact's claims rest on biological or analytical reasoning; audit interpretation, tell absence from missing data, and separate facts from assumptions."
license: "MIT"
---

# Scientific Data Integrity Audit

## Purpose

Determine whether a generated scientific artifact's claims are supported by the data, the metadata, and the analytical assumptions actually applied. Audit interpretation, not only computation. Detect biological or scientific absence misclassified as computational failure, broken metadata propagation, undocumented filtering or clustering assumptions, coordinate-convention drift, strand or orientation drift, reference-build inconsistency, unit drift, unjustified thresholds, missing-evidence misrepresented as negative evidence, and claim language that exceeds what the data support.

## Composition role

Default role: **primary**. This skill owns the task objective, the top-level verdict vocabulary, and the final report, and integrates module and modifier findings.

- **Can be primary when directly selected:** yes.
- **Owns a report when composed:** it owns the report when it is the selected primary for the task phase. When it instead contributes to another primary skill, it provides its findings block without a second top-level verdict.

## When to use

Use when a report, table, sequence set, or other artifact makes claims that downstream scientific decisions will rely on. Use before a result is shared with collaborators, included in a manuscript draft, included in a deliverable, or used as input to a follow-up analysis. Use alongside [`evidence-citation-discipline`](../evidence-citation-discipline/SKILL.md) when claim-level citation must be enforced, and alongside [`agent-output-verification-and-claim-audit`](../agent-output-verification-and-claim-audit/SKILL.md) when an agent's narrative report is the claim source. When composed, one skill is the primary for the task and owns the report and top-level verdict; the others contribute their findings as labeled subsections and emit no second top-level verdict.

## When not to use

Do not use as authorization to publish, share, deliver, or act on scientific claims. Do not substitute it for domain expert review, statistical methodology review, or peer review. Do not use it to evaluate file-format or schema details; defer to [`output-contract-and-table-schema-audit`](../output-contract-and-table-schema-audit/SKILL.md) or [`bioinformatics-sequence-output-audit`](../bioinformatics-sequence-output-audit/SKILL.md). Do not use it to evaluate clustering or grouping algorithm parameters in isolation; defer to [`classification-and-grouping-audit`](../classification-and-grouping-audit/SKILL.md).

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- The artifact under audit and the claims it supports.
- The data sources, intermediate artifacts, and analytical procedures applicable to the claims.
- The identity of the receiver who will rely on the claims.

If the artifact, claims, data sources, or receiver cannot be established, stop and report. Do not infer scientific claims from filename or convention.

## Optional inputs

Use when supplied or discoverable within scope:

- Reference data identifiers (build, accession, version) and the procedure that bound the analysis to them.
- Metadata records that connect samples or specimens to records in the artifact.
- Threshold rationale documents, prior calibration, or sensitivity analyses.
- Existing methods sections, protocol records, or operator notes.

Treat absent evidence as uncertainty, not as proof that interpretation is sound.

## Task modes

Choose exactly one mode and state it in the report:

- `INTERPRETATION_AUDIT`: Inspect each claim in an artifact and classify whether it is supported, partially supported, or unsupported by the data and assumptions.
- `METADATA_PROPAGATION_AUDIT`: Inspect whether sample, specimen, reference, or run metadata is preserved end-to-end and used consistently.
- `THRESHOLD_AND_ASSUMPTION_AUDIT`: Inspect filtering, clustering, projection, classification, and threshold choices and their stated rationale.
- `NEGATIVE_EVIDENCE_AUDIT`: Inspect claims of absence and distinguish biological or scientific absence from computational failure or missing measurement.
- `CLAIM_LANGUAGE_AUDIT`: Inspect the wording of the artifact's claims and recommend wording that does not exceed evidence.

A mode changes audit emphasis; it does not authorize file changes, republication, or claim release.

## Biological or scientific absence versus computational failure

For every claim of absence, determine which condition holds:

- The measurement was attempted and returned a meaningful zero.
- The measurement was attempted and returned no signal (sensitivity-limited absence).
- The measurement was not attempted in the relevant sample or region.
- The measurement was attempted but failed computationally (corrupted input, parser error, crashed step).
- The measurement was attempted but suppressed by a filter whose threshold was not stated.

A claim of biological absence requires the first or second condition with a stated sensitivity bound. Computational failure or missing measurement is not biological absence.

## Source specimen, sample, population, or reference identity

For every claim that depends on a specific sample, specimen, population, or reference:

- Confirm the identifier used in the artifact matches the authoritative record.
- Confirm the version or accession (where applicable) is recorded and stable.
- Confirm cross-references between artifacts agree (sample identifiers, sequencing library identifiers, alignment references, annotation versions).
- Detect mismatched identifiers, undated identifiers, or identifiers that point to mutable sources.

Identifier drift produces silent misattribution of results. Record it explicitly.

## Metadata propagation

For each metadata field the claims rely on:

- Trace the field from raw source to the final artifact.
- Confirm intermediate steps preserve the field, do not silently rename it, do not drop rows that should retain it, and do not merge it with unrelated fields.
- Confirm the receiver of the artifact can map the metadata back to the source.

A claim that depends on metadata broken upstream is unsupported.

## Filtering assumptions

For every filter applied to data before the claim is made:

- Record the filter criterion, the threshold, the value field, and the unit.
- Record the rationale for the threshold and the evidence that supports it.
- Record whether the filter was applied before or after the claim was formed.
- Detect filters that select for the conclusion (post-hoc filtering aligned to the desired result).

Filters that lack rationale or that are post-hoc to the conclusion produce findings that depend on the analyst's choices rather than on the data.

## Clustering, projection, and classification assumptions

For every clustering, projection, or classification step the claim depends on:

- Record the algorithm, parameters, random seed, and version.
- Record the distance, similarity, identity, or coverage measure and its scope.
- Record the rule used to assign labels and how ties are broken.
- Detect dependence on default parameters that have not been justified.
- Detect inconsistent reuse of clusters or labels across runs.

Defer detailed algorithmic audit to [`classification-and-grouping-audit`](../classification-and-grouping-audit/SKILL.md) when the claim hinges on grouping behavior.

## Coordinate conventions

For every claim that involves positions, intervals, or alignments:

- Confirm zero-based versus one-based convention is consistent across producer, intermediate steps, and consumer.
- Confirm inclusive versus half-open interval convention is consistent.
- Confirm conversions between conventions, where applied, are documented and audited.

Coordinate drift across a single chain of steps corrupts every position-based conclusion downstream.

## Strand or orientation semantics

For every claim that involves directional data:

- Confirm strand or orientation is recorded explicitly per record.
- Confirm reverse-complement, reversal, or reorientation operations are documented and applied consistently.
- Detect claims that treat one direction as canonical without recording the convention.

## Reference build or accession consistency

For every claim bound to a reference (genome build, transcript set, ontology version, database release):

- Confirm the reference identifier and version are recorded.
- Confirm intermediate steps used the same reference.
- Detect cross-step disagreements such as alignment to one build and annotation against another.

A claim that crosses references without explicit lift-over or remapping evidence is unsupported.

## Unit consistency

For every numeric quantity the claim depends on:

- Confirm the unit is stated and consistent across producer and consumer.
- Detect implicit unit conversions, mixed units in aggregations, or summary statistics with no unit.
- Confirm aggregation rules respect units that cannot be summed directly (rates, ratios, log-scale values).

## Threshold rationale

For every threshold the claim depends on:

- Record the chosen value, the comparison direction, and the value field.
- Record the rationale (calibration, prior literature, domain practice, sensitivity analysis).
- Record sensitivity to threshold change.
- Detect thresholds whose only rationale is "this is what produced the desired result".

A threshold without rationale is an assumption masquerading as evidence.

## Negative evidence versus missing evidence

For every claim of "not present", "not detected", or "not observed":

- Confirm the measurement or analysis was actually applied to the relevant input.
- Confirm the sensitivity bound is stated.
- Distinguish biological absence from missing measurement, filtered-out signal, or failed step.

A claim of negative evidence without a sensitivity bound is missing evidence dressed as a finding.

## Provenance from raw to final

For each claim, trace the provenance from raw or intermediate inputs to the final artifact:

- Record each transformation step, its tool and version, and its parameters.
- Confirm intermediate artifacts referenced by the chain still exist or can be reconstructed.
- Detect broken chains where an intermediate step's outputs are no longer available.

A claim whose provenance chain cannot be reconstructed is not reproducible. Cross-reference [`manifest-checksum-and-provenance`](../manifest-checksum-and-provenance/SKILL.md) when manifests are part of the chain.

## Claims that overstate what the data support

Inspect wording for overclaim patterns:

- "Confirmed", "validated", "demonstrated", or "established" when only partial evidence is present.
- "All" or "every" when only the in-scope subset was examined.
- "Novel", "first", or "previously unreported" without literature comparison.
- "Negative" or "absent" without a sensitivity bound.
- "Significant" without a stated statistical test, threshold, or effect size.
- "Reproducible" without an explicit reproduction.

Recommend wording that distinguishes confirmed facts, partial evidence, interpretations, and assumptions.

## Confirmed facts, interpretations, assumptions, and unresolved items

For each claim, assign exactly one classification:

- `confirmed fact`: Supported by directly inspectable evidence; reproduction would yield the same result.
- `interpretation`: A reading of evidence that depends on a stated model, assumption, or domain judgment.
- `assumption`: A statement accepted without inspection because it is required to proceed; must be stated as such.
- `unresolved item`: A statement whose support cannot be established from current evidence; must be marked open and not asserted as fact.

Report classifications explicitly. A claim's strongest acceptable classification governs the wording the artifact may use.

## Audit procedure

1. Restate the objective, selected task mode, scope, artifact, claims, and receiver.
2. Enumerate every claim the artifact makes that a downstream decision will rely on.
3. For each claim, identify the data sources, intermediate artifacts, metadata fields, references, units, coordinates, and thresholds it depends on.
4. Inspect biological-absence versus computational-failure framing for absence claims.
5. Inspect metadata propagation, identifier integrity, and reference-build consistency.
6. Inspect filtering, clustering, projection, classification, and threshold assumptions and their rationale.
7. Inspect coordinate, interval, strand or orientation, and unit consistency.
8. Inspect negative-evidence claims for stated sensitivity bounds.
9. Inspect provenance chains for each claim.
10. Inspect claim language for overclaim patterns and recommend wording corrections.
11. Classify every claim as confirmed fact, interpretation, assumption, or unresolved item.
12. Classify findings, record commands actually run and evidence unavailable, and select exactly one verdict.

Do not treat a passing pipeline run as proof that the scientific interpretation is sound.

## Stop-and-report triggers

Stop before publication, sharing, or downstream decision when:

- Claims and their data sources cannot be paired.
- Metadata propagation is broken for a field the claim depends on.
- Identifier, reference build, or accession drift affects a claim.
- A filter, clustering parameter, or threshold lacks rationale and materially affects the claim.
- A coordinate, interval, strand, orientation, or unit convention is inconsistent across the chain.
- A negative-evidence claim lacks a sensitivity bound.
- A provenance chain is broken or unreproducible.
- Claim wording overclaims beyond what the audit can support.
- Required evidence cannot be inspected and the gap prevents a reliable verdict.

Report the trigger, affected claim, evidence, and minimum decision or authorization required.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `MODE AND SCOPE`: selected task mode, artifact identity, claims under audit, receiver, allowed scope, and exclusions.
3. `IDENTIFIER AND REFERENCE INTEGRITY`: sample, specimen, population, and reference identifier evidence and consistency across steps.
4. `METADATA PROPAGATION`: each metadata field the claims depend on, traced from raw to final.
5. `FILTERING, CLUSTERING, AND THRESHOLDS`: each assumption, parameter, and threshold with rationale and evidence.
6. `COORDINATES, STRAND, AND UNITS`: convention agreement across producer, intermediate steps, and consumer.
7. `NEGATIVE EVIDENCE`: absence claims with sensitivity bounds and distinguished from missing measurement.
8. `PROVENANCE CHAINS`: per-claim chain from raw input to final artifact.
9. `CLAIM LANGUAGE`: exact wording inspected, overclaim findings, and recommended corrections.
10. `CLAIM CLASSIFICATION`: confirmed facts, interpretations, assumptions, and unresolved items.
11. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, checks not run, and impact.
12. `FINDINGS`: blocking findings and non-blocking warnings with location, evidence, consequence, and minimum resolution; write `none` for empty categories.
13. `NEXT STEP`: the minimum claim correction, evidence acquisition, methodology change, or authorization supported by the verdict.

Do not claim scientific interpretation was validated unless the supporting evidence was actually inspected.

## Allowed actions

- Read the artifact, intermediate evidence, methods records, configuration, logs, and external records within scope.
- Run local read-only inspection and explicitly authorized safe validation commands.
- Trace claims, classify evidence, and recommend wording corrections.
- Propose methodology, threshold, or wording corrections without applying them unless separately authorized.

## Forbidden actions

- Modify the artifact, methods, or claim language during the audit.
- Treat a passing pipeline run as scientific validation.
- Claim "validated", "confirmed", or "reproducible" when supporting evidence is partial.
- Treat the absence of evidence as evidence of absence without a stated sensitivity bound.
- Hardcode private project names, private datasets, private populations, or unpublished current results into the audit output.
- Expose private paths, restricted identifiers, or sensitive content in reports or commands.

## Verdict vocabulary
This skill owns the top-level verdict for the task phase. When it instead contributes to another primary, report its status as a component finding.

- `SCIENTIFIC_INTEGRITY_READY`: Identifier, metadata, threshold, coordinate, negative-evidence, provenance, and claim-language elements satisfy the selected mode with no remaining warnings.
- `SCIENTIFIC_INTEGRITY_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking interpretation, propagation, threshold, or wording findings prevent acceptance.
- `INTERPRETATION_UNSAFE`: A claim materially exceeds evidence, a convention drift corrupts conclusions, or negative-evidence claims lack sensitivity bounds.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe inspection conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested audit, claim revision, or artifact component exceeds authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when the audit itself cannot proceed safely, `INTERPRETATION_UNSAFE` for demonstrated overclaim or convention drift, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when claim-level evidence is explicit and inspected.
