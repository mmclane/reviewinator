# macOS App Bundling Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Bundle Reviewinator as a standalone macOS .app and automate GitHub releases with automatic minor version bumping.

**Architecture:** Create scripts/bump_version.py for version management, setup.py for py2app bundling, and Makefile targets (build, release) that orchestrate the release process using gh CLI.

**Tech Stack:** Python 3.11+, py2app, tomli/tomli-w, gh CLI, make

---

## Task 1: Add Dependencies to pyproject.toml

**Files:**
- Modify: `pyproject.toml`

**Step 1: Add py2app and TOML libraries to dev dependencies**

In `pyproject.toml`, update the `[project.optional-dependencies]` section:

```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "py2app>=0.28.0",
    "tomli>=2.0.0",
    "tomli-w>=1.0.0",
]
```

**Step 2: Install new dependencies**

Run: `uv sync --all-extras`
Expected: Dependencies installed successfully

**Step 3: Verify imports work**

Run: `python -c "import py2app; import tomli; import tomli_w; print('✓ All dependencies installed')"`
Expected: "✓ All dependencies installed"

**Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "deps: add py2app, tomli, and tomli-w for app bundling"
```

---

## Task 2: Create Version Bump Script

**Files:**
- Create: `scripts/bump_version.py`

**Step 1: Create scripts directory**

Run: `mkdir -p scripts`

**Step 2: Write version bump script**

Create `scripts/bump_version.py`:

```python
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
```

**Step 3: Make script executable**

Run: `chmod +x scripts/bump_version.py`

**Step 4: Test the script (dry run)**

Before testing, note current version:
Run: `grep 'version =' pyproject.toml`
Expected: Shows current version (e.g., `version = "0.1.0"`)

Run: `python scripts/bump_version.py`
Expected: Prints `0.2.0`

Verify file was updated:
Run: `grep 'version =' pyproject.toml`
Expected: `version = "0.2.0"`

**Step 5: Restore original version for now**

Run: `git checkout pyproject.toml`
Expected: Version reverted to 0.1.0

**Step 6: Commit**

```bash
git add scripts/bump_version.py
git commit -m "feat: add version bump script for automatic minor increments"
```

---

## Task 3: Create py2app Setup File

**Files:**
- Create: `setup.py`

**Step 1: Get current version for setup.py**

Run: `python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])"`
Expected: Prints current version (e.g., `0.1.0`)

**Step 2: Create setup.py**

Create `setup.py` at repository root:

```python
"""
py2app setup script for Reviewinator.
"""

from setuptools import setup

APP = ['src/reviewinator/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'github', 'pync', 'yaml', 'certifi'],
    'includes': ['reviewinator'],
    'plist': {
        'CFBundleName': 'Reviewinator',
        'CFBundleDisplayName': 'Reviewinator',
        'CFBundleIdentifier': 'com.reviewinator.app',
        'CFBundleVersion': '0.1.0',
        'CFBundleShortVersionString': '0.1.0',
        'LSUIElement': True,  # Run as menu bar app (no dock icon)
        'NSHighResolutionCapable': True,
    }
}

setup(
    name='Reviewinator',
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
```

**Step 3: Commit**

```bash
git add setup.py
git commit -m "feat: add py2app setup configuration"
```

---

## Task 4: Update Makefile with Build Target

**Files:**
- Modify: `Makefile`

**Step 1: Add build target**

Add to `Makefile` (after existing targets):

```makefile
build:
	python setup.py py2app
	@echo "✓ Built dist/Reviewinator.app"
```

**Step 2: Update clean target**

Modify the `clean` target to include build artifacts:

```makefile
clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info *.app.zip
```

**Step 3: Test build target**

Run: `make build`
Expected:
- Creates `dist/Reviewinator.app`
- Creates `build/` directory with intermediate files
- Prints "✓ Built dist/Reviewinator.app"

**Step 4: Verify the app**

Run: `ls -la dist/`
Expected: Shows `Reviewinator.app` directory

**Step 5: Test the built app**

Run: `open dist/Reviewinator.app`
Expected: App launches, shows menu bar icon (may need to configure GitHub token first)

**Step 6: Clean up**

Run: `make clean`
Expected: `dist/`, `build/`, and other artifacts removed

**Step 7: Commit**

```bash
git add Makefile
git commit -m "feat: add make build target for py2app bundling"
```

---

## Task 5: Add Release Makefile Targets

**Files:**
- Modify: `Makefile`

**Step 1: Add _package target**

Add to `Makefile`:

```makefile
_package:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	cd dist && zip -r ../Reviewinator-v$(VERSION).app.zip Reviewinator.app
	@echo "✓ Created Reviewinator-v$(VERSION).app.zip"
```

**Step 2: Add _publish target**

Add to `Makefile`:

```makefile
_publish:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	gh release create v$(VERSION) \
		--title "Release v$(VERSION)" \
		--notes "Release v$(VERSION)" \
		Reviewinator-v$(VERSION).app.zip
	@echo "✓ Published release v$(VERSION)"
```

**Step 3: Add release target**

Add to `Makefile`:

```makefile
release:
	@echo "Starting release process..."
	python scripts/bump_version.py
	$(MAKE) build
	$(MAKE) _package
	$(MAKE) _publish
	git add pyproject.toml setup.py
	git commit -m "chore: bump version to $$(python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])')"
	@echo "✓ Release complete"
	@echo "Push changes: git push && git push --tags"
```

**Step 4: Update .PHONY declaration**

At the top of Makefile, update the `.PHONY` line:

```makefile
.PHONY: setup test test-cov lint format run clean build release _package _publish
```

**Step 5: Commit**

```bash
git add Makefile
git commit -m "feat: add release automation targets to Makefile"
```

---

## Task 6: Update setup.py Version Dynamically

**Files:**
- Modify: `setup.py`

**Step 1: Update setup.py to read version from pyproject.toml**

Replace the OPTIONS dict in `setup.py`:

```python
import tomli

# Read version from pyproject.toml
with open("pyproject.toml", "rb") as f:
    version = tomli.load(f)["project"]["version"]

APP = ['src/reviewinator/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'github', 'pync', 'yaml', 'certifi'],
    'includes': ['reviewinator'],
    'plist': {
        'CFBundleName': 'Reviewinator',
        'CFBundleDisplayName': 'Reviewinator',
        'CFBundleIdentifier': 'com.reviewinator.app',
        'CFBundleVersion': version,
        'CFBundleShortVersionString': version,
        'LSUIElement': True,
        'NSHighResolutionCapable': True,
    }
}
```

**Step 2: Test that version is read correctly**

Run: `python -c "import tomli; print(tomli.load(open('pyproject.toml', 'rb'))['project']['version'])"`
Expected: Prints current version

**Step 3: Test build still works**

Run: `make build`
Expected: Builds successfully

**Step 4: Clean up**

Run: `make clean`

**Step 5: Commit**

```bash
git add setup.py
git commit -m "feat: read version dynamically from pyproject.toml in setup.py"
```

---

## Task 7: Test Full Release Process (Dry Run)

**Files:**
- None (testing only)

**Step 1: Ensure gh CLI is installed and authenticated**

Run: `which gh`
Expected: Shows path to gh (e.g., `/opt/homebrew/bin/gh`)

If not installed:
Run: `brew install gh`

Run: `gh auth status`
Expected: Shows "Logged in to github.com as <username>"

If not authenticated:
Run: `gh auth login`

**Step 2: Check current version**

Run: `grep 'version =' pyproject.toml`
Expected: Shows current version (e.g., `version = "0.1.0"`)

**Step 3: Do NOT run make release yet**

This is a dry run - we'll verify each component works but not actually publish.

**Step 4: Test version bump in isolation**

Run: `python scripts/bump_version.py`
Expected: Prints new version (e.g., `0.2.0`)

Verify:
Run: `grep 'version =' pyproject.toml`
Expected: `version = "0.2.0"`

**Step 5: Test build with new version**

Run: `make build`
Expected: Builds successfully

**Step 6: Test packaging**

Run: `make _package`
Expected: Creates `Reviewinator-v0.2.0.app.zip`

Verify:
Run: `ls -lh Reviewinator-v*.app.zip`
Expected: Shows the zip file (~50-80MB)

**Step 7: DO NOT test _publish (would create real release)**

Skip this step for now.

**Step 8: Revert changes**

Run: `git checkout pyproject.toml`
Run: `make clean`

**Step 9: Document findings**

If all steps passed, the release process is ready.
If any failed, debug before proceeding to Task 8.

---

## Task 8: Update README with Installation and Usage

**Files:**
- Modify: `README.md`

**Step 1: Check if README exists**

Run: `ls README.md`
Expected: File exists

If not:
Run: `touch README.md`

**Step 2: Add installation section**

Add to `README.md`:

```markdown
## Installation

### For Users

1. Download the latest `Reviewinator-vX.Y.Z.app.zip` from [Releases](https://github.com/mmclane/reviewinator/releases)
2. Unzip the file
3. Move `Reviewinator.app` to your Applications folder
4. Right-click the app and select "Open" (first time only, due to unsigned app)
5. Click "Open" in the security dialog

### Auto-Start at Login

To have Reviewinator launch automatically when you log in:

1. Open **System Settings > General > Login Items**
2. Click the **+** button under "Open at Login"
3. Navigate to `Reviewinator.app` and select it
4. The app will now start automatically on login

### Configuration

Create `~/.config/reviewinator/config.yaml`:

```yaml
github_token: ghp_your_token_here
excluded_repos: []
excluded_review_teams: []
created_pr_filter: either
activity_lookback_days: 14
refresh_interval: 300
```

See CLAUDE.md for detailed configuration options.
```

**Step 3: Add development section**

Add to `README.md`:

```markdown
## Development

### Setup

```bash
# Install dependencies
make setup

# Run tests
make test

# Run the app (development mode)
make run
```

### Building the App

```bash
# Build macOS .app bundle
make build

# Test the built app
open dist/Reviewinator.app

# Clean build artifacts
make clean
```

### Creating a Release

```bash
# Prerequisites
brew install gh
gh auth login

# Create release (bumps version, builds, publishes to GitHub)
make release

# Push changes
git push && git push --tags
```

This will:
1. Bump the minor version (e.g., 0.1.0 → 0.2.0)
2. Build the .app bundle
3. Create a GitHub release with the .app.zip
4. Commit the version bump
```

**Step 4: Commit**

```bash
git add README.md
git commit -m "docs: add installation and development instructions"
```

---

## Task 9: Create Initial Release

**Files:**
- `pyproject.toml` (version will be bumped)
- `setup.py` (version read dynamically)

**Step 1: Ensure all previous tasks are committed**

Run: `git status`
Expected: "working tree clean"

**Step 2: Run full release process**

Run: `make release`

Expected output:
```
Starting release process...
0.2.0
✓ Built dist/Reviewinator.app
✓ Created Reviewinator-v0.2.0.app.zip
✓ Published release v0.2.0
[main abc1234] chore: bump version to 0.2.0
✓ Release complete
Push changes: git push && git push --tags
```

**Step 3: Verify release on GitHub**

Run: `gh release list`
Expected: Shows `v0.2.0` release

Or visit: `https://github.com/mmclane/reviewinator/releases`
Expected: Shows "Release v0.2.0" with `Reviewinator-v0.2.0.app.zip` asset

**Step 4: Push changes**

Run: `git push && git push --tags`
Expected: Pushes commit and tag to origin

**Step 5: Verify version was updated**

Run: `grep 'version =' pyproject.toml`
Expected: `version = "0.2.0"`

**Step 6: Download and test release**

Run: `gh release download v0.2.0`
Expected: Downloads `Reviewinator-v0.2.0.app.zip`

Run: `unzip Reviewinator-v0.2.0.app.zip`
Run: `open Reviewinator.app`
Expected: App launches successfully

**Step 7: Clean up downloaded files**

Run: `rm -rf Reviewinator-v0.2.0.app.zip Reviewinator.app`

---

## Task 10: Add .gitignore Entries

**Files:**
- Modify: `.gitignore`

**Step 1: Check if .gitignore exists**

Run: `ls .gitignore`
Expected: File exists

If not:
Run: `touch .gitignore`

**Step 2: Add build artifacts**

Add to `.gitignore`:

```
# Build artifacts
dist/
build/
*.app.zip
*.egg-info
```

**Step 3: Verify gitignore works**

Run: `make build`
Run: `git status`
Expected: `dist/` and `build/` not shown as untracked

**Step 4: Clean up**

Run: `make clean`

**Step 5: Commit**

```bash
git add .gitignore
git commit -m "chore: ignore build artifacts"
```

---

## Completion Checklist

After all tasks complete:

- [ ] `make build` creates `dist/Reviewinator.app`
- [ ] Built app launches and works correctly
- [ ] `make release` bumps version, builds, and publishes to GitHub
- [ ] GitHub release appears with .app.zip asset
- [ ] README documents installation and development
- [ ] .gitignore excludes build artifacts
- [ ] All changes committed and pushed

---

## Future Enhancements

Not implemented in this plan, but documented for later:

1. **GitHub Actions**: Automate releases on push to main
2. **Auto-update**: App checks for new versions on launch
3. **Code signing**: Sign app with Apple Developer cert
4. **App icon**: Add custom .icns icon file
5. **Version display**: Show version number in menu or About dialog
