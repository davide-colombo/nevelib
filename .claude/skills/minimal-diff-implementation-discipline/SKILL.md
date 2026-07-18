---
name: minimal-diff-implementation-discipline
description: "Use when implementing a bounded change; produce the smallest correct diff, preserve stable contracts and formatting, and stop at authorized scope without drive-by refactors."
license: "MIT"
---

# Minimal-Diff Implementation Discipline

## Purpose

Constrain an implementing agent to make the smallest correct change that satisfies the current prompt's objective. Preserve existing contracts, formatting, structure, and unrelated behavior. Separate work that the objective requires from work that the agent would merely prefer to do. Stop when the requested scope is complete, and report deferred cleanup rather than silently performing it.

## Composition role

Default role: **modifier**. This skill changes how a bounded implementation is performed; it does not impose its own report schema.

- **Can be primary when directly selected:** no. It shapes another skill's work rather than owning a task objective.
- **Owns a report when composed:** no. It supplies scope-boundary and minimal-diff discipline, and the deferred-cleanup list, to the primary skill's single report.

## When to use

Use this skill whenever an agent is authorized to modify files to satisfy a defined implementation objective, including bug fixes, narrow feature additions, configuration changes, test additions tied to a specific behavior, documentation edits with a defined target, and authorized maintenance edits. Apply it alongside the implementation prompt produced from `prompt-crafting-for-coding-agents`, and report against it with `evidence-citation-discipline`.

## When not to use

Do not use this skill as the primary procedure for read-only audits, code review, dependency upgrades, broad refactors, repository reorganizations, format-only sweeps, or planned migrations. Those tasks have their own scope and acceptance criteria; treating them as "implementation" tasks under this discipline either understates the work or hides scope expansion. Do not use it to justify skipping a required fix that lies inside the authorized scope merely because the fix is large; minimality is measured against the objective, not against arbitrary line counts.

## Required inputs

Obtain from the current prompt, applicable project profile, and observed local state:

- The single implementation objective and its explicit completion criterion.
- The exact allowed files and directories.
- The exact forbidden files and directories.
- Whether new files, new tests, or new directories may be created.
- Whether changes to public interfaces, on-disk formats, configuration keys, log lines, or other observable contracts are explicitly authorized.
- The formatting policy: whether reformatting touched lines is permitted, and whether reformatting untouched lines is forbidden.
- The validation commands and their success criteria.
- Whether dependency, lockfile, build-system, or environment changes are authorized.

Treat any unspecified authorization as forbidden. Do not infer permission to broaden scope from the technical ability to do so, from "while you are there" reasoning, or from a sense that the surrounding code could be improved.

## Minimal-diff rules

Apply each rule to every edit:

- Make the smallest change that satisfies the objective. If two correct changes differ only in breadth, choose the narrower one.
- Touch only the files whose content the objective requires. Do not open additional files to edit them.
- Within a touched file, modify only the lines whose behavior the objective requires. Leave adjacent lines unchanged.
- Do not reformat code, reflow comments, normalize whitespace, change quoting style, change indentation, or change line endings on lines the objective does not require.
- Do not reorder imports, declarations, fields, methods, configuration keys, or list entries unless reordering is itself the objective.
- Do not rename variables, parameters, functions, classes, files, or directories unless renaming is itself the objective.
- Do not introduce, remove, or reshape abstractions (helpers, base classes, decorators, generics, wrappers) unless the objective requires the new shape to satisfy a stated requirement.
- Do not change error messages, log lines, exception types, return shapes, or other observable strings unless the objective requires it.
- Do not add or change dependencies, lockfiles, build configuration, or environment files unless explicitly authorized.
- Do not add tests beyond those that exercise the implemented change, and do not modify unrelated tests.
- Do not add comments that narrate the task, the prompt, the reviewer, or the change history; comment only where the code's meaning would otherwise be ambiguous to a future reader.
- Do not delete code that the objective does not require deleting, even when the code appears unused or unreachable.
- Prefer the change that leaves the surrounding code structurally indistinguishable from its prior state, except for the behavior the objective requires.

A small change that does the wrong thing is not minimal; a correct change that drags in unrelated edits is not minimal either. Minimality is correctness under the objective with the least additional surface.

## Required-fix vs optional-cleanup separation

Classify every candidate edit before making it:

- `REQUIRED`: the objective cannot be satisfied without this edit, or this edit is necessary to keep the codebase compiling, passing validation, or honoring an existing contract after the required change.
- `ADJACENT_CLEANUP`: an edit that would improve the surrounding code (naming, structure, documentation, tests, dead code, dependencies) but is not required by the objective.
- `OUT_OF_SCOPE`: an edit that lies outside the allowed files, touches a forbidden path, or implies a contract change not explicitly authorized.

Only `REQUIRED` edits belong in this diff. Record every `ADJACENT_CLEANUP` candidate as a deferred item in the report so the user can authorize it as a separate, scoped task. Stop and report any `OUT_OF_SCOPE` requirement before making it; do not absorb it into the current change.

When a `REQUIRED` edit cannot be made without first performing what would otherwise be `ADJACENT_CLEANUP` (for example, a function must be split because the change cannot be expressed otherwise), document the dependency in the report and constrain the cleanup to the minimum that unblocks the required change. Do not extend the cleanup beyond that minimum.

## Contract preservation

Treat as a stable contract, unchanged unless the objective explicitly authorizes the change:

- Public function, method, class, and module signatures, including parameter names where callers rely on keyword arguments.
- Command-line interfaces, subcommand names, flag names, default values, and exit-status meanings.
- On-disk data formats, schemas, file names, directory layouts, and serialization details consumed by other code or by users.
- Configuration keys, defaults, value types, and resolution order.
- Observable log lines, error messages, exception types, and structured event fields that downstream code or operators may match against.
- Network, protocol, and API request and response shapes.
- Test fixtures, golden files, and snapshots not in the objective's scope.

If satisfying the objective appears to require a contract change, stop and report it before changing it. Do not change a contract and then justify the change in the report; the authorization must precede the change.

## Completion boundary

Stop editing as soon as the objective's explicit completion criterion is satisfied and the authorized validation passes. Do not look for adjacent improvements, follow-on refactors, or further opportunities once the objective is met. The completion boundary is defined by the prompt, not by the agent's judgment about what the surrounding code "deserves."

If the validation command fails for a reason unrelated to the implemented change (for example, a pre-existing flaky test, a missing tool, an unrelated lint warning), stop and report the failure rather than expanding the diff to fix it.

## Stop-and-report triggers

Stop before editing further, and report, when any of these conditions occurs:

- The objective cannot be satisfied without editing a forbidden path, creating a forbidden file, or changing a contract that is not explicitly authorized.
- The objective cannot be expressed without an abstraction change, rename, reorganization, or dependency change that the prompt has not authorized.
- A `REQUIRED` edit appears to depend on a broader cleanup than the prompt permits.
- The authorized validation command fails for a reason the minimal diff did not introduce.
- The minimal change conflicts with another in-progress change visible in the working tree or branch.
- An unrelated dirty path is present in the working tree and would be carried into the commit.
- Acceptance criteria, allowed files, or forbidden files are ambiguous enough that "minimal" cannot be determined.

Report the trigger, the affected edit, the evidence supporting the classification, and the minimum decision or authorization needed to proceed. Do not work around a trigger by silently broadening scope.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict from the vocabulary below and a one-sentence rationale.
2. `OBJECTIVE AND SCOPE`: the stated objective, completion criterion, allowed files, and forbidden files.
3. `FILES CHANGED`: every changed file with a concise summary of what changed, with diff-range or line-range citations sufficient for an auditor to open the named region.
4. `DELIBERATE NON-CHANGES`: edits that an agent might reasonably expect but that were deliberately not made, with the reason (out of scope, contract preservation, formatting policy, deferred cleanup).
5. `DEFERRED CLEANUP`: every `ADJACENT_CLEANUP` candidate observed and not performed, with location, suggested action, and why it was not included; write `none` when empty.
6. `CONTRACT IMPACT`: confirmation that each affected contract was preserved, or, when authorized, the exact contract change made and the authorization quoted.
7. `VALIDATION EVIDENCE`: every validation command actually run, with exit status and the relevant final-line output; commands not run and why.
8. `STOP CONDITIONS ENCOUNTERED`: triggers that were hit and how they were resolved (or that they remain blocking); write `none` when empty.
9. `NEXT RECOMMENDED STEP`: one minimum action supported by the verdict.

Do not present `ADJACENT_CLEANUP` as performed work, and do not omit it to make the diff look complete.

## Allowed actions

- Read the prompt, project profile, local overlay, and on-disk documentation within scope.
- Inspect the allowed files and the minimum surrounding code necessary to make the required change correctly.
- Edit only the lines within the allowed files that the objective requires.
- Run only the validation commands the prompt authorizes, within their stated scope.
- Record deferred cleanup candidates in the report.
- Stop and report when a trigger above applies.

## Forbidden actions

- Editing any file outside the explicit allowlist.
- Editing any line within an allowed file that the objective does not require.
- Reformatting, reflowing, re-quoting, reordering, or renaming outside the objective.
- Introducing, removing, or restructuring abstractions not required by the objective.
- Changing any stable contract without explicit prompt authorization quoted in the report.
- Adding, removing, or upgrading dependencies, lockfiles, or build configuration without explicit authorization.
- Adding tests, fixtures, snapshots, or documentation beyond what the objective requires.
- Silently performing `ADJACENT_CLEANUP` instead of reporting it.
- Continuing past the completion boundary to look for further improvements.
- Bypassing a stop trigger by broadening scope, switching branches, stashing, or otherwise mutating state.

## Verdict vocabulary
This is a discipline status, not a task verdict. When composed, the task verdict comes from the primary skill; report this only as a component note.

- `MINIMAL_DIFF_COMPLETE`: the objective is satisfied, the diff contains only `REQUIRED` edits within the allowed scope, no stable contract changed beyond explicit authorization, authorized validation passed, and no deferred cleanup blocks the objective.
- `MINIMAL_DIFF_COMPLETE_WITH_DEFERRED`: the objective is satisfied under the same constraints as above, and one or more substantiated `ADJACENT_CLEANUP` candidates are reported as deferred for separate authorization.
- `MINIMAL_DIFF_BLOCKED`: a stop trigger prevented completion (ambiguous scope, validation failure unrelated to the diff, missing authorization, conflicting working-tree state, or inability to satisfy the objective minimally).
- `MINIMAL_DIFF_SCOPE_EXCEEDED`: the diff contains edits outside the allowed scope, touches forbidden paths, changes an unauthorized contract, or otherwise breaches minimality; the change must be revised before review.

Use `MINIMAL_DIFF_BLOCKED` when the agent stopped before committing the breach. Use `MINIMAL_DIFF_SCOPE_EXCEEDED` when the breach is already present in the working tree or commit and must be corrected.

## Anti-patterns

- Reformatting an entire file because one line was edited.
- Reordering imports or sorting members "while editing" the file.
- Renaming a local variable, parameter, or helper because the new name reads better.
- Extracting a helper function for a single new call site.
- Replacing an existing pattern with a "better" pattern across unrelated call sites.
- Bumping a dependency version because a newer one is available.
- Adding type annotations, docstrings, or comments to surrounding unchanged code.
- Adding tests for unrelated behaviors that happen to live in the same file.
- Removing code that "looks unused" without an objective that requires the removal.
- Folding multiple independent objectives into one diff because they touch overlapping files.
- Quietly changing an error message, log line, or exit status to match a preference.
- Treating a passing validation as license to keep editing past the objective.
- Reporting cleanup as done so the diff looks "tidy" without authorization.
