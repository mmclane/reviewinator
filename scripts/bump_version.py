#!/usr/bin/env python3
"""Bump the minor version in pyproject.toml."""

import sys
from pathlib import Path

import tomli
import tomli_w


def bump_version():
    """Read version from pyproject.toml, bump minor, write back."""
    pyproject_path = Path("pyproject.toml")

    if not pyproject_path.exists():
        print("Error: pyproject.toml not found", file=sys.stderr)
        sys.exit(1)

    # Read current version
    with open(pyproject_path, "rb") as f:
        data = tomli.load(f)

    current_version = data["project"]["version"]

    # Parse version
    try:
        parts = current_version.split(".")
        if len(parts) != 3:
            raise ValueError("Version must be in format X.Y.Z")
        major, minor, patch = map(int, parts)
    except (ValueError, AttributeError) as e:
        print(f"Error: Invalid version format '{current_version}': {e}", file=sys.stderr)
        sys.exit(1)

    # Bump minor version, reset patch to 0
    new_version = f"{major}.{minor + 1}.0"

    # Update version in data
    data["project"]["version"] = new_version

    # Write back
    with open(pyproject_path, "wb") as f:
        tomli_w.dump(data, f)

    print(new_version)


if __name__ == "__main__":
    bump_version()
