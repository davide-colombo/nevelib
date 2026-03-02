"""Subprocess execution, external tool availability checks, and log routing.

Provides a single entry point for running external bioinformatics tools
with consistent logging, error handling, and timeout behavior.
"""

from dataclasses import dataclass
from pathlib import Path
import subprocess


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
    raise NotImplementedError


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
    raise NotImplementedError
