# nevelib public project profile

## Identity and layout

nevelib is a Python `>=3.11` alpha shared library. `src/nevelib` contains the six
module families: reads, assembly, search, clustering, multiple sequence alignment,
and mapping. Tests live under `src/nevelib/tests`. `pyproject.toml` is authoritative
for the version, dependencies, command entry points, and pytest discovery.

The root `AGENTS.md` is the short instruction map. Maintained technical authorities
are `docs/architecture.md`, `docs/contracts.md`, `docs/operations.md`, and
`docs/agent-configuration.md`. Multi-hour work uses a repository-local plan following
`PLANS.md`.

## Setup and validation

Package installation and environment changes require authorization. The documented
setup command is `pip install -e .[dev]`; normal validation is
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest`. Resolve `python3` to an inspected
project environment before running it. Runtime wrappers require their documented
bioinformatics executables on `PATH`; do not install them implicitly.

## Compatibility contracts

nexteveApp declares `nevelib>=0.6.0` and imports FASTA, configuration, tool, BLAST,
and clustering interfaces, including modules whose names begin with an underscore.
Preserve public APIs, exception and valid-empty behavior, and table schemas. FASTA
record identifiers are the first whitespace-delimited header token. Pairwise mApping
Format coordinates are zero-based and end-exclusive. BLAST hits retain normalized
ascending subject coordinates with derived strand. Cluster assignment ordering is
deterministic. Inspect direct producers, callers, consumers, and test oracles before
changing these contracts.

## Data and action boundaries

Sample YAML files are tracked examples; configured inputs and outputs are external to
the source tree. Use maintained real-schema fixtures and keep outputs, scratch, caches,
and logs out of authoritative source locations. Report commands, evidence,
compatibility impact, environment drift, and skipped validation. Git integration or
release, remote access, transfer, destructive work, production work, and environment
mutation require explicit task authorization.

The sole permitted project rule file is `.codex/rules/repository-safety.rules`. It is
an additive restriction surface and contains no permissive decisions. Any other
project `.codex` rule or automation path remains prohibited by
`scripts/validate_agent_configuration.py`. Rule changes require decision tests;
Codex may require repository trust and a restart before a new rule is loaded.

## Skill policy

The manifest selects the generated skills discoverable in `.agents/skills` and mirrored
in `.claude/skills`. Do not edit or expand those generated payloads manually. Optional
and operational procedures remain outside ordinary repository discovery. This
repository uses its self-contained root `PLANS.md` workflow rather than adding an
unmanifested exec-plans skill.
