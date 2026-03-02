"""YAML configuration loading, schema validation, and default merging.

Each nevelib module has a config.sample.yaml defining its schema.
This module loads user configs, merges with defaults, and validates.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import subprocess
from typing import Any


try:
    import yaml  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - exercised when PyYAML is unavailable
    yaml = None


def _fallback_yaml_safe_load(text: str) -> Any:
    """Fallback YAML loader used only when PyYAML is unavailable.

    This uses the system Ruby YAML parser, then converts through JSON to ensure
    plain Python data structures.
    """
    cmd = [
        "ruby",
        "-rjson",
        "-ryaml",
        "-e",
        "obj = YAML.safe_load(ARGF.read, aliases: true); puts JSON.generate(obj)",
    ]
    proc = subprocess.run(
        cmd,
        input=text,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if proc.returncode != 0:
        raise ValueError(proc.stderr.strip() or "Failed to parse YAML configuration.")

    raw = proc.stdout.strip()
    if not raw:
        return None
    return json.loads(raw)


def load_config(path: Path) -> dict[str, Any]:
    """Load a YAML configuration file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed configuration dictionary.

    Raises:
        FileNotFoundError: If path does not exist.
        ValueError: If the file is not valid YAML.
    """
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise ValueError(f"Configuration path is not a regular file: {path}")

    text = path.read_text(encoding="utf-8")

    try:
        parsed: Any
        if yaml is not None:
            parsed = yaml.safe_load(text)
        else:
            parsed = _fallback_yaml_safe_load(text)
    except Exception as exc:
        raise ValueError(f"Invalid YAML configuration at {path}: {exc}") from exc

    if parsed is None:
        return {}
    if not isinstance(parsed, dict):
        raise ValueError(f"YAML root must be a mapping, found {type(parsed).__name__}.")
    return parsed


def merge_defaults(user_cfg: dict[str, Any], defaults: dict[str, Any]) -> dict[str, Any]:
    """Deep-merge a user configuration with defaults.

    User values take precedence.  Missing keys are filled from defaults.
    Nested dicts are merged recursively; other types are replaced.

    Args:
        user_cfg: User-provided configuration.
        defaults: Default configuration (typically from config.sample.yaml).

    Returns:
        Merged configuration dictionary.
    """

    def _merge(user_value: Any, default_value: Any) -> Any:
        if isinstance(default_value, dict) and isinstance(user_value, dict):
            merged: dict[str, Any] = {k: copy.deepcopy(v) for k, v in default_value.items()}
            for key, value in user_value.items():
                if key in merged:
                    merged[key] = _merge(value, merged[key])
                else:
                    merged[key] = copy.deepcopy(value)
            return merged
        return copy.deepcopy(user_value)

    return _merge(user_cfg, defaults)


def _is_placeholder_value(value: Any) -> bool:
    """Return True when a value is considered a placeholder."""
    if value is None:
        return True

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return True
        upper = stripped.upper()
        if upper in {"PLACEHOLDER", "CHANGEME"}:
            return True
        if stripped.startswith("/path/to/"):
            return True

    return False


def validate_required_keys(cfg: dict[str, Any], required: list[str], context: str = "") -> None:
    """Validate that all required keys are present and not placeholder values.

    Args:
        cfg: Configuration dictionary to check.
        required: List of required key names.
        context: Label for error messages (e.g., module name).

    Raises:
        ValueError: If any required key is missing or has a placeholder value.
    """
    missing: list[str] = []
    placeholders: list[str] = []

    for key in required:
        if key not in cfg:
            missing.append(key)
            continue
        if _is_placeholder_value(cfg[key]):
            placeholders.append(key)

    if missing or placeholders:
        parts: list[str] = []
        if missing:
            parts.append(f"missing required keys: {', '.join(missing)}")
        if placeholders:
            parts.append(f"placeholder values for keys: {', '.join(placeholders)}")
        prefix = f"[{context}] " if context else ""
        raise ValueError(prefix + "; ".join(parts))
