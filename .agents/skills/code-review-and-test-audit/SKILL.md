---
name: code-review-and-test-audit
description: "Use when reviewing code changes and their tests for correctness, contract preservation, risk, and validation evidence before implementing, merging, or integrating."
license: "MIT"
---

# Code Review and Test Audit

## Purpose

Determine whether proposed or completed work satisfies its objective, preserves relevant contracts, handles credible risks, and has durable test and validation evidence. Inspect and report findings before any remediation; passing tests are evidence, not proof of correctness.

## Composition role

Default role: **primary**. This skill owns the task objective, the top-level verdict vocabulary, and the final report, and integrates module and modifier findings.

- **Can be primary when directly selected:** yes.
- **Owns a report when composed:** it owns the report when it is the selected primary for the task phase. When it instead contributes to another primary skill, it provides its findings block without a second top-level verdict.

## When to use

Use before implementation to examine a plan and existing code paths, after implementation to review changed behavior, before integration to assess readiness, or when tests need an independent quality audit. Use after a failed validation command when the failure's significance is unclear.

## When not to use

Do not use as authorization to implement, repair, merge, release, deploy, or broaden the task. Do not use when repository identity or working-tree safety must first be established; perform the applicable repository-state audit first. Do not substitute this skill for domain approval, security testing, performance measurement, or other specialist review when the task requires them.

## Required inputs

Obtain from the current prompt and observable on-disk state:

- Task objective and expected durable behavior.
- Allowed scope, including files, components, and side effects that may be reviewed or changed.
- Review mode.
- Changed files or proposed change set, if any.
- Applicable project instructions and acceptance criteria.

If the objective, scope, or review target is too ambiguous to support a reliable review, stop and report the missing input. Do not invent project rules not present in the current prompt, project profile, local overlay, or on-disk documentation.

## Optional inputs

Use when supplied or discoverable within the allowed scope:

- Project profile and local overlay.
- Design documents, issue descriptions, interface specifications, schemas, or migration plans.
- Supported runtime, configuration, platform, or dependency matrix.
- Backwards-compatibility policy and public interface guarantees.
- Existing validation commands and expected results.
- Prior review findings, failure logs, benchmarks, or coverage reports.
- Explicit risk tolerance or severity policy.

Treat missing optional evidence as uncertainty, not as permission to assume a favorable result.

## Review modes

Choose exactly one mode and state it in the report:

- `READ_ONLY_REVIEW`: Review existing or proposed work without modifying files. Do not modify files, the working tree, dependencies, configuration, or external state.
- `POST_CHANGE_REVIEW`: Review an implemented change against the objective, scope, relevant code paths, contracts, and validation evidence.
- `PRE_INTEGRATION_REVIEW`: Review a completed change for integration readiness, with emphasis on compatibility, interaction risks, complete validation, and unresolved findings.
- `TEST_AUDIT_ONLY`: Review test selection, design, assertions, coverage, reliability, and execution evidence without treating application-code review as complete.

A mode selects review emphasis; it does not authorize remediation or any other side effect. Do not silently fix findings during an audit. Report first, and modify only under separate explicit authorization.

## Audit procedure

1. Restate the task objective, allowed scope, selected review mode, and review target. Identify supplied acceptance criteria and material unknowns.
2. Establish the change set. Inspect every changed file when changes exist, distinguish staged, unstaged, and untracked work when relevant, and confirm that each changed path is within scope. Do not treat a summary or file list as a substitute for reading relevant changes.
3. Trace the relevant existing code paths before judging the change. Inspect callers, callees, state transitions, persistence or serialization boundaries, and configuration or runtime selection paths as applicable.
4. Find the nearest existing analogues in the codebase. Compare conventions, behavior, error semantics, validation, and tests. Explain when no useful analogue exists; do not force an unrelated pattern onto the change.
5. Identify public interfaces and contracts affected by the work, including callable interfaces, command behavior, data formats, schemas, configuration keys, observable errors, and documented guarantees. Separate intentional contract changes from accidental ones.
6. Review correctness against the objective. Follow normal, failure, and recovery paths. Check edge cases, boundary conditions, state consistency, data validation, invalid or partial inputs, and error handling. Look for swallowed failures, misleading success, unsafe defaults, and incomplete cleanup.
7. Review configuration and runtime parity when relevant. Confirm that validated configuration, actual runtime behavior, generated artifacts, and documented usage agree across supported environments. Do not assume one successful environment represents all supported environments.
8. Review backwards compatibility when relevant. Examine existing callers, persisted data, configuration, automation, and user-visible behavior. Identify migrations, deprecations, or version gates required by the project's stated compatibility policy.
9. Review performance and scalability where the change affects data volume, concurrency, repeated work, I/O, memory, latency, or resource lifetime. Require measurement only when justified by the objective or a credible regression risk.
10. Review security and safety boundaries where relevant, including trust boundaries, authorization, secret handling, injection surfaces, path handling, resource exhaustion, destructive behavior, and unsafe failure modes.
11. Perform the test-audit procedure below. Passing tests do not override contradictory code evidence, missing coverage of material risks, or an incorrect test oracle.
12. Inspect validation evidence. Record which commands were actually run, their environment when material, their exit status, and their result. Distinguish commands observed directly from results merely reported by another source.
13. Classify each finding by risk category and severity. State the evidence, affected behavior, and minimum acceptable resolution. Distinguish blocking from non-blocking findings.
14. Select exactly one verdict. Base it on the most severe substantiated finding, unresolved uncertainty, scope compliance, and available validation evidence.

## Test-audit procedure

1. Map tests to the task objective, affected contracts, changed code paths, and identified risks. State important behavior that has no corresponding test.
2. Determine whether tests validate durable externally meaningful behavior rather than incidental implementation details such as private call order, internal structure, unstable formatting, timing accidents, or unnecessary mocks.
3. Inspect assertions and test oracles. Confirm that tests can fail for the defect they claim to detect and do not pass through weak, missing, inverted, or overly broad assertions.
4. Check success paths, failure paths, boundary cases, invalid inputs, partial state, and recovery behavior where relevant. Include regression coverage for corrected defects when the defect can be reproduced deterministically.
5. Assess brittleness and isolation. Identify dependence on execution order, shared mutable state, uncontrolled time, randomness, network access, platform details, environment leakage, or fixtures that conceal the behavior under test.
6. Check that test doubles preserve the contract material to the test. Flag mocks or fixtures that bypass the integration boundary, validation, error behavior, or serialization logic that creates the actual risk.
7. Check configuration/runtime parity when relevant. Determine whether the exercised test path matches the path used by supported runtime configurations and whether material variants need coverage.
8. Inspect existing tests near the changed behavior and the nearest analogues. Look for duplicated coverage, inconsistent expectations, obsolete tests, and suite placement that prevents normal execution.
9. Determine which validation commands were actually run. Do not claim tests passed from their presence in the repository. Record skipped, filtered, unavailable, flaky, or unrun checks and explain the impact.
10. Do not require tests that are impossible to run in the current environment. Report them as not run, explain why, identify the resulting uncertainty, and state whether other evidence is sufficient or the gap blocks the verdict.

## Risk classification

Assign every finding exactly one primary category and a severity of `BLOCKING` or `NON_BLOCKING`:

- `correctness issue`: Behavior can violate the objective, acceptance criteria, or an applicable contract.
- `robustness issue`: Credible invalid, partial, exceptional, concurrent, or recovery conditions are handled unreliably.
- `performance/scalability issue`: Resource use, latency, throughput, repeated work, or growth behavior creates a credible regression or operational limit.
- `maintainability issue`: Structure, duplication, coupling, naming, or complexity materially increases defect or change risk.
- `test-quality issue`: Coverage, assertions, isolation, durability, suite integration, or execution evidence is inadequate or misleading.
- `documentation issue`: Required user, operator, interface, migration, or maintenance guidance is absent or inconsistent with behavior.
- `security/safety issue`: The work weakens a trust boundary, permits unsafe input or action, exposes sensitive material, or creates an unacceptable failure mode.
- `scope violation`: The change exceeds, omits, or conflicts with the authorized scope.
- `non-blocking improvement`: A substantiated improvement that does not prevent the objective, contract compliance, safe operation, or integration readiness.

Use `BLOCKING` when a finding can cause incorrect or unsafe behavior, violates scope or a required contract, prevents meaningful validation, or leaves material integration risk unresolved. Use `NON_BLOCKING` when the work remains correct and safe within stated requirements. Category does not determine severity automatically; explain the consequence.

## Stop-and-report triggers

Stop the audit or stop before further side effects when any of these conditions occurs:

- The objective, allowed scope, review mode, or review target cannot be established reliably.
- Unexpected changes prevent isolation of the intended change set.
- A changed file or requested review action is outside authorized scope.
- Essential project instructions, contracts, generated sources, or relevant code paths are unavailable.
- Evidence conflicts and cannot be reconciled through allowed read-only inspection.
- A required inspection would expose secrets, access prohibited data, contact an external system, install dependencies, or modify state without authorization.
- A validation command would be destructive, unsafe, or outside the allowed environment.
- A security or safety issue makes continued execution unsafe.
- Validation cannot be run and the missing evidence prevents a reliable verdict.

Report the trigger, evidence collected, impact, and the minimum decision or access needed. Do not broaden scope or repair the condition silently.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict and a one-sentence rationale.
2. `REVIEW MODE AND SCOPE`: selected mode, objective, allowed scope, reviewed change set, and exclusions.
3. `FINDINGS`: findings ordered by severity, each with category, `BLOCKING` or `NON_BLOCKING`, location, evidence, impact, and required resolution; write `none` if empty.
4. `CODE REVIEW`: relevant paths and analogues inspected; contracts, correctness, edge cases, error handling, validation, configuration/runtime parity, compatibility, performance, and security conclusions.
5. `TEST AUDIT`: behavior and risks covered, missing coverage, failure and boundary coverage, durability, brittleness, isolation, and test-oracle conclusions.
6. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, commands not run, reasons, and impact. Distinguish observed evidence from reported evidence.
7. `SCOPE ASSESSMENT`: in-scope changes, scope violations, and unrelated changes; write `none` for empty categories.
8. `RESIDUAL RISKS AND WARNINGS`: unresolved non-blocking issues and environmental limitations; write `none` if empty.
9. `NEXT STEP`: minimum remediation, decision, or integration action supported by the verdict.

Do not hide clean conclusions behind only a verdict. Do not report a command as run unless it was actually executed.

## Allowed actions

- Read the task prompt, project instructions, project profile, local overlay, and on-disk documentation within scope.
- Inspect the specified change set, relevant existing code paths, nearest analogues, interfaces, contracts, and tests.
- Run local read-only inspection and explicitly authorized validation commands that are safe in the current environment.
- Classify and report findings, missing evidence, uncertainty, and remediation requirements.
- In non-read-only modes, propose patches or follow-up work without applying them during the audit.

## Forbidden actions

- Modify files in `READ_ONLY_REVIEW` mode.
- Silently fix findings, rewrite tests, alter configuration, or change dependencies during an audit.
- Broaden the reviewed or modified scope without authorization.
- Treat passing tests, high coverage, static analysis, or a successful build as proof of correctness.
- Invent project rules, supported environments, compatibility promises, or acceptance criteria absent from authoritative inputs.
- Require unavailable tests to run in the current environment or misrepresent them as passed.
- Conceal failed, skipped, filtered, flaky, unavailable, or unrun validation.
- Approve work with an unresolved blocking finding or known scope violation.

## Verdict vocabulary
This skill owns the top-level verdict for the task phase. When it instead contributes to another primary, report its status as a component finding.

- `REVIEW_PASS`: No blocking or non-blocking findings remain, the reviewed scope satisfies the objective and applicable contracts, and validation evidence is sufficient for the selected mode.
- `REVIEW_PASS_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking improvements, environmental limitations, or residual risks must be reported.
- `NEEDS_REVISION`: One or more blocking findings require changes before the reviewed work is acceptable.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe conditions, or unavailable essential validation prevent a reliable review conclusion.
- `OUT_OF_SCOPE`: The requested review or material parts of the change set fall outside the authorized scope.

When several verdicts could apply, use `OUT_OF_SCOPE` for unauthorized review scope, `BLOCKED` when evidence cannot support a conclusion, and `NEEDS_REVISION` when sufficient evidence demonstrates a blocking defect. Use a passing verdict only when no blocking finding remains.
