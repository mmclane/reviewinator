#!/usr/bin/env python3
"""
Build script for Reviewinator macOS app.

This script works around setuptools 82+ incompatibility with pyproject.toml [build-system]
by temporarily removing that section during the py2app build.
"""

import os
import shutil
import subprocess
import sys
import tomli
import tomli_w


def main():
    # Read original pyproject.toml
    with open("pyproject.toml", "rb") as f:
        config = tomli.load(f)
        version = config["project"]["version"]

    # Create backup
    shutil.copy("pyproject.toml", "pyproject.toml.backup")

    try:
        # Write temporary pyproject.toml without [build-system] and dependencies
        temp_config = {k: v for k, v in config.items() if k != "build-system"}
        # Also remove dependencies from [project] to avoid install_requires error
        if "project" in temp_config:
            temp_project = {k: v for k, v in temp_config["project"].items()
                          if k not in ("dependencies", "optional-dependencies")}
            temp_config["project"] = temp_project

        with open("pyproject.toml", "wb") as f:
            tomli_w.dump(temp_config, f)

        # Run py2app with the simplified setup.py
        result = subprocess.run(
            [sys.executable, "setup.py", "py2app"],
            check=False
        )

        if result.returncode != 0:
            sys.exit(result.returncode)

        print(f"✓ Built dist/Reviewinator.app (version {version})")

    finally:
        # Restore original pyproject.toml
        shutil.move("pyproject.toml.backup", "pyproject.toml")


if __name__ == "__main__":
    main()
