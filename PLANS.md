# Executable plans

Use an executable plan (ExecPlan) for multi-hour work, dependent milestones, a handoff
across sessions, or a change whose scientific and compatibility evidence must remain
reviewable. Place plans at `plans/<short-task-name>.md`. A plan records the authorization
in the current task; it never expands it.

An ExecPlan must be self-contained. A contributor with only the working tree and the plan
must be able to understand the problem, protected contracts, intended behavior, files in
scope, ordered work, and acceptance evidence. Define project-specific terms in plain
language and use repository-relative paths. Do not depend on private machine paths,
conversation history, or unstated production knowledge.

## Required content

Every plan states:

- the user-visible outcome and the behavior that demonstrates it;
- the current branch and starting commit, inspected repository state, and protected paths;
- relevant authorities in `AGENTS.md`, `.agents/PROJECT_PROFILE.md`, and `docs/`;
- the current producer, caller, consumer, input schema, and result authority for a
  scientific or data-contract change;
- sequential milestones with exact paths, expected observations, and validation commands;
- compatibility, failure, valid-empty, recovery, and rollback considerations;
- explicit boundaries for environments, external tools, production, remotes, Git, and
  releases; and
- the concrete evidence required before each authorized gate.

## Living sections

Maintain these sections throughout execution:

### Progress

Use timestamped checkboxes. Mark a milestone complete only after its acceptance command ran
and its decisive output was read. State skipped checks precisely.

### Surprises & Discoveries

Record unexpected repository state, changed assumptions, environment drift, failed
preconditions, and evidence that changes the implementation. Include the observation that
supports each entry.

### Decision Log

Record material decisions with date, owner, evidence, alternatives considered, and effect
on scope or compatibility. A plan author may resolve routine implementation choices but
cannot grant new authorization.

### Outcomes & Retrospective

At completion, state the resulting behavior, changed paths, executed checks and counts,
remaining risks, unresolved findings, and the exact next authorized action. Keep blocked or
partial work explicit.

## Plan discipline

Update the plan when a milestone or decision changes, keeping the whole document internally
consistent. Do not use it as a transcript. Keep exploratory detail in temporary task-owned
evidence and retain only conclusions needed to resume or review the work.

Describe recovery without assuming that deletion, reset, overwrite, history rewrite, or
process intervention is allowed. At a permission boundary, prepare the complete reviewable
artifact and exact proposed command, then stop. A local code edit does not authorize a
commit, and a commit does not authorize integration, push, tag, release, deployment, or
production execution.
