# Agent configuration

The selected generated skills are pinned in `.agents/skills-manifest.json`. Codex
discovers `.agents/skills`; Claude Code discovers identical copies in `.claude/skills`.
Never edit either generated tree manually.

All commands below run from the `nevelib` repository root. `<CANONICAL_SKILLS_REPOSITORY>`
is a local checkout of the canonical skill source (`agentic-engineering-skills`) at its
own repository root; it is read from, never written to.

Use `python3 scripts/sync_agent_skills.py --check --source <CANONICAL_SKILLS_REPOSITORY>`
to verify parity. An explicit `--sync` replaces selected generated directories only
after checking the manifest pin. Run
`python3 scripts/validate_agent_configuration.py --source <CANONICAL_SKILLS_REPOSITORY>`
for structural and source-parity validation.

`.agents-local/PROJECT_PROFILE.local.md` is optional and ignored. Copy the tracked
example locally only when machine-specific bindings are needed; do not commit it.

## Project rule boundary

The only permitted project rule is `.codex/rules/repository-safety.rules`. It is an
additive restriction surface: it contains `prompt` and `forbidden` decisions, never an
`allow` decision. `scripts/validate_agent_configuration.py` rejects every other file
under `.codex/rules`. For that exact file, it parses the policy without executing it,
requires at least one literal `prefix_rule` call, accepts only literal `prompt` or
`forbidden` decisions, and rejects empty, comment-only, dynamic, or otherwise executable
policy content. Existing prohibitions on project configuration, hooks, agents, and MCP
declarations remain in force. Test representative rule decisions with `codex execpolicy
check` before relying on the file. Project trust and a Codex restart may be required
before a newly installed rule is loaded.

Long-running work follows the self-contained repository plan specification in
`../PLANS.md`. It is intentionally separate from the generated skill inventory, so the
manifest and generated Codex and Claude skill payloads remain unchanged.

## Canonical source cleanliness

`--check --source` and `--sync` both require the canonical source's Git index and
working tree to be clean (no staged, tracked-modified, deleted, renamed, or untracked
non-ignored entries). A dirty source fails immediately and is never read further, so
no content is ever copied from an uncommitted canonical state. Files matched by the
canonical repository's own `.gitignore` do not count as dirty.

## Full vs. local-only validation

`validate_agent_configuration.py` prints one of three unambiguous, machine-matchable
results as its last line of stdout:

- `PASS_FULL_SOURCE_PARITY_VERIFIED` -- `--source` was supplied and canonical identity,
  cleanliness, exact pinned commit, and generated-copy parity were all verified.
- `PASS_LOCAL_STRUCTURE_SOURCE_PARITY_UNAVAILABLE` -- no `--source` was given. Local
  structure, manifest schema, the publishable-surface leakage scan, and Markdown links
  all passed, but source parity was never checked. This is a legitimate result for a
  contributor without the canonical checkout; it is not evidence that generated copies
  match the canonical commit.
- `FAIL` -- one or more checks failed.

Both `PASS_*` states exit `0`; only `FAIL` exits nonzero. Release, synchronization, and
source-drift validation must supply `--source`; ordinary local development does not need
to.

## Transactional synchronization

`--sync` stages the complete new Codex tree, the complete new Claude tree, and the new
manifest under a repository-local `.nevelib-agent-sync/` transaction directory (same
filesystem as the live destinations, so publication can use atomic renames; git-ignored)
and fully validates the staged content before touching any live path. It then backs up
the current Codex tree, Claude tree, and manifest, publishes Codex, then Claude, then the
manifest last (the manifest is the source of truth `--check` trusts, so it is never
published before the trees it describes), and re-validates the live result. Any handled
failure restores all three from their backups and verifies the restoration before
removing the transaction directory. A concurrent or interrupted synchronization is
detected via the same directory acting as an exclusive lock (`os.mkdir`, atomic on a
single POSIX or Windows filesystem): ordinary `--check`/`--sync` refuse to run while it
exists, instead of guessing at a possibly half-published state.

If a synchronization is ever interrupted by a hard process kill (not a handled
exception -- those already roll back automatically), `.nevelib-agent-sync/` is left
behind and blocks further `--check`/`--sync` until an explicit
`python3 scripts/sync_agent_skills.py --recover` restores the last verified prior state
from the retained backups and re-validates it. Recovery is refused, not silently
skipped, and it never deletes content outside the managed skill directories and the
manifest.

## Digest and generated-file policy

Skill-tree digests cover, for every regular file, its normalized POSIX-relative path,
entry type, a portable mode (`0644`, or `0755` if any executable bit is set -- no other
permission bits are recorded), its byte length, and its bytes, framed unambiguously so
no filename/content boundary can collide. Symlinks and special files (sockets, FIFOs,
devices) are rejected wherever they appear, in the canonical source, in generated trees,
or during staging. Empty directories are not part of the generated-skill contract: the
synchronizer only creates directories that are ancestors of actual files, and an
unexpected empty directory anywhere in a scanned tree fails validation. Canonical source
empty directories are never observed because Git cannot track them; this is a documented
limitation of Git, not a gap in the digest contract.

Canonical skill Markdown may cross-reference sibling skills that exist in the full
canonical registry but were not selected for this repository's partial local mirror;
such cross-skill-directory links are relative to the registry, not the local mirror, and
are intentionally out of scope for this repository's Markdown link validation.
