---
name: token-efficient-repository-inspection
description: "Use when inspecting a repository to answer a defined evidence question; minimize reads by searching before reading, using narrow line ranges, and stopping when evidence suffices."
license: "MIT"
---

# Token-Efficient Repository Inspection

## Purpose

Constrain agents to inspect a repository with the minimum reads that produce the evidence the task actually requires. Treat every file read, directory listing, and search invocation as context cost that propagates into every subsequent step. Replace broad "load everything" inspection with an explicit evidence question, an inventory-first and search-first ordering, narrow line-range reads, and a definite stop point once the question is answered. Apply this skill in audit, review, implementation planning, handoff intake, and any other task that begins with "look at the repo."

## Composition role

Default role: **modifier**. This skill changes how repository inspection is performed; it does not impose its own report schema.

- **Can be primary when directly selected:** no. It shapes another skill's work rather than owning a task objective.
- **Owns a report when composed:** no. It supplies inspection strategy and efficiency evidence (files read, search-before-read) to the primary skill's single report, not a parallel report.

## When to use

Use this skill whenever an agent must inspect a repository or filesystem to answer a question, including:

- Locating where a symbol, command, configuration key, or behavior is defined.
- Confirming whether a file, directory, or change exists.
- Understanding enough of the code surrounding a change to plan a `minimal-diff-implementation-discipline` edit.
- Gathering evidence for `agent-output-verification-and-claim-audit` or `read-only-audit-protocol`.
- Mapping a small unfamiliar area of a codebase to a defined question.

Apply this skill at the start of any inspection and re-apply it whenever the question changes.

## When not to use

Do not use this skill as a substitute for `repo-state-audit` (which establishes branch, HEAD, and working-tree safety), for `read-only-audit-protocol` (which bounds mutation during inspection), or for `evidence-citation-discipline` (which governs how the inspection's findings are written down). Do not use it to justify skipping reads that the evidence question genuinely requires; minimality is measured against the question, not against an arbitrary read budget. Do not use it as license to inspect privately restricted, off-limits, or unauthorized surfaces; it does not grant access.

## Required inputs

Before opening any file, establish:

- The evidence question: a single sentence stating what fact the inspection must produce.
- The sufficiency criterion: what observation would answer the question, and what observation would refute it.
- The authorized read surface: which paths, directories, branches, or refs the agent may read.
- Known noise paths: generated trees, vendored dependencies, lockfiles, build outputs, snapshot fixtures, binary blobs, and large data files that are not the evidence target.
- The downstream consumer of the evidence: the skill, decision, or report that will use it.

Treat an unspecified read surface as the working tree only. Do not extend inspection to other branches, refs, remotes, or filesystems unless that access is explicitly authorized by the current prompt. If the question is too vague to define a sufficiency criterion, stop and ask for clarification rather than reading widely "to be safe."

## Inspection ordering

Conduct inspection in this order, descending only when the previous step is insufficient:

1. State the evidence question and the sufficiency criterion in the report or working notes. If either cannot be stated, stop.
2. Consult inventory: list directories or tracked files at the relevant scope using bounded commands such as `git ls-files <path>`, `find <path> -maxdepth N -type f`, or a single directory listing. Prefer Git-aware inventories over filesystem traversals where the question concerns tracked content.
3. Search with `grep`/`rg`-equivalent tools, scoped to the smallest path that could plausibly contain the evidence and to the specific symbol, string, or pattern that would identify it. Capture file paths and line numbers from the match output; that output is itself evidence.
4. Read targeted line ranges of the matched files (for example, the function or block surrounding a hit), not the entire file, unless the file is short enough that opening it in full costs less than two range reads.
5. Read whole files only when the question requires understanding the whole file (for example, a configuration file under 200 lines whose meaning depends on the full contents).
6. Stop as soon as the sufficiency criterion is met. Do not move to the next step out of habit.

Each step's output is evidence; do not repeat the step against the same scope to "double-check" what the prior output already says.

## Reading discipline

Apply these rules to every read:

- Prefer line ranges over whole files. Use the smallest range that contains the evidence and its immediate context (typically the enclosing function, class, block, or section).
- Do not re-read a file whose relevant range is already in the working context. Refer back to the prior read instead of issuing it again.
- Do not open files merely because they are nearby, share a name pattern, or "might be related." A speculative read without a stated question is forbidden.
- Skip generated trees: build directories, compiled outputs, lockfiles, vendored dependency trees, snapshot/golden fixture trees, minified bundles, and binary artifacts. Open them only when the question is itself about that content.
- Skip large or noisy documentation that does not bear on the question: changelogs, release notes, contributor guides, archived design notes, third-party READMEs vendored under dependencies. Read documentation only when it directly answers the question.
- Do not open whole-directory dumps. Inventory-first listings answer "what is here"; reading every file to "build context" is forbidden.
- When the file is large and the relevant region is unknown, search the file first; do not page through it from the top.
- Record each file read in the form `<path>:<start>-<end>` so the evidence is auditable and the cost is visible.

## Search-result handling

Treat the output of an inventory or search command as evidence in its own right:

- The list of matched file paths and line numbers may by itself answer existence, location, or count questions. Reading the matched files is unnecessary in that case.
- A match's surrounding context (one to a few lines of `grep -C` output) often suffices for "is the call here, and what does it look like." Do not open the file just to see the same line in editor form.
- When the search returns many matches, narrow the pattern, narrow the path scope, or sample matches; do not read every match to be exhaustive when the question does not require exhaustiveness.
- When the search returns no matches, treat the empty result as evidence that the symbol or string is absent from the searched scope. Do not start opening files to look for it; refine the pattern or widen the scope only with a stated reason.
- Hold prior search output in working context rather than re-issuing the same search.

## Stop-once-enough-evidence rule

Stop inspecting as soon as the sufficiency criterion is met. The criterion was defined before the inspection began; reaching it ends the inspection. Do not:

- Read additional files "for completeness" once the question is answered.
- Expand into adjacent modules to understand the broader system unless a new, explicit question requires it.
- Page through the rest of a file once the relevant range has been read.
- Re-run the validating search or read to confirm what was just observed.

If the inspection answers the question more cheaply than expected, accept the savings; do not consume the remaining budget. If the inspection cannot answer the question within the authorized read surface, stop and report; do not extend the surface unilaterally.

## Stop-and-report triggers

Stop inspection and report when:

- The evidence question or sufficiency criterion cannot be stated from the inputs.
- The evidence cannot be obtained from the authorized read surface and extending the surface is not authorized.
- The evidence target is a generated, vendored, binary, or otherwise excluded artifact and reading it is not authorized.
- Continuing would require opening files that exceed authorized scope, including private paths, secrets, or excluded directories.
- Search and inventory contradict each other (for example, the file appears in `git ls-files` but search returns no expected content) in a way that suggests a stale checkout or another integrity issue.
- The inspection has already produced sufficient evidence to answer the question; continuing would be overread.

Report the trigger, the question status, the evidence collected so far, and the minimum decision, authorization, or new question needed to proceed.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: one verdict from the vocabulary below and a one-sentence rationale.
2. `EVIDENCE QUESTION`: the single-sentence question and the sufficiency criterion stated before inspection began.
3. `COMMANDS RUN`: every inventory, search, and read command actually issued, in order, with exit status and a concise note on what each contributed.
4. `FILES READ`: every file opened, with `<path>:<start>-<end>` ranges and a one-line summary of what the read showed.
5. `FINDINGS`: the answer to the evidence question, cited against the rows above.
6. `STOPPED BECAUSE`: the explicit reason inspection ended (sufficiency met, blocked, overread detected).
7. `OPEN QUESTIONS`: questions that arose but were out of scope for this inspection; write `none` when empty.
8. `DEFERRED INSPECTION`: reads that were considered and deliberately skipped, with the reason; write `none` when empty.

A reader of the report must be able to reproduce the inspection from `COMMANDS RUN` and `FILES READ` alone, without rereading the repository.

## Allowed actions

- Define the evidence question and sufficiency criterion before any read.
- Run bounded inventory commands within the authorized read surface.
- Run bounded search commands scoped to the smallest plausible path.
- Read targeted line ranges of matched files.
- Read short files in full when full-file context is required by the question.
- Reuse prior search output and prior reads held in working context.
- Stop and report when a trigger above applies.

## Forbidden actions

- Inspecting without a stated evidence question and sufficiency criterion.
- Reading whole files when a search and a line-range read would answer the question.
- Re-reading a file whose relevant range is already in context.
- Opening files speculatively, "to get a feel," or "because they might be related."
- Reading generated, vendored, lockfile, snapshot, build, minified, or binary trees unless the question is about that content.
- Loading broad documentation (changelogs, release notes, third-party READMEs, archived design notes) that does not bear on the question.
- Dumping whole directories file by file to "build context."
- Paging through a large file from the top instead of searching it.
- Extending inspection past the sufficiency criterion to "be thorough."
- Repeating a search or inventory command against the same scope to confirm prior output.
- Reading outside the authorized read surface, including other branches, refs, remotes, or filesystems, without explicit authorization.

## Verdict vocabulary
This is a discipline status, not a task verdict. When composed, the task verdict comes from the primary skill; report this only as a component note.

- `INSPECTION_SUFFICIENT`: the evidence question is answered, the sufficiency criterion is met, and no relevant question remains within scope.
- `INSPECTION_SUFFICIENT_WITH_GAPS`: the evidence question is answered well enough for the downstream consumer, but substantiated `OPEN QUESTIONS` or `DEFERRED INSPECTION` items remain and are explicitly noted.
- `INSPECTION_BLOCKED`: the question cannot be answered within the authorized read surface, the necessary content lies behind unauthorized or excluded paths, or required inputs (question, criterion, surface) are missing.
- `INSPECTION_OVERREAD`: reads or searches were performed past the point at which the sufficiency criterion was met, or in violation of the reading-discipline rules; the result is still usable, but the overread must be reported so the cost is visible and the pattern can be corrected.

Use `INSPECTION_BLOCKED` when inspection cannot conclude. Use `INSPECTION_OVERREAD` when inspection did conclude but consumed more reads than the question required.

## Anti-patterns

- Reading a 2,000-line file when a single `grep` would have answered the question.
- Opening `package-lock.json`, `yarn.lock`, `Cargo.lock`, `Pipfile.lock`, generated `dist/` or `build/` trees, or vendored `node_modules`/`vendor/` trees for "context."
- Reading the README, `CHANGELOG`, `docs/`, or contributor guide when the question is about a specific function's behavior.
- Re-reading the same file across iterations instead of holding the cited range in context.
- Running unscoped `find /` or recursive whole-tree reads.
- Loading test fixtures, golden files, or snapshot data unrelated to the question.
- Reading every file in a directory because the question mentions the directory.
- Continuing to inspect after the answer has been found, "just to be safe."
- Issuing the same search twice to confirm the first result.
- Opening a binary file or minified bundle to "see what is inside" without a question that requires that content.
- Treating "I should understand the whole codebase first" as a valid prerequisite for a narrow question.
