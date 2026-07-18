---
name: configuration-and-environment-integrity
description: "Use when designing or auditing configuration, runtime parameters, dependency and environment reproducibility, or tool discovery; catch unused settings and hidden defaults."
license: "MIT"
---

# Configuration and Environment Integrity

## Purpose

Determine whether declared configuration, actual runtime behavior, dependency setup, tool discovery, and recorded environment provenance are complete, consistent, reproducible, and safe. Detect accepted-but-unused settings, hidden defaults, undeclared global state, stale dependency metadata, and environment mismatches before expensive or consequential work begins.

## Composition role

Default role: **module**. This skill contributes domain-specific checks and findings.

- **Can be primary when directly selected:** yes. When the task objective is specifically this domain, it owns the report and verdict.
- **Owns a report when composed:** no. Within a larger workflow it reports into the primary skill's schema as a labeled subsection or findings table and emits no second top-level verdict; its verdict becomes a component status that rolls up into the primary verdict.

## When to use

Use when designing or changing configuration, reviewing installation instructions, diagnosing environment-dependent behavior, preparing a release or deployment, reproducing a result, adding an external tool, or auditing whether runtime parameters and recorded provenance match declared policy.

## When not to use

Do not use as authorization to install software, change manifests or lockfiles, mutate environments, deploy, or broaden scope. Do not substitute it for repository-state, code-review, security, licensing, performance, or domain validation. When repository safety is unknown, perform the applicable repository-state audit first.

## Required inputs

Obtain from the current prompt and authoritative project material:

- Task objective, selected task mode, and allowed scope.
- Configuration entry points and supported invocation paths.
- Target runtime environments, operating systems, and hardware constraints when relevant.
- Applicable configuration files, schemas, validation logic, dependency manifests, lockfiles, installation instructions, and runtime selection code.
- Expected validation commands and acceptance criteria.

If the objective, scope, configuration boundary, or target environment cannot be established reliably, stop and report. Do not invent project rules absent from the current prompt, project profile, local overlay, or on-disk documentation.

## Optional inputs

Use when supplied or discoverable within scope:

- Environment-variable reference and precedence policy.
- Supported runtime, dependency, executable, operating-system, or hardware matrix.
- Generated configuration, environment exports, provenance records, and diagnostic output.
- Prior installation logs, failure reports, compatibility records, and clean-environment setup evidence.
- Offline, remote, restricted-network, accelerator, or cross-platform requirements.
- Authoritative tool documentation and installed-tool help or version output.

Treat missing optional evidence as uncertainty, not as permission to assume compatibility or reproducibility.

## Task modes

Choose exactly one mode and state it in the report:

- `CONFIG_DESIGN_REVIEW`: Evaluate proposed configuration keys, defaults, validation, precedence, and runtime consumption before implementation.
- `ENVIRONMENT_AUDIT`: Inspect the current environment, dependency state, runtime identity, tool availability, and target compatibility without treating installation reproducibility as proven.
- `INSTALLATION_REVIEW`: Evaluate setup instructions, declared dependencies, lock state, global assumptions, and clean-environment feasibility.
- `RUNTIME_PARITY_AUDIT`: Trace declared configuration through parsing, validation, precedence resolution, and runtime use to detect divergence.
- `REPRODUCIBILITY_AUDIT`: Assess whether the environment and result-relevant settings can be reconstructed from declared setup and recorded provenance.
- `POST_CHANGE_AUDIT`: Review implemented configuration or environment changes against scope, contracts, compatibility, and validation evidence.

A mode changes audit emphasis; it does not authorize file changes, installation, environment mutation, remote access, or execution outside the allowed scope.

## Configuration model

Inventory every supported configuration source, including files, command inputs, environment variables, generated values, and programmatic interfaces. For each setting, define:

- Name, type, constraints, required or optional status, and owning component.
- Documented default, schema default, runtime default, or absence of a default.
- Whether the value affects outputs, resource use, control flow, safety, compatibility, or provenance.
- Precedence across explicit values, environment-variable overrides, configuration files, generated values, and defaults.
- Validation point, runtime consumer, logging or provenance behavior, and secret-redaction rule.
- Unknown-key behavior and whether any accepted key is ignored by the runtime.

Use these terms precisely:

- `missing required config key`: A required setting is absent after authorized sources and precedence are resolved.
- `unknown config key`: A supplied setting is not declared by the applicable configuration contract.
- `accepted but ignored config key`: Validation accepts a setting, but runtime behavior does not consume or intentionally act on it.
- `hardcoded runtime default`: Runtime code supplies a fallback outside the authoritative declared configuration contract.
- `documented default`: User or operator documentation states a fallback value.
- `schema default`: The configuration schema supplies a fallback value.
- `runtime default`: Runtime logic supplies a fallback when no higher-precedence value is present.
- `environment variable override`: An environment value supersedes another source under the declared precedence policy.
- `missing dependency`: A required library, package, service interface, or runtime component is unavailable.
- `missing executable`: A required external command cannot be resolved under the supported discovery policy.
- `wrong executable version`: The resolved executable is present but outside the supported version or feature contract.
- `incompatible OS or hardware`: The target platform lacks a required capability or violates a declared support constraint.
- `unreproducible installation`: The declared procedure cannot reconstruct the required environment from an allowed clean starting state.
- `stale lockfile`: A lockfile no longer agrees with its source manifest, supported resolver behavior, or required dependency state.
- `undocumented parameter`: A supported or result-affecting setting is absent from the applicable user or operator contract.
- `unsafe implicit behavior`: Undeclared fallback, discovery, coercion, or precedence can produce surprising, destructive, insecure, or irreproducible behavior.

An accepted but ignored config key is a blocking defect. A parameter that affects output must be configurable or explicitly documented as intentionally fixed.

## Environment model

Define the environment as the result-relevant combination of:

- Language or execution-runtime identity and version.
- Direct and resolved package or library versions.
- Required executables, discovery paths or mechanisms, versions, and feature capabilities.
- Operating-system, architecture, hardware, driver, accelerator, filesystem, locale, and shell constraints when relevant.
- Environment variables and other external state that affect installation, discovery, configuration, or runtime behavior.
- Dependency manifests, lockfiles, installation commands, indexes or registries, and source identities required for reconstruction.

Separate the local inspection environment from each target runtime environment. Do not infer remote, production, scheduled, or packaged behavior from local success when configuration, discovery, platform, or installed state can differ.

## Audit procedure

1. Restate the objective, scope, selected mode, supported entry points, and target environments. Identify material unknowns.
2. Inventory configuration files, schema or validation logic, defaults, required and optional keys, environment variables, and runtime consumers.
3. Establish parameter precedence and one authoritative source for each default, or a clearly documented resolution order when several layers are intentional.
4. Trace every declared and supplied key through parsing, validation, normalization, override resolution, and runtime use. Flag unknown, ignored, undocumented, or inconsistently typed settings.
5. Search relevant runtime paths for hardcoded parameters. Determine whether each is intentionally fixed, contractually documented, or required to become configurable.
6. Inventory dependency manifests, lockfiles when present, installation commands, global assumptions, and environment mutations.
7. Inspect executable and tool discovery, version constraints, runtime and package version reporting, and preflight failure behavior.
8. Compare local and target environment behavior, including operating-system and hardware constraints where relevant.
9. Confirm that required validation runs before expensive execution and that missing configuration, dependencies, executables, or platform capabilities fail clearly before work starts.
10. Inspect output provenance and logs for result-affecting configuration and reconstructive environment identity, while ensuring secrets are not exposed.
11. Run the applicable procedures below, classify findings and validation gaps, and select exactly one verdict.

## Schema and runtime parity procedure

1. Enumerate all schema keys and all runtime-read keys; compare the sets in both directions.
2. For every key, compare names, types, constraints, required status, null or empty semantics, defaults, normalization, and error behavior.
3. Verify that every accepted key reaches its intended runtime consumer. Treat an accepted but ignored key as blocking even if validation passes.
4. Verify that every runtime-read setting is declared and documented or is explicitly internal and cannot be supplied externally.
5. Exercise or inspect precedence conflicts across explicit parameters, configuration files, environment-variable overrides, generated values, and defaults.
6. Compare documented, schema, and runtime defaults. Require one authoritative source or a documented precedence order; reject accidental divergence.
7. Confirm that runtime behavior and result provenance reflect the resolved values rather than pre-resolution inputs or stale defaults.

## Dependency and installation procedure

1. Identify every direct runtime, build, validation, and external-tool dependency required by the supported workflow.
2. Map each dependency to a manifest, lockfile when present, installation step, system prerequisite, or explicitly documented external responsibility.
3. Compare manifests, lockfiles, and installation instructions for missing, conflicting, duplicated, or stale declarations.
4. Inspect installation commands for undeclared global packages, pre-existing executables, ambient environment variables, mutable external sources, interactive assumptions, and unrecorded manual steps.
5. Assess reconstruction from an allowed clean environment. A passing import or load check proves only limited availability, not reproducible installation.
6. Do not install dependencies or modify manifests or lockfiles unless the current task prompt explicitly authorizes that exact side effect.
7. Report unavailable clean-environment validation as not run, explain why, and classify the resulting uncertainty.

Installation instructions must not silently rely on undeclared global state. When an intentionally external prerequisite exists, name its contract, supported version, discovery rule, and verification command.

## Tool and version verification procedure

1. Determine the supported discovery rule for each required executable or tool: explicit path, configured location, environment search, managed environment, or platform service.
2. Resolve the exact tool selected by each supported runtime path. Do not assume an interactive shell selects the same executable as scheduled, remote, packaged, or service execution.
3. Record tool identity, path or source when safe, version, required capabilities, and command exit status. Redact credentials and private locations from public reports.
4. Record the language or execution runtime and the result-relevant package versions with sufficient precision to reconstruct the environment.
5. Check version constraints and feature availability rather than existence alone. A successful discovery or import does not establish compatibility.
6. Ensure missing or incompatible required tools fail clearly during preflight, before expensive computation or partial output creation.
7. When tool behavior may have changed, verify it against the installed tool or current authoritative documentation. Do not rely on cached software-behavior summaries.

## Reproducibility and provenance procedure

1. Define the allowed clean starting state and the exact setup procedure.
2. Determine whether manifests, lockfiles, external prerequisites, configuration sources, and installation commands fully describe reconstruction without undeclared global state.
3. Record resolved configuration, precedence outcome, runtime version, package versions, executable identities and versions, platform facts, and dependency or lock identity needed to reproduce result-affecting behavior.
4. Exclude secrets, credentials, tokens, and unnecessary private paths from logs and provenance. Record safe identifiers or redacted evidence instead.
5. Compare reconstructed and original environments at behavior-relevant boundaries; exact byte identity is required only when project policy demands it.
6. Verify target operating-system and hardware compatibility against actual constraints and available evidence. Do not claim compatibility from an unrelated platform.
7. Distinguish an environment that currently works from one that can be reconstructed reliably. Classify unresolved reconstruction failure as `unreproducible installation`.

Version reporting must be sufficient to reconstruct the result-relevant runtime environment, not merely identify one top-level application.

## Risk classification

Assign each finding one primary category and a severity of `BLOCKING` or `NON_BLOCKING`:

- `configuration contract`: Missing, unknown, ignored, undocumented, conflicting, or unsafe settings undermine declared behavior.
- `schema/runtime parity`: Validation and actual runtime consumption, defaults, types, or precedence diverge.
- `dependency integrity`: Manifests, lockfiles, resolved packages, or required components are missing, inconsistent, or stale.
- `installation reproducibility`: Setup depends on undeclared state, mutable inputs, unavailable steps, or cannot be reconstructed.
- `tool/runtime integrity`: Discovery, identity, version, capability, or early-failure behavior is inadequate.
- `platform compatibility`: Operating-system or hardware support is contradicted or lacks required evidence.
- `provenance`: Result-affecting configuration or environment identity is absent, misleading, unsafe to record, or insufficient for reconstruction.
- `scope violation`: Work or requested side effects exceed the authorized scope.
- `non-blocking improvement`: A substantiated improvement that does not threaten correctness, safety, reproducibility, or the applicable contract.

Use `BLOCKING` for accepted-but-ignored keys, material schema/runtime divergence, unsafe implicit behavior, missing required dependencies or tools, unsupported target constraints, unauthorized side effects, or evidence gaps that prevent a reliable conclusion. Explain the observable consequence and minimum resolution.

## Stop-and-report triggers

Stop before installation, mutation, expensive execution, or further side effects when:

- The objective, scope, selected mode, configuration boundary, target environment, or authority cannot be established.
- An accepted key is ignored, a result-affecting parameter is hidden or undocumented, or defaults conflict without authoritative precedence.
- Required dependencies, executables, versions, operating-system features, or hardware capabilities are missing or incompatible.
- Installation depends on undeclared global state or the lockfile is stale and no authorized correction applies.
- Required validation would install software, modify manifests or lockfiles, expose secrets, contact an external system, or mutate an environment without authorization.
- Runtime behavior cannot be traced to declared resolved configuration.
- Preflight permits expensive work to begin before required configuration, dependencies, tools, or platform constraints are validated.
- Reproducibility or target compatibility cannot be assessed with available evidence.
- Installed-tool behavior and authoritative current documentation conflict or cannot be reconciled safely.

Report the trigger, evidence, affected configuration or environment, impact, and minimum decision or authorization required. Do not silently repair the condition.

## Output contract

When this skill is the primary for the task, produce these sections and own the top-level verdict and report. When it is composed under another primary skill, contribute them as one labeled subsection or findings block in that skill's report and do not emit a second top-level verdict:

1. `VERDICT`: exactly one verdict and a one-sentence rationale.
2. `MODE AND SCOPE`: selected mode, objective, allowed scope, entry points, target environments, and exclusions.
3. `CONFIGURATION MODEL`: sources, keys, types, requirements, defaults, precedence, environment-variable overrides, validation, runtime consumers, and provenance behavior.
4. `ENVIRONMENT MODEL`: runtimes, packages, executables, manifests, lockfiles, installation procedure, operating-system and hardware constraints, and external state.
5. `PARITY FINDINGS`: schema/runtime key mapping, ignored or undocumented settings, hardcoded values, default divergence, and runtime behavior conclusions.
6. `INSTALLATION AND REPRODUCIBILITY`: clean starting state, declared setup, global assumptions, lock integrity, reconstruction evidence, and limitations.
7. `TOOL AND VERSION EVIDENCE`: discovery results, selected identities, versions, capabilities, preflight behavior, and unverified requirements.
8. `VALIDATION EVIDENCE`: commands actually run, exit statuses, concise results, commands not run, reasons, environment, and impact.
9. `FINDINGS`: blocking findings and non-blocking warnings with category, location, evidence, consequence, and minimum resolution; write `none` for empty categories.
10. `NEXT STEP`: the minimum correction, validation, authorization, or integration action supported by the verdict.

Do not report a command, platform, version, installation, or runtime path as verified unless the supporting evidence was actually inspected or executed.

## Allowed actions

- Read the task prompt, project instructions, profiles, overlays, configuration, schemas, runtime code, manifests, lockfiles, installation guidance, logs, provenance, and validation material within scope.
- Run local read-only inspection and explicitly authorized safe validation commands.
- Query installed tools for identity, version, capabilities, and help when doing so has no prohibited side effect.
- Compare declared configuration, resolved values, runtime use, dependency state, and target constraints.
- Propose corrections or validation work without applying them unless separately authorized.
- Report findings, uncertainty, unavailable checks, and the minimum authorization or evidence needed.

## Forbidden actions

- Install, upgrade, downgrade, remove, or resolve dependencies without explicit current-prompt authorization.
- Modify configuration, dependency manifests, lockfiles, environments, global state, or external systems without explicit authorization.
- Treat a passing parse, schema, import, discovery, build, or smoke check as proof of runtime parity or reproducibility.
- Accept a schema-valid but runtime-ignored configuration key.
- Invent supported platforms, versions, defaults, precedence, installation steps, or compatibility promises.
- Claim operating-system or hardware compatibility without checking relevant target constraints.
- Conceal hidden defaults, stale locks, missing tools, version mismatches, unrun validation, or undeclared global assumptions.
- Log secrets or expose private paths merely to improve provenance.
- Rely on cached software-behavior summaries when installed-tool inspection or authoritative current documentation is necessary.
- Broaden scope or silently repair findings during an audit.

## Verdict vocabulary
When composed under another primary skill, report this as a component status under that skill's findings, not as the task's top-level verdict.

- `CONFIG_ENV_READY`: Configuration, runtime behavior, dependencies, tools, installation, target compatibility, and provenance satisfy the applicable contracts with sufficient evidence and no remaining warnings.
- `CONFIG_ENV_READY_WITH_WARNINGS`: No blocking finding remains, but substantiated non-blocking limitations, environmental gaps, or residual risks are explicitly reported.
- `NEEDS_REVISION`: One or more correctable blocking configuration, environment, installation, parity, or provenance findings prevent acceptance.
- `NOT_REPRODUCIBLE`: Available evidence demonstrates that the required environment or setup cannot be reconstructed reliably under the current contracts.
- `BLOCKED`: Missing inputs, inaccessible evidence, unsafe conditions, or unavailable essential validation prevent a reliable conclusion.
- `OUT_OF_SCOPE`: The requested audit, installation, environment action, or material component exceeds the authorized scope.

When several verdicts apply, use `OUT_OF_SCOPE` for unauthorized scope, `BLOCKED` when evidence cannot support a conclusion, `NOT_REPRODUCIBLE` for demonstrated reconstruction failure, and `NEEDS_REVISION` for correctable blocking findings. Use a ready verdict only when no blocking finding remains and evidence is sufficient for the selected mode.
