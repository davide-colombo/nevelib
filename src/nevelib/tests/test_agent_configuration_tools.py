"""Tests for scripts/sync_agent_skills.py and scripts/validate_agent_configuration.py.

Every fixture builds a synthetic canonical "skills" repository and a synthetic
nevelib-shaped checkout under pytest's tmp_path; both scripts are physically
copied (never imported from or pointed at the real checkout) so ROOT resolves
inside the throwaway tree and no test can touch the real nevelib or
agentic-engineering-skills checkouts. Black-box tests drive the scripts as
subprocesses; a handful of transaction/digest tests load a fresh copy of the
module in-process via importlib so failures can be injected with monkeypatch
at named seams (_stage_skill, _publish_client, _publish_manifest) without any
production-only CLI flag.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path
from typing import Iterable

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SYNC_SCRIPT = REPO_ROOT / "scripts" / "sync_agent_skills.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_agent_configuration.py"
REPOSITORY_SAFETY_RULE = REPO_ROOT / ".codex" / "rules" / "repository-safety.rules"

SKILLS = ("agent-output-verification-and-claim-audit", "code-review-and-test-audit")

REAL_SKILLS = (
    "agent-output-verification-and-claim-audit", "bioinformatics-sequence-output-audit",
    "classification-and-grouping-audit", "code-review-and-test-audit",
    "configuration-and-environment-integrity", "evidence-citation-discipline",
    "minimal-diff-implementation-discipline", "output-contract-and-table-schema-audit",
    "read-only-audit-protocol", "repo-state-audit", "scientific-data-integrity-audit",
    "test-fixture-and-regression-design", "token-efficient-repository-inspection",
)
REAL_OPTIONAL = (
    "cross-session-handoff-and-continuity", "hardware-aware-parallelism",
    "manifest-checksum-and-provenance", "pipeline-stage-contract-audit",
    "prompt-crafting-for-coding-agents", "resumable-pipeline-design", "task-dossier-lifecycle",
)
REAL_OPERATIONAL = (
    "data-transfer-and-integrity", "failure-recovery-and-rerun-planning",
    "git-integration-and-release-workflow", "large-output-root-hygiene",
    "production-run-launch-and-monitoring", "remote-execution-safety",
)

DEFAULT_IDENTITY = "github.com/example-owner/agentic-engineering-skills"

_GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Test", "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test", "GIT_COMMITTER_EMAIL": "test@example.com",
    "GIT_CONFIG_NOSYSTEM": "1",
}


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True, env=_GIT_ENV)


# --------------------------------------------------------------------------
# Fixture architecture
# --------------------------------------------------------------------------

class CanonicalRepo:
    def __init__(self, path: Path) -> None:
        self.path = path

    def commit(self, message: str = "update") -> str:
        _git("add", "-A", cwd=self.path)
        _git("commit", "-m", message, cwd=self.path)
        return self.head

    @property
    def head(self) -> str:
        return _git("rev-parse", "HEAD", cwd=self.path).stdout.strip()


class CheckoutRepo:
    def __init__(self, path: Path) -> None:
        self.path = path

    def run_sync(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.path / "scripts" / "sync_agent_skills.py"), *args],
            cwd=self.path, capture_output=True, text=True,
        )

    def run_validate(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(self.path / "scripts" / "validate_agent_configuration.py"), *args],
            cwd=self.path, capture_output=True, text=True,
        )


def make_canonical(
    tmp_path: Path, skill_names: Iterable[str], *,
    repo_name: str = "agentic-engineering-skills", include_registry_markers: bool = True,
) -> CanonicalRepo:
    repo_dir = tmp_path / repo_name
    repo_dir.mkdir()
    _git("init", "-q", cwd=repo_dir)
    if include_registry_markers:
        (repo_dir / "scripts").mkdir()
        (repo_dir / "scripts" / "validate_skills.py").write_text("# stub canonical validator\n")
        (repo_dir / "tests").mkdir()
        (repo_dir / "tests" / "test_validate_skills.py").write_text("# stub canonical test suite\n")
    skills_dir = repo_dir / "skills"
    skills_dir.mkdir()
    for name in skill_names:
        skill_dir = skills_dir / name
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"# {name}\n\nUse when the {name} situation arises.\n")
    (repo_dir / ".gitignore").write_text("ignored.tmp\n")
    repo = CanonicalRepo(repo_dir)
    repo.commit("initial")
    return repo


_AGENTS_MD = "# nevelib agent guidance\n\nSee [PROJECT_PROFILE](.agents/PROJECT_PROFILE.md).\n"
_NESTED_AGENTS_MD = "# nested guidance\n"
_CLAUDE_MD = "# Claude Code adapter\n\nRead AGENTS.md.\n"
_PROFILE_MD = "# project profile\n"
_OVERLAY_EXAMPLE_MD = "# Local overlay (example only)\n\n- Path: `<LOCAL_ENVIRONMENT>`\n"
_README_MD = "# demo\n\nSee [docs](docs/agent-configuration.md).\n"
_DOCS_MD = "# agent configuration\n\nSee [AGENTS.md](../AGENTS.md).\n"
_GITIGNORE = "__pycache__/\n.agents-local/PROJECT_PROFILE.local.md\n.nevelib-agent-sync/\n"


def _base_manifest(canonical: CanonicalRepo, skills: list[str], extra_manifest: dict | None) -> dict:
    manifest = {
        "schema_version": 2,
        "canonical_repository": canonical.path.name,
        "canonical_repository_identity": DEFAULT_IDENTITY,
        "canonical_source_commit": canonical.head,
        "skills": {
            n: {"classification": "DEFAULT_DISCOVERABLE", "invocation_policy": "ALLOW_IMPLICIT",
                "private_binding_may_be_required": False}
            for n in skills
        },
        "generated_skills": {},
        "optional_uninstalled_skills": {},
        "excluded_operational_skills": {},
        "excluded_not_relevant_skills": {},
        "update_policy": "Run sync only with an explicit source and an exact matching canonical commit.",
    }
    if extra_manifest:
        manifest.update(extra_manifest)
    return manifest


def full_policy_extra_manifest() -> dict:
    return {
        "optional_uninstalled_skills": {
            n: {"classification": "OPTIONAL_ON_DEMAND", "invocation_policy": "EXPLICIT_ONLY"} for n in REAL_OPTIONAL
        },
        "excluded_operational_skills": {
            n: {"classification": "DO_NOT_INSTALL", "invocation_policy": "EXPLICIT_ONLY"} for n in REAL_OPERATIONAL
        },
    }


def make_checkout(
    tmp_path: Path, canonical: CanonicalRepo, skill_names: Iterable[str], *,
    name: str = "nevelib-checkout", pre_synced: bool = False, commit: bool = False,
    extra_manifest: dict | None = None,
) -> CheckoutRepo:
    checkout_dir = tmp_path / name
    checkout_dir.mkdir()
    _git("init", "-q", cwd=checkout_dir)

    (checkout_dir / "scripts").mkdir()
    shutil.copy2(SYNC_SCRIPT, checkout_dir / "scripts" / "sync_agent_skills.py")
    shutil.copy2(VALIDATE_SCRIPT, checkout_dir / "scripts" / "validate_agent_configuration.py")

    (checkout_dir / "AGENTS.md").write_text(_AGENTS_MD)
    (checkout_dir / "CLAUDE.md").write_text(_CLAUDE_MD)
    (checkout_dir / ".agents").mkdir(exist_ok=True)
    (checkout_dir / ".agents" / "PROJECT_PROFILE.md").write_text(_PROFILE_MD)
    (checkout_dir / ".agents-local").mkdir(exist_ok=True)
    (checkout_dir / ".agents-local" / "PROJECT_PROFILE.local.md.example").write_text(_OVERLAY_EXAMPLE_MD)
    (checkout_dir / "README.md").write_text(_README_MD)
    (checkout_dir / "docs").mkdir(exist_ok=True)
    (checkout_dir / "docs" / "agent-configuration.md").write_text(_DOCS_MD)
    (checkout_dir / "src" / "nevelib" / "tests").mkdir(parents=True, exist_ok=True)
    (checkout_dir / "src" / "nevelib" / "AGENTS.md").write_text(_NESTED_AGENTS_MD)
    (checkout_dir / "src" / "nevelib" / "tests" / "AGENTS.md").write_text(_NESTED_AGENTS_MD)
    (checkout_dir / ".gitignore").write_text(_GITIGNORE)

    skills = sorted(skill_names)
    manifest = _base_manifest(canonical, skills, extra_manifest)
    (checkout_dir / ".agents" / "skills-manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n"
    )
    (checkout_dir / ".agents" / "skills").mkdir(exist_ok=True)
    (checkout_dir / ".claude").mkdir(exist_ok=True)
    (checkout_dir / ".claude" / "skills").mkdir(exist_ok=True)

    checkout = CheckoutRepo(checkout_dir)
    if pre_synced:
        result = checkout.run_sync("--sync", "--source", str(canonical.path))
        assert result.returncode == 0, result.stderr
    if commit:
        _git("add", "-A", cwd=checkout_dir)
        _git("commit", "-m", "initial", cwd=checkout_dir)
    return checkout


def _snapshot(root: Path) -> dict[str, tuple[int, str]]:
    result: dict[str, tuple[int, str]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            rel = path.relative_to(root).as_posix()
            st = path.stat()
            result[rel] = (stat.S_IMODE(st.st_mode), hashlib.sha256(path.read_bytes()).hexdigest())
    return result


def _load_module_from(script_path: Path, module_name: str):
    # A unique module_name per call avoids collisions across tests that each
    # load their own throwaway copy of the script.
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    module = importlib.util.module_from_spec(spec)
    # Registering in sys.modules before exec is required here: the module uses
    # `from __future__ import annotations` plus @dataclasses.dataclass, and
    # dataclass's own annotation resolution looks the module up via
    # sys.modules[cls.__module__] while the class body executes.
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)  # type: ignore[union-attr]
    finally:
        del sys.modules[module_name]
    return module


def _load_sync_module(checkout: CheckoutRepo):
    return _load_module_from(checkout.path / "scripts" / "sync_agent_skills.py", "sync_under_test")


def _load_bare_sync_module():
    return _load_module_from(SYNC_SCRIPT, "sync_bare")


# --------------------------------------------------------------------------
# SYNC-001: canonical source cleanliness and identity
# --------------------------------------------------------------------------

def test_sync_check_accepts_clean_source(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_sync_check_rejects_dirty_tracked_source(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    skill_file = canonical.path / "skills" / SKILLS[0] / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "\nmutated\n")
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "not clean" in result.stderr


def test_sync_check_rejects_staged_uncommitted_change(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    skill_file = canonical.path / "skills" / SKILLS[0] / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "\nstaged change\n")
    _git("add", "-A", cwd=canonical.path)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "not clean" in result.stderr


def test_sync_check_rejects_untracked_nonignored_source_file(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (canonical.path / "stray.txt").write_text("stray\n")
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "not clean" in result.stderr


def test_sync_check_permits_ignored_source_file(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (canonical.path / "ignored.tmp").write_text("scratch\n")
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr


def test_sync_check_rejects_wrong_source_commit(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (canonical.path / "skills" / SKILLS[0] / "SKILL.md").write_text("# updated\nnew content\n")
    canonical.commit("advance")
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "commit does not match" in result.stderr


def test_sync_check_rejects_wrong_source_identity(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS, include_registry_markers=False)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "registry structure" in result.stderr


def test_sync_check_rejects_mismatched_origin_identity(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    _git("remote", "add", "origin", "git@github.com:someone-else/different-repo.git", cwd=canonical.path)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "origin identity does not match" in result.stderr


def test_sync_check_rejects_missing_selected_skill(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, list(SKILLS) + ["not-in-canonical"])
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "missing source skill" in result.stderr


def test_sync_check_rejects_source_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    (canonical.path / "skills" / SKILLS[0] / "linked.md").symlink_to("SKILL.md")
    canonical.commit("add symlink")
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "symlink" in result.stderr


def test_sync_check_rejects_canonical_source_root_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    source_link = tmp_path / "canonical-link"
    source_link.symlink_to(canonical.path, target_is_directory=True)
    result = checkout.run_sync("--check", "--source", str(source_link))
    assert result.returncode != 0
    assert "canonical source root must not be a symlink" in result.stderr


def test_sync_rejects_canonical_source_root_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    source_link = tmp_path / "canonical-link"
    source_link.symlink_to(canonical.path, target_is_directory=True)
    result = checkout.run_sync("--sync", "--source", str(source_link))
    assert result.returncode != 0
    assert "canonical source root must not be a symlink" in result.stderr


def test_sync_check_rejects_canonical_selected_skill_root_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    skill_root = canonical.path / "skills" / SKILLS[0]
    replacement = canonical.path / "source-skill-replacement"
    skill_root.rename(replacement)
    skill_root.symlink_to("../source-skill-replacement", target_is_directory=True)
    canonical.commit("replace source skill root with symlink")
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "canonical source skill root" in result.stderr
    assert "must not be a symlink" in result.stderr


def test_sync_check_rejects_generated_codex_skill_root_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    skill_root = checkout.path / ".agents" / "skills" / SKILLS[0]
    replacement = checkout.path / "codex-skill-replacement"
    skill_root.rename(replacement)
    skill_root.symlink_to("../../codex-skill-replacement", target_is_directory=True)
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "codex generated skill root" in result.stderr
    assert "must not be a symlink" in result.stderr


def test_sync_check_rejects_generated_claude_skill_root_symlink(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    skill_root = checkout.path / ".claude" / "skills" / SKILLS[0]
    replacement = checkout.path / "claude-skill-replacement"
    skill_root.rename(replacement)
    skill_root.symlink_to("../../claude-skill-replacement", target_is_directory=True)
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "claude generated skill root" in result.stderr
    assert "must not be a symlink" in result.stderr


def test_sync_check_rejects_source_path_with_symlinked_parent(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    parent_link = tmp_path / "canonical-parent-link"
    parent_link.symlink_to(tmp_path, target_is_directory=True)
    result = checkout.run_sync("--check", "--source", str(parent_link / canonical.path.name))
    assert result.returncode != 0
    assert "symlinked parent component" in result.stderr


# --------------------------------------------------------------------------
# General/regression: generated-tree, manifest, and unrelated-content checks
# --------------------------------------------------------------------------

def test_check_rejects_generated_source_divergence(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    generated_file = checkout.path / ".agents" / "skills" / SKILLS[0] / "SKILL.md"
    generated_file.write_text(generated_file.read_text() + "\nmanually edited\n")
    claude_file = checkout.path / ".claude" / "skills" / SKILLS[0] / "SKILL.md"
    claude_file.write_text(claude_file.read_text() + "\nmanually edited\n")
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode != 0
    assert "differs from source" in result.stderr


def test_check_rejects_codex_claude_mismatch(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    claude_file = checkout.path / ".claude" / "skills" / SKILLS[0] / "SKILL.md"
    claude_file.write_text(claude_file.read_text() + "\ndiverged\n")
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "Codex and Claude copies differ" in result.stderr


def test_check_rejects_unknown_skill_directory_without_deleting_it(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    stray = checkout.path / ".agents" / "skills" / "stray-skill"
    stray.mkdir()
    (stray / "SKILL.md").write_text("# stray\n")
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "unrecognized generated directory" in result.stderr
    assert stray.is_dir()


def test_sync_preserves_unrelated_agents_content(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    unrelated = checkout.path / ".agents" / "unrelated.txt"
    unrelated.write_text("keep me\n")
    result = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    assert unrelated.read_text() == "keep me\n"


def test_sync_preserves_unrelated_claude_content(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    unrelated = checkout.path / ".claude" / "unrelated.txt"
    unrelated.write_text("keep me too\n")
    result = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    assert unrelated.read_text() == "keep me too\n"


def test_check_detects_executable_mode_drift(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    target = checkout.path / ".agents" / "skills" / SKILLS[0] / "SKILL.md"
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    result = checkout.run_sync("--check")
    assert result.returncode != 0


def test_check_rejects_special_file_in_generated_tree(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    fifo_path = checkout.path / ".agents" / "skills" / SKILLS[0] / "pipe"
    os.mkfifo(fifo_path)
    try:
        result = checkout.run_sync("--check")
        assert result.returncode != 0
        assert "unsafe entries" in result.stderr
    finally:
        fifo_path.unlink()


def test_check_rejects_manifest_source_path_traversal(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    manifest_path = checkout.path / ".agents" / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["generated_skills"][SKILLS[0]]["canonical_source_path"] = "../../etc/passwd"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "escapes skills" in result.stderr


def test_check_rejects_manifest_destination_path_traversal(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    manifest_path = checkout.path / ".agents" / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["generated_skills"][SKILLS[0]]["codex_destination"] = "/etc/passwd"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = checkout.run_sync("--check")
    assert result.returncode != 0
    assert "escapes .agents/skills" in result.stderr


# --------------------------------------------------------------------------
# SYNC-002: transactional publish, rollback, interruption, concurrency
# --------------------------------------------------------------------------

def test_sync_pristine_source_succeeds(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    result = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    for client in (".agents", ".claude"):
        for name in SKILLS:
            assert (checkout.path / client / "skills" / name / "SKILL.md").is_file()
    assert not (checkout.path / ".nevelib-agent-sync").exists()


def test_sync_is_idempotent_on_repeat(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    first = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert first.returncode == 0, first.stderr
    manifest_before = (checkout.path / ".agents" / "skills-manifest.json").read_text()
    second = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert second.returncode == 0, second.stderr
    manifest_after = (checkout.path / ".agents" / "skills-manifest.json").read_text()
    assert manifest_before == manifest_after


def test_sync_check_mode_mutates_no_files_or_mtimes(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    before = _snapshot(checkout.path)
    result = checkout.run_sync("--check", "--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    assert _snapshot(checkout.path) == before


def test_sync_injected_failure_before_publication_leaves_live_state_unchanged(tmp_path, monkeypatch):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    module = _load_sync_module(checkout)
    before = _snapshot(checkout.path)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("injected: staging failure")

    monkeypatch.setattr(module, "_stage_skill", _boom)
    errors = module.sync(canonical.path)
    assert errors
    assert not (checkout.path / ".nevelib-agent-sync").exists()
    assert _snapshot(checkout.path) == before


def test_sync_injected_failure_after_first_client_restores_both_clients(tmp_path, monkeypatch):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    module = _load_sync_module(checkout)
    before = _snapshot(checkout.path)
    real_publish_client = module._publish_client
    calls = {"n": 0}

    def _flaky(label, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise RuntimeError("injected: second client publish failure")
        return real_publish_client(label, *args, **kwargs)

    monkeypatch.setattr(module, "_publish_client", _flaky)
    errors = module.sync(canonical.path)
    assert errors
    assert calls["n"] == 2  # confirms the first client really did publish before injection fired
    assert not (checkout.path / ".nevelib-agent-sync").exists()
    assert _snapshot(checkout.path) == before


def test_sync_injected_manifest_failure_restores_clients_and_manifest(tmp_path, monkeypatch):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    module = _load_sync_module(checkout)
    before = _snapshot(checkout.path)

    def _boom(*_args, **_kwargs):
        raise RuntimeError("injected: manifest publish failure")

    monkeypatch.setattr(module, "_publish_manifest", _boom)
    errors = module.sync(canonical.path)
    assert errors
    assert not (checkout.path / ".nevelib-agent-sync").exists()
    assert _snapshot(checkout.path) == before


def test_sync_interrupted_transaction_detected_and_recovery_restores_prior_state(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    before = _snapshot(checkout.path)

    # Simulate a hard crash mid-publication: the first client's skill
    # directory has already been evicted to its backup slot (exactly what
    # _publish_client does before placing the replacement), and the
    # transaction directory is left behind without completing.
    tx_root = checkout.path / ".nevelib-agent-sync"
    backups = tx_root / "backups" / "codex"
    backups.mkdir(parents=True)
    live_skill = checkout.path / ".agents" / "skills" / SKILLS[0]
    shutil.move(str(live_skill), str(backups / SKILLS[0]))
    (tx_root / "journal.json").write_text(json.dumps({"phase": "CODEX_PUBLISHED"}))

    blocked_check = checkout.run_sync("--check")
    assert blocked_check.returncode != 0
    assert "--recover" in blocked_check.stderr

    blocked_sync = checkout.run_sync("--sync", "--source", str(canonical.path))
    assert blocked_sync.returncode != 0
    assert "--recover" in blocked_sync.stderr

    recovered = checkout.run_sync("--recover")
    assert recovered.returncode == 0, recovered.stderr
    assert not tx_root.exists()
    assert _snapshot(checkout.path) == before

    clean_check = checkout.run_sync("--check", "--source", str(canonical.path))
    assert clean_check.returncode == 0, clean_check.stderr


def test_sync_recover_rejects_symlinked_transaction_root(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    before = _snapshot(checkout.path)
    external = tmp_path / "external-transaction"
    external.mkdir()
    tx_root = checkout.path / ".nevelib-agent-sync"
    tx_root.symlink_to(external, target_is_directory=True)
    recovered = checkout.run_sync("--recover")
    assert recovered.returncode != 0
    assert "transaction root must not be a symlink" in recovered.stderr
    assert _snapshot(checkout.path) == before


def test_sync_concurrent_invocation_is_rejected(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)
    tx_root = checkout.path / ".nevelib-agent-sync"
    tx_root.mkdir()  # a held lock, exactly as a genuinely concurrent sync would leave it
    try:
        result = checkout.run_sync("--sync", "--source", str(canonical.path))
        assert result.returncode != 0
        assert "--recover" in result.stderr
    finally:
        tx_root.rmdir()


# --------------------------------------------------------------------------
# SYNC-003: canonical tree digest
# --------------------------------------------------------------------------

def test_digest_tree_detects_executable_bit_change(tmp_path):
    module = _load_bare_sync_module()
    root = tmp_path / "tree"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    digest_before = module.tree_digest(root)
    (root / "a.txt").chmod(0o755)
    digest_after = module.tree_digest(root)
    assert digest_before != digest_after


def test_digest_tree_distinguishes_empty_directory_presence(tmp_path):
    module = _load_bare_sync_module()
    root = tmp_path / "tree"
    root.mkdir()
    (root / "a.txt").write_text("hello")
    (root / "empty").mkdir()
    with pytest.raises(module.EmptyDirectoryError):
        module.tree_digest(root)


def test_digest_tree_rejects_special_file(tmp_path):
    module = _load_bare_sync_module()
    root = tmp_path / "tree"
    root.mkdir()
    os.mkfifo(root / "pipe")
    with pytest.raises(module.UnsafeTreeError):
        module.tree_digest(root)


def test_digest_tree_framing_disambiguates_name_content_boundary(tmp_path):
    module = _load_bare_sync_module()
    root_a = tmp_path / "a"
    root_a.mkdir()
    (root_a / "ab").write_text("cd")
    root_b = tmp_path / "b"
    root_b.mkdir()
    (root_b / "a").write_text("bcd")
    assert module.tree_digest(root_a) != module.tree_digest(root_b)


# --------------------------------------------------------------------------
# VAL-001: explicit full vs. degraded local-only result states
# --------------------------------------------------------------------------

def test_validate_full_pass_with_clean_source(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest()
    )
    result = checkout.run_validate("--source", str(canonical.path))
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PASS_FULL_SOURCE_PARITY_VERIFIED"


def test_validate_no_source_result_is_explicitly_degraded(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest()
    )
    full = checkout.run_validate("--source", str(canonical.path))
    local = checkout.run_validate()
    assert full.returncode == 0, full.stderr
    assert local.returncode == 0, local.stderr
    assert full.stdout.strip() != local.stdout.strip()
    assert local.stdout.strip() == "PASS_LOCAL_STRUCTURE_SOURCE_PARITY_UNAVAILABLE"
    assert "PASS_FULL_SOURCE_PARITY_VERIFIED" not in local.stdout


# --------------------------------------------------------------------------
# VAL-002: publishable-surface enumeration, leakage, overlay, manifest,
# automation-artifact, and Markdown-link checks
# --------------------------------------------------------------------------

def test_validate_missing_required_file_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "CLAUDE.md").unlink()
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "missing required file: CLAUDE.md" in result.stderr


def test_validate_malformed_manifest_json_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / ".agents" / "skills-manifest.json").write_text("{not valid json")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "cannot read manifest" in result.stderr


def test_validate_unknown_manifest_field_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    manifest_path = checkout.path / ".agents" / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["unexpected_field"] = "surprise"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "unknown top-level field" in result.stderr


def test_validate_missing_selected_skill_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS)  # not synced: skill not installed
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "missing generated skill" in result.stderr


def test_validate_installed_operational_skill_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    manifest_path = checkout.path / ".agents" / "skills-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["skills"][SKILLS[0]]["invocation_policy"] = "EXPLICIT_ONLY"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "non-default policy" in result.stderr


def test_validate_codex_claude_mismatch_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    claude_file = checkout.path / ".claude" / "skills" / SKILLS[0] / "SKILL.md"
    claude_file.write_text(claude_file.read_text() + "\nmismatch\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "sync check:" in result.stderr


def test_validate_generated_canonical_mismatch_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    for client in (".agents", ".claude"):
        generated_file = checkout.path / client / "skills" / SKILLS[0] / "SKILL.md"
        generated_file.write_text(generated_file.read_text() + "\ndrift\n")
    result = checkout.run_validate("--source", str(canonical.path))
    assert result.returncode != 0
    assert "differs from source" in result.stderr


def test_validate_wrong_canonical_commit_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (canonical.path / "skills" / SKILLS[0] / "SKILL.md").write_text("# advanced\n")
    canonical.commit("advance")
    result = checkout.run_validate("--source", str(canonical.path))
    assert result.returncode != 0
    assert "commit does not match" in result.stderr


def test_validate_dirty_canonical_source_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (canonical.path / "stray.txt").write_text("oops\n")
    result = checkout.run_validate("--source", str(canonical.path))
    assert result.returncode != 0
    assert "not clean" in result.stderr


def test_validate_private_absolute_path_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "leak.md").write_text("secret path " + "/" + "Users/someone/data\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in leak.md" in result.stderr


def test_validate_credential_url_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "leak.md").write_text("remote is " + "ssh" + "://git@example.com/repo\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in leak.md" in result.stderr


def test_validate_private_key_marker_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "leak.md").write_text("-----" + "BEGIN " + "PRIVATE " + "KEY" + "-----\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in leak.md" in result.stderr


def test_validate_safe_placeholder_passes(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "notes.md").write_text("Local scratch: `<LOCAL_SCRATCH_ROOT>`\n")
    result = checkout.run_validate()
    assert "private marker in notes.md" not in result.stderr


def test_validate_tracked_private_overlay_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    overlay = checkout.path / ".agents-local" / "PROJECT_PROFILE.local.md"
    overlay.write_text("repo: " + "/" + "Users/real/path\n")
    _git("add", "-f", str(overlay), cwd=checkout.path)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private overlay is tracked" in result.stderr


def test_validate_ignored_private_overlay_permitted(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    overlay = checkout.path / ".agents-local" / "PROJECT_PROFILE.local.md"
    overlay.write_text("repo: " + "/" + "Users/real/path\n")
    result = checkout.run_validate()
    assert "private overlay is tracked" not in result.stderr
    assert "private marker in .agents-local/PROJECT_PROFILE.local.md" not in result.stderr


def test_validate_example_accidentally_ignored_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    gitignore = checkout.path / ".gitignore"
    gitignore.write_text(gitignore.read_text() + "\n.agents-local/PROJECT_PROFILE.local.md.example\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "neither tracked nor publishable" in result.stderr


def test_validate_overlay_not_ignored_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    gitignore = checkout.path / ".gitignore"
    gitignore.write_text(gitignore.read_text().replace(".agents-local/PROJECT_PROFILE.local.md\n", ""))
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private overlay is not ignored" in result.stderr


def test_validate_suspicious_tracked_file_matching_ignore_rules_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    leak = checkout.path / "build" / "leak.md"
    leak.parent.mkdir()
    leak.write_text("secret " + "/" + "Users/tracked/leak\n")
    _git("add", "-f", str(leak), cwd=checkout.path)
    _git("commit", "-m", "add tracked leak under a soon-to-be-ignored dir", cwd=checkout.path)
    gitignore = checkout.path / ".gitignore"
    gitignore.write_text(gitignore.read_text() + "\nbuild/\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in build/leak.md" in result.stderr


def test_validate_suspicious_untracked_nonignored_file_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "scratch.md").write_text("tok" + "en=abc123\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in scratch.md" in result.stderr


def test_validate_suspicious_content_in_validator_source_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    validator = checkout.path / "scripts" / "validate_agent_configuration.py"
    validator.write_text(validator.read_text() + "\n# leaked: " + "/" + "Users/someone/secret\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in scripts/validate_agent_configuration.py" in result.stderr


def test_validate_binary_file_explicitly_classified(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / "blob.bin").write_bytes(b"\x00\x01binary\x00data")
    result = checkout.run_validate()
    assert "binary file: blob.bin" in result.stderr
    assert "private marker in blob.bin" not in result.stderr


def test_validate_symlink_in_generated_tree_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    target = checkout.path / ".agents" / "skills" / SKILLS[0] / "SKILL.md"
    link = checkout.path / ".agents" / "skills" / SKILLS[0] / "linked.md"
    link.symlink_to(target)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "sync check:" in result.stderr


def test_validate_executable_mode_drift_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    target = checkout.path / ".agents" / "skills" / SKILLS[0] / "SKILL.md"
    target.chmod(target.stat().st_mode | stat.S_IXUSR)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "sync check:" in result.stderr


def test_validate_broken_markdown_link_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    readme = checkout.path / "README.md"
    readme.write_text(readme.read_text() + "\n[broken](docs/does-not-exist.md)\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link in README.md" in result.stderr


def _make_full_policy_checkout(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest(),
    )
    return canonical, checkout


def test_validate_tracked_listed_markdown_with_valid_link_passes(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr


def test_validate_tracked_arbitrary_markdown_with_valid_link_passes(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    document = checkout.path / "notes.md"
    document.write_text("[guidance](AGENTS.md)\n")
    _git("add", str(document), cwd=checkout.path)
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr


def test_validate_tracked_arbitrary_markdown_with_broken_link_fails(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    document = checkout.path / "notes.md"
    document.write_text("[broken](missing.md)\n")
    _git("add", str(document), cwd=checkout.path)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link in notes.md" in result.stderr


def test_validate_untracked_publishable_markdown_with_broken_link_fails(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    (checkout.path / "unlisted.md").write_text("[broken](missing.md)\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link in unlisted.md" in result.stderr


def test_validate_tracked_ignored_markdown_with_broken_link_fails(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    document = checkout.path / "build" / "notes.md"
    document.parent.mkdir()
    document.write_text("[broken](missing.md)\n")
    _git("add", "-f", str(document), cwd=checkout.path)
    gitignore = checkout.path / ".gitignore"
    gitignore.write_text(gitignore.read_text() + "\nbuild/\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link in build/notes.md" in result.stderr


def test_validate_ignored_untracked_private_markdown_is_not_checked(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    overlay = checkout.path / ".agents-local" / "PROJECT_PROFILE.local.md"
    overlay.write_text("[private](missing.md)\n")
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr


def test_validate_external_markdown_link_is_not_fetched(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    document = checkout.path / "external.md"
    document.write_text("[external](https://example.invalid/never-fetched)\n")
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr


def test_validate_generated_cross_registry_link_is_permitted(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    skill_file = canonical.path / "skills" / REAL_SKILLS[0] / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "\n[sibling](../not-selected/SKILL.md)\n")
    canonical.commit("add cross-registry skill link")
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest(),
    )
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr


def test_validate_unrelated_broken_generated_skill_link_fails(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    skill_file = canonical.path / "skills" / REAL_SKILLS[0] / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "\n[broken](missing.md)\n")
    canonical.commit("add broken generated skill link")
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest(),
    )
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link" in result.stderr


def test_validate_broken_generated_sibling_non_skill_link_fails(tmp_path):
    canonical = make_canonical(tmp_path, REAL_SKILLS)
    skill_file = canonical.path / "skills" / REAL_SKILLS[0] / "SKILL.md"
    skill_file.write_text(skill_file.read_text() + "\n[broken](../not-selected/missing.md)\n")
    canonical.commit("add broken generated sibling link")
    checkout = make_checkout(
        tmp_path, canonical, REAL_SKILLS, pre_synced=True, extra_manifest=full_policy_extra_manifest(),
    )
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link" in result.stderr


def test_validate_uppercase_publishable_markdown_with_broken_link_fails(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    (checkout.path / "notes.MD").write_text("[broken](missing.md)\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "broken relative link in notes.MD" in result.stderr


def test_validate_markdown_symlink_fails_under_publishable_surface_policy(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    document = checkout.path / "linked.md"
    document.symlink_to("README.md")
    _git("add", str(document), cwd=checkout.path)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "symlink is not permitted in the publishable surface: linked.md" in result.stderr


def test_validate_project_codex_config_toml_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    codex_dir = checkout.path / ".codex"
    codex_dir.mkdir()
    (codex_dir / "config.toml").write_text("[core]\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "prohibited project automation file is present: .codex/config.toml" in result.stderr


def test_validate_hook_artifact_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    hooks_dir = checkout.path / ".codex" / "hooks"
    hooks_dir.mkdir(parents=True)
    (hooks_dir / "pre-tool.sh").write_text("#!/bin/sh\necho hi\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "prohibited project automation path is present: .codex/hooks/pre-tool.sh" in result.stderr


def test_validate_repository_safety_rule_is_permitted(tmp_path):
    _, checkout = _make_full_policy_checkout(tmp_path)
    rules_dir = checkout.path / ".codex" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "repository-safety.rules").write_bytes(REPOSITORY_SAFETY_RULE.read_bytes())
    result = checkout.run_validate()
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "PASS_LOCAL_STRUCTURE_SOURCE_PARITY_UNAVAILABLE"


@pytest.mark.parametrize(
    "contents",
    ["", "# comment-only policy\n"],
    ids=["empty", "comment-only"],
)
def test_validate_repository_safety_rule_requires_a_rule(tmp_path, contents):
    _, checkout = _make_full_policy_checkout(tmp_path)
    rules_dir = checkout.path / ".codex" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "repository-safety.rules").write_text(contents)
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "repository safety rule must define at least one valid prefix_rule" in result.stderr


@pytest.mark.parametrize(
    ("decision", "message"),
    [
        ('"allow"', "decision must be literal 'prompt' or 'forbidden'"),
        ("choose_decision()", "all values must be literal"),
    ],
    ids=["allow", "dynamic"],
)
def test_validate_repository_safety_rule_rejects_nonrestrictive_policy(
    tmp_path, decision, message
):
    _, checkout = _make_full_policy_checkout(tmp_path)
    rules_dir = checkout.path / ".codex" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "repository-safety.rules").write_text(
        "prefix_rule(\n"
        "    pattern=[\"example-command\"],\n"
        f"    decision={decision},\n"
        "    justification=\"test policy\",\n"
        "    match=[\"example-command\"],\n"
        ")\n"
    )
    result = checkout.run_validate()
    assert result.returncode != 0
    assert message in result.stderr


def test_validate_unexpected_rule_artifact_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    rules_dir = checkout.path / ".codex" / "rules"
    rules_dir.mkdir(parents=True)
    (rules_dir / "policy.md").write_text("# rule\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "prohibited project automation path is present: .codex/rules/policy.md" in result.stderr


def test_validate_project_subagent_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    agents_dir = checkout.path / ".claude" / "agents"
    agents_dir.mkdir(parents=True)
    (agents_dir / "custom.md").write_text("# custom subagent\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "prohibited project automation path is present: .claude/agents/custom.md" in result.stderr


def test_validate_mcp_declaration_fails(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    (checkout.path / ".mcp.json").write_text(json.dumps({"mcpServers": {}}))
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "prohibited project automation file is present: .mcp.json" in result.stderr


def test_validate_full_publishable_surface_not_hardcoded_list(tmp_path):
    canonical = make_canonical(tmp_path, SKILLS)
    checkout = make_checkout(tmp_path, canonical, SKILLS, pre_synced=True)
    outside = checkout.path / "some_new_top_level_dir" / "notes.md"
    outside.parent.mkdir()
    outside.write_text("tok" + "en=leaked-value\n")
    result = checkout.run_validate()
    assert result.returncode != 0
    assert "private marker in some_new_top_level_dir/notes.md" in result.stderr
