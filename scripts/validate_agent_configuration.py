#!/usr/bin/env python3
"""Validate nevelib's public agent-configuration surface, stdlib-only.

Result states are explicit and never conflated:

  PASS_FULL_SOURCE_PARITY_VERIFIED             -- local checks passed AND
                                                   --source was supplied and
                                                   canonical-source identity,
                                                   cleanliness, exact commit,
                                                   and generated-copy parity
                                                   were all verified.
  PASS_LOCAL_STRUCTURE_SOURCE_PARITY_UNAVAILABLE -- local/structural checks
                                                   passed but no --source was
                                                   given, so source parity was
                                                   never checked. This is a
                                                   legitimate, intentionally
                                                   degraded result for a
                                                   contributor without the
                                                   canonical checkout -- it is
                                                   NOT evidence that generated
                                                   copies match the canonical
                                                   commit. Release, sync, and
                                                   source-drift validation
                                                   must supply --source.
  FAIL                                          -- one or more checks failed.

Both PASS_* states exit 0; FAIL exits 1.
"""
from __future__ import annotations

import argparse
import json
import re
import stat
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sync_agent_skills as synclib  # noqa: E402

EXPECTED_SKILLS = {
    "agent-output-verification-and-claim-audit", "bioinformatics-sequence-output-audit",
    "classification-and-grouping-audit", "code-review-and-test-audit",
    "configuration-and-environment-integrity", "evidence-citation-discipline",
    "minimal-diff-implementation-discipline", "output-contract-and-table-schema-audit",
    "read-only-audit-protocol", "repo-state-audit", "scientific-data-integrity-audit",
    "test-fixture-and-regression-design", "token-efficient-repository-inspection",
}
EXPECTED_OPTIONAL = {
    "cross-session-handoff-and-continuity", "prompt-crafting-for-coding-agents",
    "task-dossier-lifecycle", "pipeline-stage-contract-audit",
    "manifest-checksum-and-provenance", "hardware-aware-parallelism",
    "resumable-pipeline-design",
}
EXPECTED_OPERATIONAL = {
    "remote-execution-safety", "production-run-launch-and-monitoring",
    "git-integration-and-release-workflow", "data-transfer-and-integrity",
    "failure-recovery-and-rerun-planning", "large-output-root-hygiene",
}

# Obfuscated concatenation so this file's own source never trips its own scan.
PRIVATE_MARKERS = (
    "/" + "Users/", "BEGIN " + "PRIVATE " + "KEY", "pass" + "word=",
    "tok" + "en=", "ssh" + "://", "/" + "mnt/",
)
# Clearly synthetic placeholders such as <LOCAL_ENVIRONMENT> or
# <SIBLING_APPLICATION_CHECKOUT> are masked out (the bracketed token only,
# never surrounding text) before marker matching, so a real absolute path
# immediately following a placeholder still fails.
_PLACEHOLDER_RE = re.compile(r"<[A-Z][A-Z0-9_]*>")

_TEXT_SAMPLE_BYTES = 8192
_MAX_FULL_SCAN_BYTES = 1_048_576  # 1 MiB

_REQUIRED_FILES = (
    "AGENTS.md", "CLAUDE.md", ".agents/PROJECT_PROFILE.md",
    ".agents/skills-manifest.json", ".agents-local/PROJECT_PROFILE.local.md.example",
    "src/nevelib/AGENTS.md", "src/nevelib/tests/AGENTS.md",
)

_FORBIDDEN_EXACT = {
    ".codex/config.toml", ".codex/hooks.json", ".mcp.json", ".codex/mcp.json",
}
_FORBIDDEN_PREFIXES = (
    ".codex/agents", ".codex/rules", ".codex/hooks",
    ".githooks", ".agents/rules", ".claude/agents",
)

_MD_LINK_RE = re.compile(r"\[[^\]]*\]\(([^)]+)\)")


class Result:
    PASS_FULL = "PASS_FULL_SOURCE_PARITY_VERIFIED"
    PASS_LOCAL = "PASS_LOCAL_STRUCTURE_SOURCE_PARITY_UNAVAILABLE"
    FAIL = "FAIL"


def _check_required_files() -> list[str]:
    errors: list[str] = []
    for rel in _REQUIRED_FILES:
        path = ROOT / rel
        if not path.is_file():
            errors.append(f"missing required file: {rel}")
        elif path.name == "AGENTS.md" and len(path.read_bytes()) > 4096:
            errors.append(f"instruction too large: {rel}")
    claude_md = ROOT / "CLAUDE.md"
    if claude_md.is_file() and len(claude_md.read_bytes()) >= 1024:
        errors.append("CLAUDE.md is not minimal")
    return errors


def _check_manifest_and_policy() -> list[str]:
    try:
        manifest = synclib.load_manifest()
    except (OSError, json.JSONDecodeError, synclib.DuplicateKeyError) as exc:
        return [f"cannot read manifest: {exc}"]
    errors = synclib.validate_manifest_schema(manifest)
    if errors:
        return errors
    if manifest.get("canonical_repository") != "agentic-engineering-skills":
        errors.append("invalid manifest pin: canonical_repository")
    if (
        set(manifest.get("skills", {})) != EXPECTED_SKILLS
        or set(manifest.get("optional_uninstalled_skills", {})) != EXPECTED_OPTIONAL
        or set(manifest.get("excluded_operational_skills", {})) != EXPECTED_OPERATIONAL
    ):
        errors.append("skill classification set differs from approved policy")
    for name, data in manifest.get("skills", {}).items():
        if data.get("classification") != "DEFAULT_DISCOVERABLE" or data.get("invocation_policy") != "ALLOW_IMPLICIT":
            errors.append(f"installed skill has non-default policy: {name}")
    return errors


def _git_ls(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", *args],
        capture_output=True, text=True, check=True,
    )
    return [p for p in result.stdout.split("\0") if p]


def _publishable_surface() -> tuple[set[str], set[str]]:
    tracked = set(_git_ls(["--cached"]))
    untracked = set(_git_ls(["--others", "--exclude-standard"]))
    return tracked, untracked


def _check_forbidden_project_config(tracked: set[str], untracked: set[str]) -> list[str]:
    errors: list[str] = []
    for rel in sorted(tracked | untracked):
        if rel in _FORBIDDEN_EXACT:
            errors.append(f"prohibited project automation file is present: {rel}")
            continue
        rel_path = Path(rel)
        for prefix in _FORBIDDEN_PREFIXES:
            prefix_path = Path(prefix)
            if rel_path == prefix_path or rel_path.is_relative_to(prefix_path):
                errors.append(f"prohibited project automation path is present: {rel}")
                break
    hooks_dir = ROOT / ".git" / "hooks"
    if hooks_dir.is_dir():
        for entry in sorted(hooks_dir.iterdir()):
            if entry.is_file() and not entry.name.endswith(".sample") and entry.stat().st_mode & 0o111:
                errors.append(f"active git hook script is present: .git/hooks/{entry.name}")
    return errors


def _classify_file(path: Path) -> str:
    st = path.lstat()
    if stat.S_ISLNK(st.st_mode):
        return "symlink"
    if not stat.S_ISREG(st.st_mode):
        return "special"
    with path.open("rb") as handle:
        sample = handle.read(_TEXT_SAMPLE_BYTES)
    if b"\0" in sample:
        return "binary"
    return "text"


def _mask_placeholders(text: str) -> str:
    return _PLACEHOLDER_RE.sub("", text)


def _scan_publishable_surface() -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    tracked, untracked = _publishable_surface()
    surface = sorted(tracked | untracked)

    errors.extend(_check_forbidden_project_config(tracked, untracked))

    overlay = ".agents-local/PROJECT_PROFILE.local.md"
    overlay_example = ".agents-local/PROJECT_PROFILE.local.md.example"
    if overlay in tracked:
        errors.append(f"private overlay is tracked and must not be: {overlay}")
    # The example counterpart must be part of the publishable surface (tracked,
    # or untracked-but-not-ignored while this configuration foundation is still
    # uncommitted) and must not itself be excluded by an ignore rule.
    if overlay_example not in tracked and overlay_example not in untracked:
        errors.append(f"private-overlay example is neither tracked nor publishable: {overlay_example}")
    gitignore_path = ROOT / ".gitignore"
    if gitignore_path.is_file():
        gitignore_text = gitignore_path.read_text(encoding="utf-8")
        if not re.search(r"^\.agents-local/PROJECT_PROFILE\.local\.md$", gitignore_text, re.M):
            errors.append("private overlay is not ignored by .gitignore")
    else:
        errors.append("missing required file: .gitignore")

    root_resolved = ROOT.resolve()
    for rel in surface:
        path = ROOT / rel
        try:
            resolved = path.resolve()
            resolved.relative_to(root_resolved)
        except (OSError, ValueError):
            errors.append(f"publishable entry escapes repository root: {rel}")
            continue
        kind = _classify_file(path)
        if kind == "symlink":
            errors.append(f"symlink is not permitted in the publishable surface: {rel}")
            continue
        if kind == "special":
            errors.append(f"special (non-regular) file is not permitted in the publishable surface: {rel}")
            continue
        size = path.stat().st_size
        if kind == "binary":
            warnings.append(f"binary file: {rel} ({size} bytes)")
            continue
        if size > _MAX_FULL_SCAN_BYTES:
            warnings.append(f"large text file skipped: {rel} ({size} bytes)")
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            warnings.append(f"non-UTF-8 text-like file skipped: {rel}")
            continue
        masked = _mask_placeholders(text)
        for marker in PRIVATE_MARKERS:
            if marker in masked:
                errors.append(f"private marker in {rel}")
                break
    return errors, warnings


def _extract_heading_slugs(text: str) -> set[str]:
    slugs: set[str] = set()
    for line in text.splitlines():
        match = re.match(r"^#{1,6}\s+(.*)$", line)
        if match:
            heading = match.group(1).strip()
            slug = re.sub(r"[^\w\- ]", "", heading).strip().lower().replace(" ", "-")
            slugs.add(slug)
    return slugs


def _generated_skill_root(md_path: Path) -> Path | None:
    """The skill directory containing md_path, if it lies under a generated
    .agents/skills/<name>/ or .claude/skills/<name>/ tree; else None."""
    for skills_root in (ROOT / ".agents" / "skills", ROOT / ".claude" / "skills"):
        try:
            relative = md_path.relative_to(skills_root)
        except ValueError:
            continue
        return skills_root / relative.parts[0]
    return None


def _is_generated_cross_registry_link(
    md_path: Path, target_path_part: str, resolved: Path,
) -> bool:
    skill_root = _generated_skill_root(md_path)
    if skill_root is None:
        return False
    target_parts = Path(target_path_part).parts
    if (
        len(target_parts) != 3
        or target_parts[0] != ".."
        or target_parts[2] != "SKILL.md"
        or not synclib._SKILL_NAME_RE.fullmatch(target_parts[1])
    ):
        return False
    try:
        relative = resolved.relative_to(skill_root.parent.resolve())
    except ValueError:
        return False
    return bool(relative.parts) and relative.parts[0] != skill_root.name


def _check_markdown_links(tracked: set[str], untracked: set[str]) -> tuple[list[str], int]:
    errors: list[str] = []
    checked = 0
    markdown_paths = sorted(
        rel for rel in tracked | untracked if Path(rel).suffix.lower() == ".md"
    )
    for rel in markdown_paths:
        md_path = ROOT / rel
        if _classify_file(md_path) != "text":
            continue
        try:
            text = md_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        checked += 1
        for match in _MD_LINK_RE.finditer(text):
            target = match.group(1).strip()
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            target_path_part, _, anchor = target.partition("#")
            if not target_path_part:
                continue
            resolved = (md_path.parent / target_path_part).resolve()
            if _is_generated_cross_registry_link(md_path, target_path_part, resolved):
                continue
            if not resolved.exists():
                errors.append(f"broken relative link in {md_path.relative_to(ROOT)}: {target}")
                continue
            if anchor and resolved.suffix == ".md":
                slugs = _extract_heading_slugs(resolved.read_text(encoding="utf-8"))
                if anchor.lower() not in slugs:
                    errors.append(f"broken anchor in {md_path.relative_to(ROOT)}: {target}")
    return errors, checked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source")
    args = parser.parse_args()

    errors: list[str] = []
    warnings: list[str] = []

    errors.extend(_check_required_files())
    errors.extend(_check_manifest_and_policy())
    scan_errors, scan_warnings = _scan_publishable_surface()
    errors.extend(scan_errors)
    warnings.extend(scan_warnings)
    tracked, untracked = _publishable_surface()
    link_errors, markdown_count = _check_markdown_links(tracked, untracked)
    errors.extend(link_errors)

    source_path = synclib.source_root(args.source)
    sync_cmd = [sys.executable, str(ROOT / "scripts" / "sync_agent_skills.py"), "--check"]
    if source_path is not None:
        sync_cmd += ["--source", str(source_path)]
    sync_result = subprocess.run(sync_cmd, cwd=ROOT, capture_output=True, text=True)
    if sync_result.returncode:
        stderr_lines = [line for line in sync_result.stderr.splitlines() if line.strip()]
        if stderr_lines:
            errors.extend(f"sync check: {line}" for line in stderr_lines)
        else:
            errors.append("skill synchronization check failed")

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)
    print(f"INFO: publishable Markdown files checked: {markdown_count}", file=sys.stderr)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)

    if errors:
        print(Result.FAIL)
        return 1
    if source_path is not None:
        print(Result.PASS_FULL)
        return 0
    print(Result.PASS_LOCAL)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
