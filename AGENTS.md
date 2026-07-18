# nevelib agent guidance

nevelib is a shared Python 3.11+ bioinformatics library for reads, assembly,
search, clustering, MSA, and mapping. Preserve public APIs and output contracts:
nexteveApp depends on `nevelib>=0.6.0` and imports library modules directly.

Read `.agents/PROJECT_PROFILE.md` before task-specific work. Read
`.agents-local/PROJECT_PROFILE.local.md` only if it exists. Use the installed
skills; do not duplicate their procedures.

Keep changes minimal and add focused regression tests. FASTA identifiers are the
first whitespace-delimited header token. PAF coordinates are zero-based,
end-exclusive; preserve strand and normalized BLAST-coordinate semantics.
Clustering and serialized table schemas must remain deterministic and compatible.
Distinguish a valid empty result from an input/tool failure; do not silently change
formats, dependencies, or external-tool behavior.

`pyproject.toml` is authoritative for supported Python and test discovery.
When separately authorized, setup follows `pip install -e .[dev]`; validate with
`PYTHONDONTWRITEBYTECODE=1 python3 -m pytest`.
External bioinformatics executables are runtime prerequisites, not dependencies to
install implicitly. Keep generated outputs, temporary files, caches, and tool logs
outside source and authoritative result locations.

Environment changes, Git integration or release work, remote access, data transfer,
destructive operations, and production work each require separate authorization.
