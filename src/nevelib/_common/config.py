"""YAML configuration loading, schema validation, and default merging.

Each nevelib module has a config.sample.yaml defining its schema.
This module loads user configs, merges with defaults, and validates.
"""

from pathlib import Path
from typing import Any


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
    raise NotImplementedError


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
    raise NotImplementedError


def validate_required_keys(cfg: dict[str, Any], required: list[str], context: str = "") -> None:
    """Validate that all required keys are present and not placeholder values.

    Args:
        cfg: Configuration dictionary to check.
        required: List of required key names.
        context: Label for error messages (e.g., module name).

    Raises:
        ValueError: If any required key is missing or has a placeholder value.
    """
    raise NotImplementedError
