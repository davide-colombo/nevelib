# nevelib agent guidance

nevelib is a Python 3.11+ bioinformatics library for read preparation, assembly,
homology search, clustering, multiple sequence alignment, and mapping. nexteveApp
depends on `nevelib>=0.6.0` and imports library modules directly, including modules
whose names begin with an underscore.

## Start here

- Read `.agents/PROJECT_PROFILE.md` before task-specific work.
- Read `.agents-local/PROJECT_PROFILE.local.md` only when it exists.
- Use `README.md` for the public module and command overview.
- Use `docs/architecture.md`, `docs/contracts.md`, and `docs/operations.md` as the
  maintained technical authorities.
- Use `docs/agent-configuration.md` for generated-skill validation and update rules.
- For multi-hour work, create and maintain a self-contained plan under `plans/`
  following `PLANS.md`.
- Follow the closest nested `AGENTS.md`; test-specific rules are in
  `src/nevelib/tests/AGENTS.md`.

## Commands and boundaries

`pyproject.toml` is authoritative for supported Python, dependencies, entry points,
and pytest discovery. When separately authorized, setup uses
`pip install -e .[dev]`. Run the test suite from the repository root with
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest`. Route temporary output and caches away
from source and authoritative result locations.

Keep diffs minimal. Preserve public APIs, deterministic output schemas, sequence
identifier rules, coordinate conventions, strand semantics, and the distinction
between a valid empty result and an input or tool failure. Do not install external
bioinformatics tools implicitly.

Environment changes, Git integration, releases, remote access, data transfer,
destructive operations, and production work each require explicit authorization.
Do not edit generated `.agents/skills` or `.claude/skills` payloads manually.

## Code Review Rules

- Review the complete diff and the direct producer, caller, consumer, and test oracle.
- Treat nexteveApp compatibility as a public contract, including imported underscore
  modules; identify any required coordinated consumer change.
- Reject silent reinterpretation of missing, malformed, or failed input as biological
  absence or valid emptiness.
- Check FASTA identifiers, BLAST and pairwise mapping coordinates, strand, table
  columns, row identity, missing values, and deterministic ordering where affected.
- Require a focused regression that fails for the pre-change behavior and asserts the
  corrected public result or error; do not accept execution-only assertions.
- Report unrun checks, environment drift, and unresolved scientific impact before
  routine implementation detail.
