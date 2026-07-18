---
name: repo-state-audit
description: "Use when about to run a state-changing repository task, release, or branch switch; verify repo identity, branch, HEAD, working-tree cleanliness, policy, and authorization."
license: "MIT"
---

# Repository State Audit

## Purpose

Determine whether the observed repository state, applicable project policy, requested action, and current prompt authorization are mutually consistent before work begins. Inspect and report; do not silently repair.

## Composition role

Default role: **gate**. This skill decides whether execution may proceed, constrains permitted actions, and adds stop conditions.

- **Can be primary when directly selected:** yes. When the task objective is this gate's decision, it owns a gate-decision report and verdict.
- **Owns a report when composed:** no. Under another primary skill it contributes its proceed/stop decision and permitted-action boundary into that skill's single report and emits no second top-level verdict.

## When to use

Use before any state-changing repository task, after resuming an interrupted session, before a release or deployment, after another actor may have changed the checkout, or when a task supplies an expected branch or commit. Use a read-only audit when the user asks only for inspection or diagnosis.

## When not to use

Do not use as a substitute for code review, test selection, dependency validation, data-integrity validation, or deployment approval. Do not run Git commands outside a Git working tree unless the task is to diagnose that condition. For a directory that intentionally has no version control, report that this skill is not applicable.

## Required inputs

Obtain from the current prompt and observable local state:

- Repository location or an unambiguous current working directory.
- Requested action and intended outcome.
- Explicit authorization in the current prompt for side-effect categories required by that action.

Treat absent authorization as not authorized. Do not infer permission from earlier unrelated tasks, repository configuration, available credentials, or technical capability.

## Optional project profile and local overlay

Load a project profile and then a local overlay when the prompt or always-on instructions identify them. The public skill remains authoritative for its general procedure; the profile supplies stable project facts, and the overlay supplies private bindings or stricter project rules. Resolve conflicts using the authority order stated by the project. Never invent missing policy values.

Optional inputs include:

- Expected branch and expected HEAD.
- Protected branches and the operations prohibited on them.
- Source-of-truth branch.
- Allowed dirty files.
- Local-only files.
- Forbidden files or paths.
- Repository-specific reporting requirements.

## Audit procedure

Run the audit from the repository root. Prefer commands that do not contact a remote or change repository, index, or working-tree state.

1. Establish repository identity and root:

   ```sh
   git rev-parse --show-toplevel
   git rev-parse --is-inside-work-tree
   ```

   Stop if the location is ambiguous, is not a working tree, or resolves to a different repository than the task identifies.

2. Inspect the current branch and exact HEAD:

   ```sh
   git symbolic-ref --quiet --short HEAD
   git rev-parse HEAD
   ```

   If `git symbolic-ref` fails, determine whether HEAD is detached and report it. Compare the observed branch and full commit identifier with expected values when supplied. Do not fetch to resolve a mismatch unless remote access is explicitly authorized.

3. Inspect the working tree, staged changes, unstaged changes, and untracked files:

   ```sh
   git status --short --branch --untracked-files=all
   git diff --cached --name-status
   git diff --name-status
   git ls-files --others --exclude-standard
   ```

   Treat staged, unstaged, and untracked entries as distinct. Compare every dirty path with the allowed dirty files, local-only files, and forbidden paths supplied by policy. An allowlist is exact unless its policy explicitly defines pattern semantics.

   Git status and untracked-file listings normally omit ignored files. Check every policy-named forbidden path directly, including paths that may be Git-ignored, using safe read-only filesystem inspection. For exact paths, use commands such as:

   ```sh
   test -e "$path"
   find "$path" -prune -print
   ```

   Use the policy's documented matching semantics for patterns. Do not broaden a pattern, traverse unrelated large trees, or treat absence from Git output as proof that a forbidden path is absent. Record each direct check and its result.

4. Evaluate branch policy. Determine whether the current branch is protected and whether the requested action is allowed there. Read-only inspection is not equivalent to authorization to commit, merge, rewrite, release, or deploy. If the protected-branch policy is referenced but unavailable or ambiguous, stop before state-changing work.

5. Evaluate alignment:

   - Compare observed branch with expected branch, if supplied.
   - Compare observed HEAD with expected HEAD, if supplied. Resolve abbreviated expected identifiers locally and report the full observed identifier.
   - Identify unexpected staged, unstaged, or untracked paths.
   - Identify any present or proposed forbidden path.
   - Distinguish a policy violation from a harmless but unexpected state difference.

6. Classify the requested action for side effects. State whether it requires any of the following:

   - Remote access, including fetch, pull, clone, API calls, or remote execution.
   - Push or other remote mutation.
   - Destructive filesystem or history operations, including overwrite, deletion, cleanup, reset, or force operations.
   - Dependency installation or environment mutation.
   - Long-running execution.

   For each required category, quote or precisely identify the current-prompt authorization. If none exists, mark the category unauthorized. Authorization for one category does not imply another; for example, remote read access does not authorize push.

7. Choose exactly one verdict using the rules below. Do not change state as part of reaching the verdict.

8. Report every command actually run, exactly as executed and in execution order, with its exit status and a concise result. Do not list commands that were merely considered. Redact secrets from output, but do not obscure repository facts required by the audit.

## Stop-and-report triggers

Stop before state-changing work and report when any of these conditions occurs:

- The repository cannot be identified unambiguously.
- The observed branch or HEAD differs from an expected value.
- HEAD is detached and the requested action assumes a branch.
- A protected-branch rule prohibits or does not clearly permit the requested action.
- An unexpected dirty or untracked path could be overwritten, incorporated, or invalidated.
- A forbidden file or path is present, staged, tracked contrary to policy, or would be created or modified.
- Required policy, profile, overlay, or authorization is missing or ambiguous.
- The requested action needs remote access, push, destructive operations, dependency installation, or long-running execution without explicit current-prompt authorization.
- A proposed audit command would itself modify state or contact a remote without authorization.
- Observed evidence conflicts or a command fails in a way that prevents a reliable verdict.

Do not stash, discard, reset, clean, switch branches, fetch, pull, install, kill jobs, delete outputs, or otherwise repair a trigger condition unless the user separately authorizes that exact action.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict and a one-sentence rationale.
2. `REPOSITORY STATE`: repository root, branch or detached state, full HEAD, and protected-branch status.
3. `WORKING TREE`: staged, unstaged, untracked, allowed dirty, unexpected dirty, and forbidden paths; write `none` for empty categories.
4. `EXPECTED VS OBSERVED`: each supplied expectation and its result; write `not supplied` where applicable.
5. `ACTION AND AUTHORIZATION`: requested action; whether remote access, push, destructive operations, dependency installation, and long-running execution are required; and the authorization evidence for each.
6. `COMMANDS RUN`: exact commands in order, exit statuses, and concise results.
7. `NEXT STEP`: the permitted next action or the specific user decision or correction required.

Do not claim a clean tree from `git status` alone if the required staged, unstaged, and untracked inspections were not completed.

## Allowed actions

- Read project instructions, profiles, and overlays identified by the task.
- Run local, read-only repository inspection commands.
- Compare observed state with supplied expectations and policies.
- Report findings, uncertainty, and the minimum decision needed.

## Forbidden actions

- Modify the working tree, index, references, configuration, hooks, remotes, or object database during the audit.
- Contact a remote merely to make the state look current.
- Stash, discard, clean, reset, checkout, switch, merge, rebase, commit, tag, or push.
- Install dependencies or start long-running work.
- Bypass or weaken protected-branch, forbidden-path, or authorization policy.
- Treat ignored files as safe when policy explicitly names them as forbidden.
- Conceal command failures, dirty paths, detached HEAD, or mismatches.

## Verdict vocabulary
When composed under another primary skill, report this as a gate decision and stop-condition set under that skill's report, not as the task's top-level verdict.

- `READY`: State and policy align, all required inspections succeeded, and every side effect required for the requested action passes all three authorization axes — semantic authorization (the task asked for it), project policy (profile/overlay/branch/data rules permit it), and runtime permission (the sandbox, approvals, and credentials actually allow it). If any axis is unconfirmed for a required side effect, do not report `READY`; use `NEEDS_USER_DECISION` or `BLOCKED`. Runtime capability alone never satisfies `READY`.
- `READY_READ_ONLY`: Read-only inspection or analysis may proceed, but state-changing work is not requested, not authorized, or unsafe; no blocker prevents read-only work.
- `BLOCKED`: A definite policy violation, forbidden path, unsafe dirty state, failed essential inspection, or prohibited operation prevents the requested work.
- `MISALIGNED`: Observed branch, HEAD, or repository identity differs from a supplied expectation, without enough evidence to classify the difference as a policy violation.
- `NEEDS_USER_DECISION`: The state is known, but missing or ambiguous policy, authorization, or competing safe choices require an explicit user decision.

When several verdicts could apply, prefer `BLOCKED` for definite violations, then `MISALIGNED` for explicit state mismatches, then `NEEDS_USER_DECISION` for unresolved authority or choice. Use `READY_READ_ONLY` only when useful read-only work can safely proceed.
