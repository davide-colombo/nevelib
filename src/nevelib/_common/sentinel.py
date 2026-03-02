"""Step-level sentinel (lock file) management for resume support.

Sentinels track which steps have completed so that reruns skip
already-finished work. Each step writes a sentinel file on success;
the presence of that file signals completion.
"""

from pathlib import Path
from typing import Callable


def sentinel_path(sentinel_dir: Path, step_name: str) -> Path:
    """Return the canonical sentinel file path for a step.

    Args:
        sentinel_dir: Directory containing sentinel files.
        step_name: Name of the step.

    Returns:
        Path to the sentinel file.
    """
    raise NotImplementedError


def is_done(sentinel_dir: Path, step_name: str) -> bool:
    """Check if a step's sentinel exists, indicating completion.

    Args:
        sentinel_dir: Directory containing sentinel files.
        step_name: Name of the step.

    Returns:
        True if the sentinel file exists.
    """
    raise NotImplementedError


def run_step(
    name: str,
    sentinel_dir: Path,
    expected_outputs: list[Path],
    func: Callable[[], None],
    *,
    skip_if_done: bool = True,
) -> None:
    """Execute a step function with sentinel-based resume logic.

    If skip_if_done is True and the sentinel exists and all expected outputs
    exist, the step is skipped.  Otherwise, func() is called.  On success,
    the sentinel is written.  On failure, the sentinel is not written and
    the exception propagates.

    Args:
        name: Step name (used for sentinel filename and logging).
        sentinel_dir: Directory for sentinel files.
        expected_outputs: Paths that must exist after successful execution.
        func: Callable that performs the step's work.
        skip_if_done: Whether to skip if sentinel already exists.

    Raises:
        RuntimeError: If func() succeeds but expected outputs are missing.
    """
    raise NotImplementedError
