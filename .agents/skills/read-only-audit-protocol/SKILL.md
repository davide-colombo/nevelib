---
name: read-only-audit-protocol
description: "Use when running a strict read-only audit of a commit, patch, branch, output, or agent report; inspect and report readiness without modifying files or systems."
license: "MIT"
---

# Read-Only Audit Protocol

## Purpose

Determine whether an audited target is correctly scoped, supported by evidence, and ready for its claimed next state without modifying repositories, files, environments, remotes, outputs, or running systems. Inspect and report only; never repair findings during the audit.

## Composition role

Default role: **gate**. This skill decides whether execution may proceed, constrains permitted actions, and adds stop conditions.

- **Can be primary when directly selected:** yes. When the task objective is this gate's decision, it owns a gate-decision report and verdict.
- **Owns a report when composed:** no. Under another primary skill it contributes its proceed/stop decision and permitted-action boundary into that skill's single report and emits no second top-level verdict.

## Use cases

Use for audits of:

- Commits, branches, patches, diffs, and pull-request-like work.
- Generated outputs and their contracts.
- Validation commands, logs, artifacts, and other evidence.
- Agent reports and claims about completed work.
- Repository integration readiness.
- Release readiness when mutation is not authorized.

Apply this protocol alongside a more specialized audit skill when needed. The stricter read-only boundary controls all actions. As a gate, this protocol constrains actions and contributes its read-only decision and any mutation-risk findings into the specialized skill's single report; that specialized skill owns the report structure and the top-level verdict. This protocol owns the report only when it is itself the selected primary audit.

## Required inputs

Identify before auditing:

- Repository path.
- Expected current branch.
- Expected base or protected branch.
- Expected HEAD, target commit, or commit range when provided.
- Changed-file allowlist and intended scope.
- Forbidden paths.
- Commands allowed during the audit.
- Expected validation evidence and acceptance criteria.
- Known dirty or local-only files, if any.
- Whether remote or network access is authorized.
- Whether tests may be run or only inspected.

Treat missing authorization as absent. Obtain inputs from the current prompt, applicable project profile or overlay, and observed local evidence. Do not invent project policy. If required inputs cannot be established, stop and report.

## Non-negotiable read-only boundary

During the audit, do not:

- Edit, create, delete, rename, move, or generate files.
- Stage changes, commit, amend, create or delete branches, or modify Git references.
- Check out, switch, rebase, or merge unless the current prompt explicitly authorizes the exact operation solely for safe inspection; prefer commands that inspect objects without changing the worktree.
- Push or create tags.
- Install dependencies or mutate an environment.
- Access a network or remote unless explicitly authorized.
- Write through SSH or any remote interface.
- Synchronize or transfer files or data.
- Execute production workloads or pipelines.
- Perform destructive cleanup.
- Run formatters, auto-fix commands, or tools with implicit write behavior.
- Run tests that write outputs unless the current prompt explicitly authorizes the test and its outputs are isolated and controlled.

Do not treat a dry-run flag as safe without verifying the installed tool's behavior. Prefer inspection of existing evidence over rerunning commands. If a command's side effects are uncertain, do not run it.

## Audit procedure

1. Restate the audited target, expected repository state, scope, allowed commands, evidence requirements, and authorization boundaries.
2. Verify repository state using read-only commands before evaluating claims.
3. Determine the exact diff or object range under audit without switching branches or changing the worktree.
4. Audit scope, patch content, evidence, outputs, and reported claims using the procedures below.
5. Separate observed evidence from reported evidence and inference. Record evidence that is inaccessible or not run.
6. Classify each finding as blocking or non-blocking and select exactly one verdict.
7. Produce the required report without applying fixes or broadening the audit.

## Repository-state verification

Inspect and record:

- Repository root and repository identity.
- Current branch and HEAD.
- Full status covering staged, unstaged, and untracked paths.
- Upstream relation and divergence when relevant and locally observable.
- Recent commits relevant to the target.
- Changed files and the exact comparison base.
- Ignored or local-only files when they can affect the audit.
- Whether the audited commit is reachable from the expected branch or base.

Do not fetch to establish remote state unless network access is explicitly authorized. State when upstream or reachability conclusions rely only on local references.

## Scope audit

Check that:

- Changed files match the allowlist and intended scope.
- No unrelated files, generated junk, or temporary artifacts are included.
- Public files contain no private, project-specific, credential, infrastructure, personal, or restricted data.
- Forbidden paths are unchanged.
- No broad refactor is hidden inside a narrow task.
- Dependency, configuration, schema, or interface changes are intentional and authorized.
- Durable documentation contains no volatile task state, temporary identifiers, or current operational status.

Treat unexplained changes as findings even when tests pass.

## Evidence audit

Evaluate:

- Which validation commands were actually run, by whom or by what system, and with what exit status.
- Whether each command is appropriate, bounded, and relevant to the claimed behavior.
- Whether reported results match available command output, logs, and artifacts.
- Whether failures are fully disclosed and interpreted correctly.
- Whether skipped tests or checks have explicit, credible justification.
- Whether claims exceed the inspected evidence.
- Whether expected output artifacts exist and satisfy counts, names, formats, or contracts when relevant.

Distinguish direct observation, supplied report, and inference. Never convert missing evidence into a passing result.

## Commit and patch audit

Check:

- Commit messages agree with the actual change and requested objective.
- The patch is narrow, correct, internally consistent, and free of unrelated churn.
- No accidental file-mode or line-ending changes are present.
- No binary or large artifacts are added unless explicitly authorized.
- No merge commits are present unless authorized.
- No push is required or implied unless explicitly requested outside this audit.
- No release or tag is claimed unless the tag exists in inspected state and its creation was authorized.

Inspect both aggregate and per-commit diffs when a range contains multiple commits. Verify that the chosen base is the intended base rather than assuming it from branch names.

## Generated-output audit

For generated outputs, inspect as applicable:

- Inventory, filenames, counts, and sizes.
- Schema, header, format, and content contracts.
- Checksums or manifests when available.
- Valid empty outputs versus missing outputs.
- Partial-output markers, temporary names, completion markers, and incomplete publication state.
- Provenance linking outputs to inputs, configuration, producer, and version.
- Compatibility with declared downstream consumers.
- Active-writer or running-process risk before classifying output as final.

Do not open or transform outputs with tools that may rewrite metadata or content. File existence alone does not establish completeness, validity, or finality.

## Agent-report audit

Map each material report claim to inspected repository state, diff content, command output, log, or artifact. Flag omitted changes, unsupported completion claims, misstated validation, concealed failures, and discrepancies between reported and observed state. An agent's summary is a claim source, not independent evidence.

## Stop-and-report triggers

Stop and report when:

- The repository path is missing or is not a Git repository.
- Observed branch or HEAD contradicts supplied assumptions.
- Dirty state is unexpected.
- Continuing the audit would require mutation.
- Required evidence is missing or inaccessible.
- Scope or comparison base cannot be determined.
- A needed command may modify files or other state.
- The public/private boundary is unclear.
- Remote or network access is required but not authorized.

Report the observed condition, affected conclusion, and minimum evidence or authorization needed. Do not repair, clean, switch state, fetch, or rerun a mutating command to bypass a stop condition.

## Final report format

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict and a concise rationale.
2. `AUDITED TARGET`: repository, branch or object range, comparison base, outputs or reports reviewed, and exclusions.
3. `REPOSITORY STATE`: root, branch, HEAD, status, upstream or reachability evidence, and material local-only state.
4. `SCOPE CHECK`: allowlist, forbidden paths, changed files, unrelated changes, public-safety check, and scope conclusion.
5. `EVIDENCE CHECK`: commands and artifacts inspected, results, failures, skipped checks, limitations, and whether claims are supported.
6. `FINDINGS`: blocking and non-blocking findings with target, evidence, consequence, and minimum resolution; write `none` when empty.
7. `RISKS / WARNINGS`: residual uncertainty, locally limited conclusions, active-writer risk, and non-blocking caveats; write `none` when empty.
8. `RECOMMENDED NEXT STEP`: one minimum action supported by the verdict, without performing it.
9. `COMMANDS / EVIDENCE APPENDIX`: read-only commands actually run, exit statuses, concise outputs or references, and evidence not run.

Do not claim a command ran, an artifact was inspected, or a state was verified unless supporting evidence was directly observed.

## Allowed actions

- Read task instructions, project profiles, overlays, source files, repository objects, diffs, logs, reports, manifests, and existing outputs within scope.
- Run local commands whose behavior is known to be read-only and permitted by the current prompt.
- Compare existing evidence, compute bounded summaries in memory, and report findings.
- Recommend a correction, validation action, or authorization request without applying it.

## Forbidden actions

- Any action prohibited by the non-negotiable read-only boundary.
- Silent repair, cleanup, normalization, regeneration, or evidence creation.
- Broadening the target to compensate for unclear scope.
- Treating command success, file existence, reported results, or a clean diff alone as proof of readiness.
- Concealing uncertainty, unavailable evidence, skipped checks, or contradictory state.

## Verdict vocabulary
When composed under another primary skill, report this as a gate decision and stop-condition set under that skill's report, not as the task's top-level verdict.

- `READ_ONLY_AUDIT_READY`: The target is within scope, required evidence is sufficient, no blocking or non-blocking finding remains, and the claimed readiness is supported.
- `READ_ONLY_AUDIT_READY_WITH_WARNINGS`: No blocking finding remains and required evidence supports the target, but substantiated non-blocking limitations or residual risks remain.
- `READ_ONLY_AUDIT_BLOCKED`: Missing inputs, inaccessible evidence, contradictory state, unclear scope, or the read-only boundary prevents a reliable conclusion.
- `READ_ONLY_AUDIT_FAILED`: Inspected evidence demonstrates a blocking scope, correctness, integrity, validation, reporting, integration, or release-readiness failure.

Use `READ_ONLY_AUDIT_BLOCKED` when the audit cannot reach a reliable conclusion. Use `READ_ONLY_AUDIT_FAILED` when sufficient inspected evidence establishes that the target does not satisfy its contract. Use a ready verdict only when all required checks are supported by evidence.
