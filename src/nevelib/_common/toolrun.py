"""Subprocess execution, external tool availability checks, and log routing.

Provides a single entry point for running external bioinformatics tools
with consistent logging, error handling, and timeout behavior.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
from typing import Iterable


LOGGER = logging.getLogger(__name__)


@dataclass
class ToolInfo:
    """Information about an external tool.

    Attributes:
        name: Tool name or path.
        available: Whether the tool was found on PATH.
        version: Detected version string (None if not available or not parseable).
        path: Resolved absolute path to the binary.
    """

    name: str
    available: bool
    version: str | None = None
    path: Path | None = None


def _version_tuple(value: str) -> tuple[int, ...] | None:
    """Extract a comparable integer version tuple from free-form text."""
    match = re.search(r"\d+(?:\.\d+)*", value)
    if not match:
        return None
    try:
        return tuple(int(part) for part in match.group(0).split("."))
    except ValueError:
        return None


def _is_version_at_least(found: str, minimum: str) -> bool:
    """Return True when `found` is greater than or equal to `minimum`."""
    found_tuple = _version_tuple(found)
    min_tuple = _version_tuple(minimum)
    if found_tuple is None or min_tuple is None:
        return False

    width = max(len(found_tuple), len(min_tuple))
    found_norm = found_tuple + (0,) * (width - len(found_tuple))
    min_norm = min_tuple + (0,) * (width - len(min_tuple))
    return found_norm >= min_norm


def _command_display(cmd: list[str] | str) -> str:
    """Render a readable command string for logs and errors."""
    if isinstance(cmd, str):
        return cmd
    return shlex.join(cmd)


def _stderr_tail_from_text(stderr: str | bytes | None, *, n: int = 20) -> str:
    """Return the last `n` stderr lines from captured process output."""
    if stderr is None:
        return ""
    if isinstance(stderr, bytes):
        text = stderr.decode("utf-8", errors="replace")
    else:
        text = stderr
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def _stderr_tail_from_file(path: Path | None, *, n: int = 20) -> str:
    """Return the last `n` stderr lines from a log file when available."""
    if path is None or (not path.is_file()):
        return ""
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    return "\n".join(lines[-n:])


def check_tool(
    name: str,
    *,
    version_args: list[str] | None = None,
    min_version: str | None = None,
) -> ToolInfo:
    """Check if an external tool is available and optionally verify its version.

    Args:
        name: Tool name or path.
        version_args: Arguments to pass to get the version (e.g., ['--version']).
        min_version: Minimum required version string.

    Returns:
        ToolInfo with availability and version details.
    """
    resolved = shutil.which(name)
    if resolved is None:
        maybe_path = Path(name).expanduser()
        if maybe_path.is_file() and os.access(maybe_path, os.X_OK):
            resolved = str(maybe_path.resolve())

    if resolved is None:
        return ToolInfo(name=name, available=False, version=None, path=None)

    resolved_path = Path(resolved)
    version: str | None = None
    available = True

    if version_args is None and min_version is not None:
        version_args = ["--version"]

    if version_args is not None:
        proc = subprocess.run(
            [str(resolved_path), *version_args],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        combined = "\n".join(
            part.strip()
            for part in (proc.stdout or "", proc.stderr or "")
            if part and part.strip()
        ).strip()
        if combined:
            version = combined.splitlines()[0].strip()

        if min_version is not None:
            if version is None or (not _is_version_at_least(version, min_version)):
                available = False

    return ToolInfo(name=name, available=available, version=version, path=resolved_path)


def run_tool(
    cmd: list[str] | str,
    *,
    out_log: Path | None = None,
    err_log: Path | None = None,
    check: bool = True,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run an external tool with standardized logging and error handling.

    Args:
        cmd: Command as a list of strings or a shell string.
        out_log: Path to write stdout. If None, stdout is captured in memory.
        err_log: Path to write stderr. If None, stderr is captured in memory.
        check: Raise CalledProcessError on non-zero exit.
        timeout: Timeout in seconds (None for no timeout).
        env: Environment variables to set (merged with os.environ).

    Returns:
        subprocess.CompletedProcess with the result.

    Raises:
        subprocess.CalledProcessError: If check=True and exit code is non-zero.
        FileNotFoundError: If the command binary is not found.
    """
    if isinstance(cmd, list) and len(cmd) == 0:
        raise ValueError("Command list must not be empty.")

    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)

    use_shell = isinstance(cmd, str)
    display_cmd = _command_display(cmd)
    LOGGER.debug("Running command: %s", display_cmd)

    if out_log is not None:
        out_log.parent.mkdir(parents=True, exist_ok=True)
    if err_log is not None:
        err_log.parent.mkdir(parents=True, exist_ok=True)

    out_handle = None
    err_handle = None
    try:
        if out_log is not None:
            out_handle = out_log.open("w", encoding="utf-8")
        if err_log is not None:
            err_handle = err_log.open("w", encoding="utf-8")

        proc = subprocess.run(
            cmd,
            shell=use_shell,
            stdout=out_handle if out_handle is not None else subprocess.PIPE,
            stderr=err_handle if err_handle is not None else subprocess.PIPE,
            check=False,
            timeout=timeout,
            env=merged_env,
            text=True,
        )
    finally:
        if out_handle is not None:
            out_handle.close()
        if err_handle is not None:
            err_handle.close()

    if check and proc.returncode != 0:
        stderr_tail = _stderr_tail_from_text(proc.stderr)
        if not stderr_tail:
            stderr_tail = _stderr_tail_from_file(err_log)
        detail = (
            f"Command failed with exit code {proc.returncode}: {display_cmd}\n"
            f"stderr tail (last 20 lines):\n{stderr_tail or '<no stderr output>'}"
        )
        exc = subprocess.CalledProcessError(
            returncode=proc.returncode,
            cmd=cmd,
            output=proc.stdout,
            stderr=proc.stderr,
        )
        exc.add_note(detail)
        raise exc

    return proc
