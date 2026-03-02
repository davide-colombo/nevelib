"""CLI entry point for the nevelib assembly module.

Usage:
    nevelib-assembly config.yaml
"""

import sys
from pathlib import Path


def main() -> None:
    """Entry point: load config YAML and run the assembly pipeline."""
    if len(sys.argv) != 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: nevelib-assembly <config.yaml>", file=sys.stderr)
        sys.exit(2 if len(sys.argv) != 2 else 0)

    config_path = Path(sys.argv[1])
    if not config_path.is_file():
        print(f"Error: config file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    # TODO: Phase B — load config, validate, run module pipeline
    raise NotImplementedError(f"nevelib-assembly not yet implemented. Config: {config_path}")


if __name__ == "__main__":
    main()
