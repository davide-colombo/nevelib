---
name: evidence-citation-discipline
description: "Use when writing a coding-agent report another actor will act on; bind each consequential claim to inspectable evidence and separate facts from interpretation and assumptions."
license: "MIT"
---

# Evidence Citation Discipline

## Purpose

Produce reports whose claims can be checked against the artifacts that justify them. Make the auditor's job possible by attaching inspectable evidence to each consequential statement, by separating confirmed observations from interpretation and assumption, and by refusing to assert what the evidence does not support. Treat the discipline as the writer-side complement of `agent-output-verification-and-claim-audit`.

## Composition role

Default role: **modifier**. This skill governs how any report classifies claims, binds them to evidence, words uncertainty, and records unresolved state. It does **not** impose a report layout of its own.

- **Can be primary when directly selected:** no. It shapes another skill's report rather than owning a task objective or verdict.
- **Owns a report when composed:** no. The primary skill owns the report structure and the top-level verdict. This skill contributes required claim classes (`FACT`, `INTERPRETATION`, `ASSUMPTION`, `UNRESOLVED`), evidence bindings, and an evidence appendix as content within that report, in whatever section order the primary skill defines.

Use this skill when writing any report that another actor will rely on for a decision, including:

- Implementation reports after adding, changing, or removing code or configuration.
- Audit reports after inspecting a repository, a commit, a patch, or a generated output.
- Review reports after evaluating code, tests, or documentation.
- Validation reports after running tests, validators, linters, or builds.
- Operational reports after launching, monitoring, or intervening in a long-running job.
- Handoff reports passing work to another session, agent, or human.
- Integration, merge, push, and release reports.

The same discipline applies to short conversational replies that carry consequential claims.

## Evidence model

Evidence is an inspectable artifact a reader can examine without trusting the writer. Accepted evidence types and the minimum form each must take:

- Exact command and excerpted output: the literal command string and the relevant stdout or stderr lines or exit status. Identify truncation. Identify the working directory when it matters.
- File path with line or range reference: `<path>:<line>` or `<path>:<start>-<end>` so the reader can open the named region.
- Git object reference: a full or unambiguous short SHA, branch name, tag name, or `<base>..<head>` range, with the command that produced it when relevant.
- Diff path list: the output of `git diff --name-only`, `git show --name-only`, or `git status --short`, scoped to the relevant base or commit.
- Hash digest: algorithm name and digest string produced by the tool that computed it, against a named path.
- Validator pass or fail line: the literal final line emitted by the validator, with its exit status.
- Log excerpt: the relevant lines from a named log file with the file path and a line or timestamp range.
- Manifest entry: a quoted field from a tracked or generated manifest with the manifest path.
- Test output: the test runner's per-test or summary line plus the pass or fail count and exit status.
- Read-only inspection result: the literal output of a non-mutating command bound to the claim it supports.

Unacceptable as evidence:

- Memory, recall, prior training, or general knowledge of how the tool usually behaves.
- "It should", "it would", "by convention", "as documented elsewhere" without a citation.
- "Looks fine", "works as expected", or other unanchored confidence.
- Tool summaries that the writer did not inspect directly.
- Briefing or context provided to the writer without independent confirmation.
- Stale evidence whose provenance predates the relevant change.
- An invocation transcript without its result. "Ran X" is not evidence that X produced the claimed outcome.

## Claim discipline

Before writing the report, separate each consequential statement into one of four kinds and never mix them in the same sentence:

- `FACT`: a statement supported by directly inspected, currently valid evidence in this work session.
- `INTERPRETATION`: a reading of evidence that exceeds what the evidence directly shows. Mark the underlying evidence and the inference distance.
- `ASSUMPTION`: a working condition the writer believes but has not verified. Mark explicitly and identify what would confirm it.
- `UNRESOLVED`: a known unknown the writer could not resolve within scope.

Apply this rule for every consequential claim:

- A `FACT` must carry citation evidence within the same paragraph or list item, or in a clearly named appendix the claim references by index.
- An `INTERPRETATION` must carry the underlying `FACT` evidence and a one-line statement of the inference.
- An `ASSUMPTION` must be flagged with the literal label so a reader can find it and challenge it.
- An `UNRESOLVED` item must be listed in the report's unresolved section and may not be silently absorbed into a `FACT`.

A negative claim is a claim, and its wording must match what the evidence can establish (see Negative-evidence rules). "No config files were changed" is a final-state claim backed by a diff filtered by the config path. "No push occurred" is an event-history claim that a current-state check cannot establish on its own; word it as a final-state or transcript-limited claim, or mark it `UNRESOLVED`, unless a trusted event trace is available.

A completion claim is a claim. "Complete", "ready", "safe", "merged", "pushed", "cleaned up", "passes", "production-ready" are completion or readiness labels and must each be backed by the specific evidence the label implies.

## Report-writing rules

Write so the auditor can verify the report by reading it and inspecting cited artifacts, without needing the writer to explain anything.

Required content the primary report must carry (the primary skill decides the section names and order; this modifier only requires that the following appear somewhere in that single report):

- A single verdict using the report's defined vocabulary, placed before any prose justification.
- A repository or system state section that quotes the read-only state evidence used as the audit baseline.
- A changes or actions section that lists what was added, modified, removed, run, or transferred, with citation evidence per item.
- A validation section that lists every validation command actually run with its exit status and the relevant output excerpt.
- A scope section that lists which authorized paths or actions were touched and confirms which forbidden paths or actions were not, each with cited evidence.
- An unresolved or non-actions section that lists known unknowns, deferred items, and authorized actions not taken.
- An evidence appendix that gathers commands and outputs the report cites by reference rather than inline.

Style rules:

- Quote literal command strings and their outputs; do not paraphrase commands or summarize outputs into adjectives.
- Prefer short, citable bullet entries over long narrative paragraphs.
- When summarizing, retain enough of the original output that the auditor can match it against the artifact.
- When a claim cannot be backed in the allowed report length, move the evidence to the appendix and reference it.
- Label uncertainty in the same sentence as the claim, not in a separate disclaimer.
- Do not soften unsupported claims with hedging words to make them look qualified; mark them `ASSUMPTION` or `UNRESOLVED` or remove them.

Handling unverifiable claims:

- Downgrade: convert the claim from `FACT` to `INTERPRETATION` or `ASSUMPTION` and cite the partial evidence available.
- Omit: remove the claim from the report if it is not needed for the verdict and cannot be backed.
- Mark `UNRESOLVED`: keep the claim in the report only as an explicit unknown, with the next step that would resolve it.

Do not delete a known unknown to make the report look cleaner. Do not invent evidence to elevate an `ASSUMPTION` to a `FACT`.

## Negative-evidence rules

Word each negative claim to match what the observation surface can establish. The governing rule: **absence from an incomplete observation surface establishes non-observation, not non-occurrence.** Classify every negative as a final-state claim, an event-history claim, a transcript-limited claim, or `UNRESOLVED`.

- **Final-state claims** (supportable from read-only inspection):
  - "No dirty state now": empty `git status --short` output.
  - "The final diff against baseline shows no change to `<path>`": empty `git diff --name-only <base>..HEAD -- <path>`.
  - "No tag matching `<name>` exists currently": `git show-ref --tags` / `git tag --contains <commit>`.
- **Event-history claims** ("no push occurred", "no tag was ever created", "no remote access happened", "`<path>` was never edited during the work"): require a trusted, sufficiently complete event trace (a reflog, a controlled harness, a trusted command log). An absent upstream, an unchanged remote ref, or an empty final diff describes final state and cannot establish these. Without such a trace, downgrade to a final-state or transcript-limited claim, or mark `UNRESOLVED`.
- **Transcript-limited claims** ("the captured command log shows no push command"): state the observation surface; do not extend the claim beyond it.

A negative claim whose required observation surface is not available, but which the verdict needs as an event-history fact, is not evidence-backed: word it honestly or mark it `UNRESOLVED`. Omission is never itself evidence of non-occurrence.

## Stop-and-report triggers

Stop writing the report and report the blocker instead when:

- A consequential claim cannot be evidence-backed and is required by the verdict.
- The evidence available contradicts a claim the verdict assumes.
- The writer has been asked to assert outcomes that the writer's authorization, scope, or tooling could not have produced.
- The writer is being asked to summarize a tool result the writer did not directly inspect.
- The required reporting format would force conflation of `FACT`, `INTERPRETATION`, `ASSUMPTION`, and `UNRESOLVED`.

A report that cannot meet this discipline must declare the gap, not paper over it.

## Verdict vocabulary

This skill governs reporting discipline; verdict labels come from whichever task-specific skill the report is closing. When a report-level meta-verdict is needed, use:

- `EVIDENCE_CITATION_DISCIPLINED`: every consequential claim is `FACT`-with-citation, `INTERPRETATION`-with-citation, explicit `ASSUMPTION`, or explicit `UNRESOLVED`.
- `EVIDENCE_CITATION_INCOMPLETE`: at least one consequential claim is unsupported and the verdict still depends on it.

## Required report content (not a competing layout)

This modifier does not define a report layout and does not compete with the primary skill's section order. It requires only that the primary skill's single report carry the following content somewhere, under whatever section names and order that skill defines:

- `VERDICT` content: one label from the primary skill's vocabulary, placed before prose. Optionally followed by the meta-verdict above. This modifier never adds a second top-level verdict.
- `STATE BASELINE` content: read-only inspection at the start of the reported work, with cited commands.
- `ACTIONS` content: every consequential action with citation evidence (added files with path, modified files with diff range, commands run with exit status, transfers with source and destination).
- `VALIDATION` content: every validation command actually run, with literal final-line outputs and exit statuses.
- `SCOPE AND NON-ACTIONS` content: which authorized paths or actions were touched, which forbidden paths or actions were not, and explicit non-actions, each cited within the limits of the evidence model.
- `UNRESOLVED` content: known unknowns, deferred items, and authorized but not-performed actions; write `none` when empty.
- `EVIDENCE APPENDIX` content: full text of cited commands and outputs summarized inline, plus references to logs, files, or artifacts.

When the primary skill already defines equivalent sections, fold this content into them rather than adding duplicates. A reader who has access to the cited artifacts must be able to confirm every `FACT` without contacting the writer.

## Allowed actions

- Cite commands the writer actually ran in this work session.
- Cite files the writer actually inspected in this work session.
- Cite manifests, logs, and artifacts the writer actually opened or generated in this work session.
- Mark claims as `ASSUMPTION` or `UNRESOLVED` when their evidence is incomplete.
- Recommend the inspection that would convert an `ASSUMPTION` into a `FACT`.

## Forbidden actions

- Citing evidence the writer did not directly inspect.
- Quoting fabricated, paraphrased, or summarized command output as if it were literal.
- Asserting completion, safety, success, or readiness without the evidence the label implies.
- Smuggling `ASSUMPTION` or `UNRESOLVED` content into a `FACT` paragraph.
- Removing an unresolved item to make the report look complete.
- Using softening language to disguise unsupported claims as qualified ones.

## Anti-patterns

- "All tests pass" with no test command, no scope, and no pass count.
- "No changes to production code" with no diff filtered by the production paths.
- "Pushed cleanly" with no remote-ref evidence and no push transcript.
- "Cleaned up the temporary files" with no listing showing they are gone.
- "Production-ready" with no enumerated production checks.
- "Validator passed" with no final-line excerpt and no exit status.
- "Audit complete" with the auditor's own summary substituted for cited evidence.
- A negative claim with no inspection named to support the negative.
- A confident verdict immediately followed by hedging prose that contradicts it.
