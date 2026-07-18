#!/usr/bin/env python3
"""Synchronize generated agent skills from an explicitly supplied canonical source.

Publication is transactional: both client trees (Codex, Claude) and the manifest
are staged and fully validated under a repository-local transaction directory
before any live path is touched, backed up before replacement, and rolled back
to the last verified prior state on any handled failure. An interrupted
transaction blocks ordinary --check/--sync until an explicit --recover is run.

Digest contract: a tree digest covers, for every regular file, its normalized
POSIX-relative path, entry type, a portable mode (0644 or 0755, derived solely
from the executable bit; no other permission bits are recorded), its byte
length, and its bytes -- framed unambiguously via length-prefixed records so no
delimiter-concatenation collision is possible. Symlinks and special files
(sockets, FIFOs, devices) are rejected wherever they are encountered. Empty
directories are not part of the generated-skill contract: the synchronizer only
creates directories that are ancestors of actual files, and an unexpected empty
directory anywhere in a scanned tree is a validation failure. Canonical source
empty directories are never observed because Git cannot track them; this is a
documented limitation, not a gap in the digest contract.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / ".agents" / "skills-manifest.json"
DESTINATIONS = {"codex": ROOT / ".agents" / "skills", "claude": ROOT / ".claude" / "skills"}

# Transaction staging/backup/lock area. Must live on the same filesystem as the
# live destinations so publication renames are atomic; therefore it lives inside
# the repository itself rather than under /tmp. It is git-ignored.
TX_ROOT = ROOT / ".nevelib-agent-sync"
JOURNAL_PATH = TX_ROOT / "journal.json"

MANIFEST_SCHEMA_VERSION = 2

_REGISTRY_MARKERS = ("skills", "scripts/validate_skills.py", "tests/test_validate_skills.py")

_TOP_LEVEL_FIELDS = {
    "schema_version", "canonical_repository", "canonical_repository_identity",
    "canonical_source_commit", "skills", "generated_skills",
    "optional_uninstalled_skills", "excluded_operational_skills",
    "excluded_not_relevant_skills", "update_policy",
}
_SKILL_ENTRY_FIELDS = {"classification", "invocation_policy", "private_binding_may_be_required"}
_CLASSIFICATION_MAP_FIELDS = {"classification", "invocation_policy"}
_GENERATED_ENTRY_FIELDS = {"canonical_source_path", "codex_destination", "claude_destination", "sha256"}
_CLASSIFICATIONS = {"DEFAULT_DISCOVERABLE", "OPTIONAL_ON_DEMAND", "DO_NOT_INSTALL"}
_INVOCATION_POLICIES = {"ALLOW_IMPLICIT", "EXPLICIT_ONLY", "CONDITIONAL_BY_PROJECT", "NOT_APPLICABLE"}
_SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTITY_RE = re.compile(r"^[a-z0-9.-]+/[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
_SSH_SHORTHAND_RE = re.compile(r"^[\w.-]+@(?P<host>[\w.-]+):(?P<path>.+)$")
_URL_RE = re.compile(r"^(?:ssh|https?)://(?:[^@/]+@)?(?P<host>[^/]+)/(?P<path>.+)$")


class GitError(RuntimeError):
    pass


class DuplicateKeyError(ValueError):
    pass


class UnsafeTreeError(RuntimeError):
    def __init__(self, entries: list[tuple[str, str]]) -> None:
        super().__init__(f"unsafe entries: {entries}")
        self.entries = entries


class EmptyDirectoryError(RuntimeError):
    def __init__(self, paths: list[str]) -> None:
        super().__init__(f"unexpected empty directories: {paths}")
        self.paths = paths


class EntryType:
    FILE = "file"
    DIR = "dir"
    SYMLINK = "symlink"
    SPECIAL = "special"


@dataclasses.dataclass
class TreeScan:
    files: list[Path]
    unsafe: list[tuple[str, str]]
    empty_dirs: list[str]


# --------------------------------------------------------------------------
# Git helpers
# --------------------------------------------------------------------------

def _run_git_raw(args: list[str]) -> str:
    try:
        result = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    except OSError as exc:
        raise GitError(str(exc)) from exc
    if result.returncode != 0:
        raise GitError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout


def run_git(args: list[str]) -> str:
    return _run_git_raw(args).strip()


def git_status_dirty_paths(repo: Path) -> list[str]:
    """Relative paths for every staged, tracked-modified, deleted, renamed, or
    untracked non-ignored entry. Ignored files are excluded by Git itself and
    never appear here."""
    raw = _run_git_raw(["-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=all"])
    tokens = raw.split("\0")
    if tokens and tokens[-1] == "":
        tokens.pop()
    paths: list[str] = []
    i = 0
    while i < len(tokens):
        entry = tokens[i]
        if len(entry) >= 3:
            status, path = entry[:2], entry[3:]
            paths.append(path)
            if status[0] in ("R", "C"):
                i += 1  # skip the following orig-path token emitted for renames/copies
        i += 1
    return paths


def get_git_origin_url(repo: Path) -> str | None:
    try:
        return run_git(["-C", str(repo), "remote", "get-url", "origin"])
    except GitError:
        return None


def normalize_git_origin_identity(url: str) -> str | None:
    """Normalize git@host:path shorthand, ssh-protocol, and https-protocol
    origin URLs that refer to the same repository to one lowercase
    'host/owner/repo' identity string."""
    url = url.strip()
    match = _SSH_SHORTHAND_RE.match(url) or _URL_RE.match(url)
    if not match:
        return None
    host = match.group("host").lower()
    path = match.group("path")
    if path.endswith(".git"):
        path = path[: -len(".git")]
    path = path.strip("/").lower()
    if not path or "/" not in path:
        return None
    return f"{host}/{path}"


# --------------------------------------------------------------------------
# Manifest loading and strict schema validation
# --------------------------------------------------------------------------

def _no_duplicate_keys(pairs: list[tuple[str, object]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_manifest_text(text: str) -> dict:
    return json.loads(text, object_pairs_hook=_no_duplicate_keys)


def load_manifest() -> dict:
    return load_manifest_text(MANIFEST_PATH.read_text(encoding="utf-8"))


def _validate_relative_containment(value: object, root: str, name: str) -> bool:
    if not isinstance(value, str) or not value:
        return False
    if value.startswith("/") or value.startswith("~") or "\\" in value:
        return False
    parts = value.split("/")
    if any(part in ("", ".", "..") for part in parts):
        return False
    expected_root = f"{root}/{name}"
    return value == expected_root or value.startswith(expected_root + "/")


def validate_manifest_schema(manifest: object) -> list[str]:
    errors: list[str] = []
    if not isinstance(manifest, dict):
        return ["manifest is not a JSON object"]

    unknown_top = set(manifest) - _TOP_LEVEL_FIELDS
    if unknown_top:
        errors.append(f"manifest has unknown top-level field(s): {', '.join(sorted(unknown_top))}")
    missing_top = _TOP_LEVEL_FIELDS - set(manifest)
    if missing_top:
        errors.append(f"manifest is missing required top-level field(s): {', '.join(sorted(missing_top))}")
        return errors

    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        errors.append(f"manifest schema_version must be {MANIFEST_SCHEMA_VERSION}")
    if not isinstance(manifest.get("canonical_repository"), str) or not manifest["canonical_repository"]:
        errors.append("canonical_repository must be a non-empty string")
    identity = manifest.get("canonical_repository_identity")
    if not isinstance(identity, str) or not _IDENTITY_RE.fullmatch(identity):
        errors.append("canonical_repository_identity must be a normalized host/owner/repo string")
    commit = manifest.get("canonical_source_commit")
    if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
        errors.append("canonical_source_commit must be a 40-character lowercase hex commit hash")
    if not isinstance(manifest.get("update_policy"), str) or not manifest["update_policy"]:
        errors.append("update_policy must be a non-empty string")

    all_names: dict[str, str] = {}

    def check_classification_map(field: str) -> None:
        value = manifest.get(field)
        if not isinstance(value, dict):
            errors.append(f"{field} must be a JSON object")
            return
        entry_fields = _SKILL_ENTRY_FIELDS if field == "skills" else _CLASSIFICATION_MAP_FIELDS
        required_fields = entry_fields if field == "skills" else _CLASSIFICATION_MAP_FIELDS
        for name, entry in value.items():
            if not _SKILL_NAME_RE.fullmatch(name):
                errors.append(f"{field}: invalid skill name '{name}'")
            if name in all_names:
                errors.append(f"duplicate skill name '{name}' in both {all_names[name]} and {field}")
            else:
                all_names[name] = field
            if not isinstance(entry, dict):
                errors.append(f"{field}[{name}] must be a JSON object")
                continue
            unknown = set(entry) - entry_fields
            if unknown:
                errors.append(f"{field}[{name}] has unknown field(s): {', '.join(sorted(unknown))}")
            missing = required_fields - set(entry)
            if field == "skills" and "private_binding_may_be_required" not in entry:
                missing = missing | {"private_binding_may_be_required"}
            if missing:
                errors.append(f"{field}[{name}] is missing field(s): {', '.join(sorted(missing))}")
            if entry.get("classification") not in _CLASSIFICATIONS:
                errors.append(f"{field}[{name}] has invalid classification")
            if entry.get("invocation_policy") not in _INVOCATION_POLICIES:
                errors.append(f"{field}[{name}] has invalid invocation_policy")
            if field == "skills" and not isinstance(entry.get("private_binding_may_be_required"), bool):
                errors.append(f"{field}[{name}].private_binding_may_be_required must be a boolean")

    for field in ("skills", "optional_uninstalled_skills", "excluded_operational_skills", "excluded_not_relevant_skills"):
        check_classification_map(field)

    generated = manifest.get("generated_skills")
    if not isinstance(generated, dict):
        errors.append("generated_skills must be a JSON object")
    else:
        # generated_skills may legitimately be a strict subset of skills (e.g.
        # before the very first --sync has ever run); completeness against the
        # live filesystem is check()'s job, not a schema-shape requirement.
        skills_names = set(manifest.get("skills") or {})
        unknown_generated = set(generated) - skills_names
        if unknown_generated:
            errors.append(f"generated_skills has entries outside the skills selection: {', '.join(sorted(unknown_generated))}")
        for name, entry in generated.items():
            if not isinstance(entry, dict):
                errors.append(f"generated_skills[{name}] must be a JSON object")
                continue
            unknown = set(entry) - _GENERATED_ENTRY_FIELDS
            if unknown:
                errors.append(f"generated_skills[{name}] has unknown field(s): {', '.join(sorted(unknown))}")
            missing = _GENERATED_ENTRY_FIELDS - set(entry)
            if missing:
                errors.append(f"generated_skills[{name}] is missing field(s): {', '.join(sorted(missing))}")
                continue
            if not _validate_relative_containment(entry["canonical_source_path"], "skills", name):
                errors.append(f"generated_skills[{name}].canonical_source_path escapes skills/{name}/")
            if not _validate_relative_containment(entry["codex_destination"], ".agents/skills", name):
                errors.append(f"generated_skills[{name}].codex_destination escapes .agents/skills/{name}/")
            if not _validate_relative_containment(entry["claude_destination"], ".claude/skills", name):
                errors.append(f"generated_skills[{name}].claude_destination escapes .claude/skills/{name}/")
            if not isinstance(entry["sha256"], str) or not _SHA256_RE.fullmatch(entry["sha256"]):
                errors.append(f"generated_skills[{name}].sha256 is not a 64-character lowercase hex digest")
    return errors


# --------------------------------------------------------------------------
# Entry classification and the canonical tree digest
# --------------------------------------------------------------------------

def classify_entry(path: Path) -> str:
    st = path.lstat()
    mode = st.st_mode
    if stat.S_ISLNK(mode):
        return EntryType.SYMLINK
    if stat.S_ISDIR(mode):
        return EntryType.DIR
    if stat.S_ISREG(mode):
        return EntryType.FILE
    return EntryType.SPECIAL


def normalized_mode(path: Path) -> int:
    st = path.lstat()
    return 0o755 if (st.st_mode & 0o111) else 0o644


def validated_directory_root(
    path: Path, label: str, *, contained_by: Path | None = None,
) -> tuple[Path | None, str | None]:
    """Validate a lexical directory root before resolving it."""
    lexical = Path(os.path.abspath(path))
    filesystem_root = Path(lexical.anchor)
    for parent in reversed(lexical.parents):
        if parent == filesystem_root:
            continue
        try:
            if stat.S_ISLNK(parent.lstat().st_mode):
                return None, f"{label} path contains a symlinked parent component"
        except OSError:
            break
    try:
        mode = lexical.lstat().st_mode
    except OSError:
        return None, f"{label} does not exist or is not a directory"
    if stat.S_ISLNK(mode):
        return None, f"{label} must not be a symlink"
    if not stat.S_ISDIR(mode):
        return None, f"{label} is not a directory"
    resolved = lexical.resolve(strict=True)
    if contained_by is not None:
        try:
            resolved.relative_to(contained_by)
        except ValueError:
            return None, f"{label} escapes its required parent directory"
    return resolved, None


def scan_tree(root: Path) -> TreeScan:
    root_type = classify_entry(root)
    if root_type != EntryType.DIR:
        return TreeScan(files=[], unsafe=[(".", root_type)], empty_dirs=[])
    resolved_root = root.resolve()
    files: list[Path] = []
    unsafe: list[tuple[str, str]] = []
    dirs_with_files: set[str] = set()
    all_dirs: list[str] = []
    for dirpath, dirnames, filenames in os.walk(resolved_root, followlinks=False):
        current = Path(dirpath)
        rel_dir = current.relative_to(resolved_root).as_posix()
        rel_dir = "" if rel_dir == "." else rel_dir
        all_dirs.append(rel_dir)
        kept_dirnames = []
        for dname in dirnames:
            dpath = current / dname
            if dpath.is_symlink():
                rel = dpath.relative_to(resolved_root).as_posix()
                unsafe.append((rel, EntryType.SYMLINK))
                continue
            kept_dirnames.append(dname)
        dirnames[:] = kept_dirnames
        for fname in filenames:
            fpath = current / fname
            rel = fpath.relative_to(resolved_root).as_posix()
            entry_type = classify_entry(fpath)
            if entry_type != EntryType.FILE:
                unsafe.append((rel, entry_type))
                continue
            files.append(fpath)
            marker = rel_dir
            while True:
                dirs_with_files.add(marker)
                if marker == "":
                    break
                marker = marker.rsplit("/", 1)[0] if "/" in marker else ""
    empty_dirs = sorted((d if d else ".") for d in all_dirs if d not in dirs_with_files)
    files.sort(key=lambda p: p.relative_to(resolved_root).as_posix())
    return TreeScan(files=files, unsafe=sorted(unsafe), empty_dirs=empty_dirs)


def tree_digest(root: Path) -> str:
    scan = scan_tree(root)
    if scan.unsafe:
        raise UnsafeTreeError(scan.unsafe)
    if scan.empty_dirs:
        raise EmptyDirectoryError(scan.empty_dirs)
    resolved_root = root.resolve()
    digest = hashlib.sha256()
    for file_path in scan.files:
        rel = file_path.relative_to(resolved_root).as_posix()
        mode = normalized_mode(file_path)
        data = file_path.read_bytes()
        header = json.dumps(
            {"path": rel, "type": "file", "mode": mode, "size": len(data)},
            sort_keys=True, separators=(",", ":"),
        ).encode("utf-8")
        digest.update(len(header).to_bytes(8, "big"))
        digest.update(header)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def safe_tree_digest(path: Path) -> tuple[str | None, list[str]]:
    try:
        return tree_digest(path), []
    except UnsafeTreeError as exc:
        detail = ", ".join(f"{rel} ({kind})" for rel, kind in exc.entries)
        return None, [f"unsafe entries present: {detail}"]
    except EmptyDirectoryError as exc:
        noun = "directory" if len(exc.paths) == 1 else "directories"
        return None, [f"unexpected empty {noun}: {', '.join(exc.paths)}"]


# --------------------------------------------------------------------------
# Canonical source trust model
# --------------------------------------------------------------------------

def source_root(value: str | None) -> Path | None:
    value = value or os.environ.get("NEVELIB_CANONICAL_SKILLS_SOURCE")
    return Path(os.path.abspath(value)) if value else None


def verify_source_identity(source: Path, manifest: dict) -> list[str]:
    source_root_path, root_error = validated_directory_root(source, "canonical source root")
    if root_error:
        return [root_error]
    assert source_root_path is not None
    try:
        top_level = run_git(["-C", str(source_root_path), "rev-parse", "--show-toplevel"])
    except GitError:
        return ["canonical source is not a Git worktree root"]
    if Path(top_level).resolve() != source_root_path:
        return ["canonical source path is not its Git top-level"]
    try:
        head = run_git(["-C", str(source_root_path), "rev-parse", "HEAD"])
    except GitError:
        return ["cannot read canonical source Git HEAD"]

    errors: list[str] = []
    if head != manifest.get("canonical_source_commit"):
        errors.append("canonical source commit does not match the manifest pin")
    missing_markers = [marker for marker in _REGISTRY_MARKERS if not (source_root_path / marker).exists()]
    if missing_markers:
        errors.append(
            "canonical source does not match the expected canonical registry structure: missing "
            + ", ".join(missing_markers)
        )
    expected_identity = manifest.get("canonical_repository_identity")
    origin_url = get_git_origin_url(source_root_path)
    if origin_url is not None:
        normalized = normalize_git_origin_identity(origin_url)
        if normalized is None:
            errors.append("canonical source origin URL could not be normalized for identity verification")
        elif expected_identity and normalized != expected_identity:
            errors.append("canonical source origin identity does not match the manifest pin")
    # When no origin is configured, exact-commit + registry-structure evidence
    # (already checked above) is the documented fallback identity mechanism.
    return errors


def verify_source_clean(source: Path) -> list[str]:
    try:
        dirty = git_status_dirty_paths(source)
    except GitError as exc:
        return [f"cannot read canonical source Git status: {exc}"]
    if not dirty:
        return []
    shown = sorted(set(dirty))
    display = ", ".join(shown[:20])
    if len(shown) > 20:
        display += f" (+{len(shown) - 20} more)"
    return [f"canonical source working tree is not clean: {display}"]


def verify_source(source: Path, manifest: dict) -> list[str]:
    """Single source preflight shared by --check --source and --sync: identity,
    then cleanliness (a dirty source is never read further, so no content is
    ever copied from it), then per-selected-skill existence and safety."""
    errors = verify_source_identity(source, manifest)
    if errors:
        return errors
    errors = verify_source_clean(source)
    if errors:
        return errors
    source_root_path = source.resolve(strict=True)
    skills_root, root_error = validated_directory_root(
        source_root_path / "skills", "canonical skills root", contained_by=source_root_path,
    )
    if root_error:
        return [root_error]
    assert skills_root is not None
    for name in sorted(manifest.get("skills", {})):
        lexical_skill_dir = skills_root / name
        if not lexical_skill_dir.exists() and not lexical_skill_dir.is_symlink():
            errors.append(f"missing source skill: {name}")
            continue
        skill_dir, skill_error = validated_directory_root(
            lexical_skill_dir, f"canonical source skill root '{name}'", contained_by=skills_root,
        )
        if skill_error:
            errors.append(skill_error)
            continue
        assert skill_dir is not None
        scan = scan_tree(skill_dir)
        for rel, kind in scan.unsafe:
            errors.append(f"{name}: canonical source {kind} is not allowed ({rel})")
    return errors


# --------------------------------------------------------------------------
# --check
# --------------------------------------------------------------------------

def validated_generated_roots() -> tuple[dict[str, Path], list[str]]:
    roots: dict[str, Path] = {}
    errors: list[str] = []
    for label, destination in DESTINATIONS.items():
        root, error = validated_directory_root(
            destination, f"{label} generated skills root", contained_by=ROOT,
        )
        if error:
            errors.append(error)
        else:
            assert root is not None
            roots[label] = root
    return roots, errors


def transaction_root_error() -> str | None:
    try:
        mode = TX_ROOT.lstat().st_mode
    except FileNotFoundError:
        return None
    if stat.S_ISLNK(mode):
        return "transaction root must not be a symlink"
    if not stat.S_ISDIR(mode):
        return "transaction root is not a directory"
    transaction_root = TX_ROOT.resolve(strict=True)
    backups = transaction_root / "backups"
    if backups.exists() or backups.is_symlink():
        backups_root, backup_error = validated_directory_root(
            backups, "transaction backup root", contained_by=transaction_root,
        )
        if backup_error:
            return backup_error
        assert backups_root is not None
        for label in DESTINATIONS:
            backup_dir = backups_root / label
            if not backup_dir.exists() and not backup_dir.is_symlink():
                continue
            _, backup_error = validated_directory_root(
                backup_dir, f"transaction {label} backup root", contained_by=backups_root,
            )
            if backup_error:
                return backup_error
        manifest_backup = backups_root / "manifest.json"
        if manifest_backup.exists() or manifest_backup.is_symlink():
            mode = manifest_backup.lstat().st_mode
            if stat.S_ISLNK(mode):
                return "transaction manifest backup must not be a symlink"
            if not stat.S_ISREG(mode):
                return "transaction manifest backup is not a regular file"
    return None


def check(source: Path | None) -> list[str]:
    transaction_error = transaction_root_error()
    if transaction_error:
        return [transaction_error]
    if TX_ROOT.exists():
        return ["an interrupted or in-progress synchronization transaction was detected; run --recover"]
    return _check_impl(source)


def _check_impl(source: Path | None) -> list[str]:
    try:
        manifest = load_manifest()
    except (OSError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return [f"cannot read manifest: {exc}"]
    errors = validate_manifest_schema(manifest)
    if errors:
        return errors

    selected = sorted(manifest["skills"])
    if source is not None:
        errors.extend(verify_source(source, manifest))
        if errors:
            return errors

    destinations, root_errors = validated_generated_roots()
    if root_errors:
        return root_errors

    for label, destination in destinations.items():
        for existing in destination.iterdir():
            if existing.is_dir() and existing.name not in selected:
                errors.append(f"{label}: unrecognized generated directory is present: {existing.name}")
    if errors:
        return errors

    generated = manifest.get("generated_skills", {})
    for name in selected:
        copies = {label: destination / name for label, destination in destinations.items()}
        present: dict[str, bool] = {}
        for label, path in copies.items():
            root, root_error = validated_directory_root(
                path, f"{label} generated skill root '{name}'", contained_by=destinations[label],
            )
            if root_error:
                errors.append(root_error)
                present[label] = False
            else:
                assert root is not None
                copies[label] = root
                present[label] = True
        if not any(present.values()):
            errors.append(f"missing generated skill: {name}")
            continue
        if not all(present.values()):
            missing = [label for label, ok in present.items() if not ok]
            errors.append(f"{name}: missing from {', '.join(missing)}")
            continue

        digests: dict[str, str] = {}
        for label, path in copies.items():
            digest, tree_errors = safe_tree_digest(path)
            if tree_errors:
                errors.extend(f"{name} ({label}): {msg}" for msg in tree_errors)
                continue
            digests[label] = digest
        if len(digests) == len(copies) and len(set(digests.values())) > 1:
            errors.append(f"{name}: Codex and Claude copies differ")

        recorded = generated.get(name, {}).get("sha256")
        if digests and recorded not in digests.values():
            errors.append(f"{name}: manifest digest does not match generated copies")

        if source is not None:
            src_dir = source / "skills" / name
            if src_dir.is_dir():
                src_digest, src_errors = safe_tree_digest(src_dir)
                if src_errors:
                    errors.extend(f"{name} (source): {msg}" for msg in src_errors)
                elif digests and src_digest not in digests.values():
                    errors.append(f"{name}: generated copy differs from source")
    return errors


# --------------------------------------------------------------------------
# Transaction primitives
# --------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _write_journal(data: dict) -> None:
    payload = dict(data)
    payload["updated_at"] = _now_iso()
    JOURNAL_PATH.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _acquire_lock() -> None:
    os.mkdir(TX_ROOT)


def _stage_skill(source_dir: Path, staging_dir: Path) -> None:
    entry_type = classify_entry(source_dir)
    if entry_type != EntryType.DIR:
        raise UnsafeTreeError([(source_dir.name, entry_type)])
    staging_dir.mkdir(parents=True, exist_ok=True)
    for child in sorted(source_dir.iterdir()):
        child_type = classify_entry(child)
        target = staging_dir / child.name
        if child_type == EntryType.DIR:
            _stage_skill(child, target)
        elif child_type == EntryType.FILE:
            target.write_bytes(child.read_bytes())
            target.chmod(normalized_mode(child))
        else:
            raise UnsafeTreeError([(child.name, child_type)])


def _publish_client(
    label: str, destination: Path, selected: list[str], obsolete: list[str],
    new_trees: dict[str, dict[str, Path]], backups: Path,
) -> list[str]:
    """Publish one client's skill directories via per-skill atomic renames:
    evict any existing directory to its backup slot, then place the staged
    replacement (if the skill is still selected; obsolete skills are evicted
    without replacement). Never touches the destination's parent directory or
    any sibling entry outside the named skill directories."""
    published_names: list[str] = []
    for name in selected + obsolete:
        live = destination / name
        backup = backups / label / name
        if live.exists():
            backup.parent.mkdir(parents=True, exist_ok=True)
            os.rename(live, backup)
        if name in selected:
            live.parent.mkdir(parents=True, exist_ok=True)
            os.rename(new_trees[label][name], live)
        published_names.append(name)
    return published_names


def _publish_manifest(new_manifest_path: Path, backups: Path) -> None:
    manifest_backup = backups / "manifest.json"
    if MANIFEST_PATH.exists():
        manifest_backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(MANIFEST_PATH, manifest_backup)
    os.replace(new_manifest_path, MANIFEST_PATH)


def _run_sync_transaction(source: Path, manifest: dict, selected: list[str], managed_prior: set[str]) -> list[str]:
    obsolete = sorted(managed_prior - set(selected))
    staging = TX_ROOT / "staging"
    _write_journal({"phase": "STAGING", "started_at": _now_iso(), "selected": selected, "obsolete": obsolete})

    new_trees: dict[str, dict[str, Path]] = {label: {} for label in DESTINATIONS}
    for name in selected:
        src_dir = source / "skills" / name
        for label in DESTINATIONS:
            dst = staging / label / name
            _stage_skill(src_dir, dst)
            new_trees[label][name] = dst

    staged_digests: dict[str, dict[str, str]] = {label: {} for label in DESTINATIONS}
    for label in DESTINATIONS:
        for name in selected:
            digest, errs = safe_tree_digest(new_trees[label][name])
            if errs:
                raise RuntimeError(f"staged content invalid for {label}/{name}: {'; '.join(errs)}")
            staged_digests[label][name] = digest
    for name in selected:
        first_label = next(iter(DESTINATIONS))
        for label in DESTINATIONS:
            if staged_digests[label][name] != staged_digests[first_label][name]:
                raise RuntimeError(f"staged client trees diverge for {name}")

    new_generated = {
        name: {
            "canonical_source_path": f"skills/{name}",
            "codex_destination": f".agents/skills/{name}",
            "claude_destination": f".claude/skills/{name}",
            "sha256": staged_digests[next(iter(DESTINATIONS))][name],
        }
        for name in selected
    }
    new_manifest = dict(manifest)
    new_manifest["generated_skills"] = new_generated
    new_manifest_text = json.dumps(new_manifest, indent=2, sort_keys=True) + "\n"
    schema_errors = validate_manifest_schema(load_manifest_text(new_manifest_text))
    if schema_errors:
        raise RuntimeError(f"staged manifest is invalid: {'; '.join(schema_errors)}")
    new_manifest_path = staging / "manifest.json"
    new_manifest_path.parent.mkdir(parents=True, exist_ok=True)
    new_manifest_path.write_text(new_manifest_text, encoding="utf-8")

    _write_journal({"phase": "STAGED", "selected": selected, "obsolete": obsolete})

    backups = TX_ROOT / "backups"
    published: dict[str, list[str]] = {}
    for label, destination in DESTINATIONS.items():
        published[label] = _publish_client(label, destination, selected, obsolete, new_trees, backups)
        _write_journal({"phase": f"{label.upper()}_PUBLISHED", "published": published, "obsolete": obsolete, "selected": selected})

    _publish_manifest(new_manifest_path, backups)
    _write_journal({"phase": "MANIFEST_PUBLISHED", "published": published, "obsolete": obsolete, "selected": selected})

    post_errors = _check_impl(source)
    if post_errors:
        raise RuntimeError(f"post-publication validation failed: {'; '.join(post_errors)}")

    shutil.rmtree(TX_ROOT, ignore_errors=True)
    return []


def _rollback_transaction() -> list[str]:
    transaction_error = transaction_root_error()
    if transaction_error:
        return [transaction_error]
    errors: list[str] = []
    restored_anything = False
    backups = TX_ROOT / "backups"
    for label, destination in DESTINATIONS.items():
        backup_dir = backups / label
        if not backup_dir.is_dir():
            continue
        for backup_entry in sorted(backup_dir.iterdir()):
            entry_type = classify_entry(backup_entry)
            if entry_type != EntryType.DIR:
                errors.append(f"transaction {label} backup entry is not a directory: {backup_entry.name}")
                continue
            restored_anything = True
            live = destination / backup_entry.name
            try:
                if live.exists():
                    shutil.rmtree(live)
                os.rename(backup_entry, live)
            except OSError as exc:
                errors.append(f"failed to restore {label}/{backup_entry.name}: {exc}")
    manifest_backup = backups / "manifest.json"
    if manifest_backup.is_file():
        restored_anything = True
        try:
            os.replace(manifest_backup, MANIFEST_PATH)
        except OSError as exc:
            errors.append(f"failed to restore manifest: {exc}")
    if errors:
        return errors
    if restored_anything:
        # Verify the restore only when something was actually rolled back;
        # if the failure happened before any live path was touched (e.g.
        # during staging), live state was never mutated in the first place,
        # so there is nothing to verify and no prior "fully synced" state is
        # implied -- running a full check here would wrongly require one.
        post_check_errors = _check_impl(None)
        if post_check_errors:
            return [f"post-rollback validation failed: {'; '.join(post_check_errors)}"]
    shutil.rmtree(TX_ROOT, ignore_errors=True)
    return []


def sync(source: Path) -> list[str]:
    transaction_error = transaction_root_error()
    if transaction_error:
        return [transaction_error]
    if TX_ROOT.exists():
        return ["an interrupted or in-progress synchronization transaction was detected; run --recover"]
    try:
        manifest = load_manifest()
    except (OSError, json.JSONDecodeError, DuplicateKeyError) as exc:
        return [f"cannot read manifest: {exc}"]
    errors = validate_manifest_schema(manifest)
    if errors:
        return errors
    errors = verify_source(source, manifest)
    if errors:
        return errors

    destinations, root_errors = validated_generated_roots()
    if root_errors:
        return root_errors

    selected = sorted(manifest["skills"])
    managed_prior = set(manifest.get("generated_skills", {}))

    for label, destination in destinations.items():
        for existing in destination.iterdir():
            if not existing.is_dir():
                continue
            if existing.name in selected or existing.name in managed_prior:
                continue
            return [f"refusing sync: {label} contains unrecognized directory '{existing.name}'"]

    for name in selected:
        src_dir = source / "skills" / name
        source_digest, source_errors = safe_tree_digest(src_dir)
        if source_errors:
            return [f"{name} (source): {msg}" for msg in source_errors]
        for label, destination in destinations.items():
            dest = destination / name
            if not dest.exists():
                continue
            dest_digest, dest_errors = safe_tree_digest(dest)
            if dest_errors or dest_digest != source_digest:
                return [f"refusing to overwrite divergent generated directory: {label}/{name}"]

    try:
        _acquire_lock()
    except FileExistsError:
        return ["another synchronization is already in progress or was interrupted; run --recover"]

    try:
        return _run_sync_transaction(source, manifest, selected, managed_prior)
    except Exception as exc:  # noqa: BLE001 - transactional boundary must always attempt rollback
        rollback_errors = _rollback_transaction()
        if rollback_errors:
            return [
                f"sync failed ({exc}) and automatic rollback could not be fully verified: {'; '.join(rollback_errors)}",
                f"transaction evidence retained at {TX_ROOT}",
            ]
        return [f"sync failed and was rolled back to the prior verified state: {exc}"]


def recover() -> tuple[list[str], bool]:
    transaction_error = transaction_root_error()
    if transaction_error:
        return [transaction_error], True
    if not TX_ROOT.exists():
        return [], False
    return _rollback_transaction(), True


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true")
    group.add_argument("--sync", action="store_true")
    group.add_argument(
        "--recover", action="store_true",
        help="restore the last verified prior state after an interrupted synchronization",
    )
    parser.add_argument("--source")
    args = parser.parse_args()
    source = source_root(args.source)
    if args.sync and source is None:
        parser.error("--sync requires --source or NEVELIB_CANONICAL_SKILLS_SOURCE")

    if args.recover:
        errors, recovered = recover()
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        if errors:
            return 1
        if recovered:
            print("PASS: interrupted transaction detected and rolled back to the last verified prior state")
        else:
            print("PASS: no interrupted transaction was found")
        return 0

    errors = sync(source) if args.sync else check(source)
    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    if not errors:
        print("PASS: generated skill configuration is consistent")
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
