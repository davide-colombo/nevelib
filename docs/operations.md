# Operations

## Environment setup

`pyproject.toml` is the only dependency and build authority. It requires Python 3.11 or
newer and defines the `dev` extra used for testing. This repository has no lock or
constraints file, so an environment is not reproducible merely because its packages meet
the declared ranges.

Creating or changing an environment requires explicit authorization. When authorized, use
an isolated environment and install the repository with:

    python3 -m pip install -e '.[dev]'

Do not install runtime bioinformatics executables through the Python dependency set. Record
their executable paths and versions with any scientific run.

## Validation

From the repository root, in the declared existing environment:

    PYTHONDONTWRITEBYTECODE=1 python3 -m pytest

Tests discover from `src/nevelib/tests`. Read the applicable test guidance before running
them. Route pytest base temporary files, the operating-system temporary directory, caches,
coverage output, build output, and tool logs to a fresh task-owned scratch directory when
the governing task requires isolation. Do not claim the complete suite passed when tests
were excluded or skipped; report the exact selection and counts.

External-tool calls in unit tests are mocked. A real executable or end-to-end run is a
separate integration or production action and needs its own authorization and recorded
inputs, configuration, tool versions, output location, and acceptance checks.

Agent-configuration structure can be checked without canonical source parity using:

    python3 scripts/validate_agent_configuration.py

Full generated-skill parity additionally requires an explicitly supplied clean canonical
source checkout at the commit pinned by `.agents/skills-manifest.json`. See
`agent-configuration.md`. Never run skill synchronization merely to make validation pass.

## Running commands

The six installed commands each accept one YAML configuration path. Start from the sample
configuration shipped beside the corresponding package, choose output directories outside
source and authoritative data, and validate every input/reference path before execution.
Capture the configuration, nevelib source or release identity, Python package inventory,
external-tool versions, input/reference digests, command status, and output inventory for a
scientific run.

An output directory may contain partial files after interruption or tool failure. Do not
infer completion from directory presence. Resume or overwrite behavior is module-specific;
inspect the implementation and existing artifacts before retrying. Preserve unexplained
partial state until an authorized recovery decision is made.

## Release evidence

The version in `pyproject.toml` is the package version authority. A release claim also needs
a matching immutable tag or published release artifact; an unreleased commit that retains
the same package version is not the tagged release. Before release work, verify the exact
commit, clean working state, tag absence, build inventory, tests, citation metadata, and
configured destination. Publishing, tagging, pushing, or changing dependencies always
requires separate authorization.

The repository currently declares an MIT license and project URLs in `pyproject.toml`. No
software Digital Object Identifier is declared; do not invent one.

## Safety boundaries

Production execution, remote access, data transfer, dependency or environment mutation,
destructive cleanup, Git integration, tag creation, and release publication are distinct
actions. Authorization for source edits or local tests does not authorize any of them.
Keep private machine paths, host bindings, credentials, and transient run state in an
ignored local overlay or external run record, not in committed documentation.
