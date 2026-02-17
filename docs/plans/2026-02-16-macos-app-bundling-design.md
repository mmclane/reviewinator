# macOS App Bundling and GitHub Release Design

**Date:** 2026-02-16

## Overview

Bundle the Reviewinator Python application into a standalone macOS .app and automate GitHub releases with automatic minor version bumping via Makefile targets.

## Problem

Currently, Reviewinator runs as a Python script via `make run`. To distribute it as a proper macOS application:
- Users need to install Python and dependencies manually
- No easy way to distribute updates
- Not a first-class macOS citizen

## Solution

Create a release system that:
1. Bundles the app into a self-contained Reviewinator.app using py2app
2. Automatically increments minor version numbers (0.1.0 → 0.2.0 → 0.3.0)
3. Publishes releases to GitHub with the .app.zip as an asset
4. All orchestrated via simple `make build` and `make release` commands

## User Requirements

Based on clarifying questions:
1. **No code signing/notarization** - Keep it simple, users will approve the app manually
2. **Automatic version bumping** - Minor version increments (0.1.0 → 0.2.0) on each release
3. **Just the .app bundle** - GitHub releases contain only Reviewinator-vX.Y.Z.app.zip
4. **Use py2app** - macOS-native bundler, best for rumps/menu bar apps
5. **Manual login setup** - Document how users add to Login Items, no automatic installation

## Architecture

### Component Overview

Three main components working together:

1. **Version Manager** (`scripts/bump_version.py`)
   - Reads current version from `pyproject.toml`
   - Increments minor version (0.1.0 → 0.2.0)
   - Writes updated version back to `pyproject.toml`
   - Validates version format (X.Y.Z)

2. **App Bundler** (`setup.py` with py2app)
   - Configures py2app to bundle Python app + dependencies
   - Entry point: `reviewinator.app:main`
   - Includes rumps, PyGithub, pync, pyyaml
   - Produces standalone `dist/Reviewinator.app`

3. **Release Publisher** (Makefile targets)
   - Orchestrates: bump → build → zip → publish
   - Uses `gh` CLI to create GitHub releases
   - Uploads .app.zip as release asset
   - Commits version bump to git

### Release Flow

```
make release
  ↓
scripts/bump_version.py (0.1.0 → 0.2.0)
  ↓
python setup.py py2app (creates dist/Reviewinator.app)
  ↓
zip dist/Reviewinator.app → Reviewinator-v0.2.0.app.zip
  ↓
gh release create v0.2.0 Reviewinator-v0.2.0.app.zip
  ↓
git commit version bump to pyproject.toml
  ↓
User runs: git push && git push --tags
```

## Version Management

### Automatic Minor Bumping

- **Current version:** Stored in `pyproject.toml` under `[project] version = "0.1.0"`
- **Auto-increment:** `make release` bumps minor version (0.1.0 → 0.2.0 → 0.3.0)
- **Patch stays at 0:** Unless manually edited
- **Philosophy:** Each release is a feature/improvement release (minor), not just bug fixes (patch)

### Manual Major/Minor Bumps

- **Major bumps (1.0.0):** Manually edit `pyproject.toml` to `version = "1.0.0"`
- **Custom versions:** Edit pyproject.toml, next `make release` bumps from that base
- **Example:** Set to `1.0.0`, next release becomes `1.1.0`

### Version Script Logic

`scripts/bump_version.py`:
1. Parse `pyproject.toml` using `tomli` (read-only TOML parser)
2. Extract current version, split into major.minor.patch
3. Increment minor, reset patch to 0: `(0, 1, 0) → (0, 2, 0)`
4. Write back using `tomli-w` (write-only TOML library)
5. Print new version for Makefile to capture

## Build Process

### py2app Configuration

Create `setup.py` at repository root:

```python
from setuptools import setup

APP = ['src/reviewinator/app.py']
DATA_FILES = []
OPTIONS = {
    'argv_emulation': False,
    'packages': ['rumps', 'github', 'pync', 'yaml'],
    'plist': {
        'CFBundleName': 'Reviewinator',
        'CFBundleDisplayName': 'Reviewinator',
        'CFBundleIdentifier': 'com.reviewinator.app',
        'CFBundleVersion': '0.1.0',  # Will be updated by bump script
        'CFBundleShortVersionString': '0.1.0',
        'LSUIElement': True,  # Run as menu bar app without dock icon
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

### Build Output

- **Command:** `python setup.py py2app`
- **Output:** `dist/Reviewinator.app` (self-contained macOS application)
- **Size:** ~50-80MB (includes Python runtime + all dependencies)
- **Compatibility:** macOS 11+ (matches Python 3.11+ requirement)

### Dependencies

Add to `pyproject.toml`:
```toml
[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
    "py2app>=0.28.0",
    "tomli>=2.0.0",      # For reading TOML
    "tomli-w>=1.0.0",    # For writing TOML
]
```

## Release Process

### GitHub Release Creation

Uses `gh` CLI (GitHub's official command-line tool):

```bash
# Create release with tag, title, notes, and upload asset
gh release create v0.2.0 \
  --title "Release v0.2.0" \
  --notes "Release v0.2.0" \
  Reviewinator-v0.2.0.app.zip
```

### Release Workflow Steps

1. **Zip the app:**
   ```bash
   cd dist && zip -r ../Reviewinator-v0.2.0.app.zip Reviewinator.app
   ```

2. **Create GitHub release:**
   - Creates git tag `v0.2.0`
   - Creates release at `github.com/user/reviewinator/releases`
   - Uploads .app.zip as downloadable asset

3. **Commit version bump:**
   ```bash
   git add pyproject.toml
   git commit -m "chore: bump version to 0.2.0"
   ```

4. **User pushes:**
   ```bash
   git push && git push --tags
   ```

### Prerequisites

- `gh` CLI installed: `brew install gh`
- Authenticated: `gh auth login`
- Push access to repository

## Makefile Targets

### New Targets

```makefile
.PHONY: build release _package _publish

# Build the macOS app bundle
build:
	python setup.py py2app
	@echo "✓ Built dist/Reviewinator.app"

# Full release: bump, build, package, publish
release:
	@echo "Starting release process..."
	python scripts/bump_version.py
	$(MAKE) build
	$(MAKE) _package
	$(MAKE) _publish
	git add pyproject.toml
	git commit -m "chore: bump version to $$(python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])')"
	@echo "✓ Release complete"
	@echo "Push changes: git push && git push --tags"

# Internal: package the app as zip
_package:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	cd dist && zip -r ../Reviewinator-v$(VERSION).app.zip Reviewinator.app
	@echo "✓ Created Reviewinator-v$(VERSION).app.zip"

# Internal: publish to GitHub
_publish:
	$(eval VERSION := $(shell python -c 'import tomli; print(tomli.load(open("pyproject.toml", "rb"))["project"]["version"])'))
	gh release create v$(VERSION) \
		--title "Release v$(VERSION)" \
		--notes "Release v$(VERSION)" \
		Reviewinator-v$(VERSION).app.zip
	@echo "✓ Published release v$(VERSION)"
```

### Updated Clean Target

```makefile
clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info *.app.zip
```

### Typical Usage

**Development:**
```bash
make build          # Build app locally for testing
open dist/Reviewinator.app  # Test the built app
```

**Release:**
```bash
make release        # Bumps version, builds, publishes to GitHub
git push && git push --tags  # Push changes
```

## Testing Strategy

### Pre-Release Testing

1. **Local build test:**
   ```bash
   make build
   open dist/Reviewinator.app
   ```

2. **Verify functionality:**
   - App launches without errors
   - Menu bar icon appears
   - Can fetch PRs and display notifications
   - Config and cache work correctly

3. **If good, release:**
   ```bash
   make release
   ```

### Post-Release Verification

1. **Download from GitHub:**
   - Go to `github.com/user/reviewinator/releases`
   - Download `Reviewinator-vX.Y.Z.app.zip`

2. **Test downloaded artifact:**
   - Unzip and open the app
   - Verify it works identically to local build

3. **Version verification:**
   - Check that version number is correct (if displayed in app)

### Automated Testing

- **Python tests:** Existing `make test` continues to work
- **No .app bundle tests:** Would require macOS CI runner (expensive/complex)
- **Manual testing sufficient:** For a personal project, manual verification is adequate

### Version Validation

`scripts/bump_version.py` includes:
- Version format validation (must be X.Y.Z)
- Fails fast if version can't be parsed or written
- Prints clear error messages

### Rollback

- **If release has issues:** Create new release with fix (0.3.0 → 0.4.0)
- **GitHub releases:** Can be deleted via web UI or `gh release delete`
- **Version numbers:** Don't reuse - always increment forward

## Login at Startup

### Manual Setup (Option A - Selected)

**Document in README:**
1. Open **System Settings > General > Login Items**
2. Click **+** under "Open at Login"
3. Navigate to Reviewinator.app and add it
4. App will launch automatically on every login

**No code changes needed** - users configure this themselves once.

### Future Options (Not Implemented)

- **Option B:** LaunchAgent plist with installation script
- **Option C:** App self-registration via macOS APIs

## Error Handling

### Build Failures

- **py2app errors:** Check setup.py configuration, verify all dependencies installed
- **Missing dependencies:** Run `uv sync --all-extras`
- **Python version:** Ensure Python 3.11+ is active

### Release Failures

- **gh CLI not authenticated:** Run `gh auth login`
- **Version bump fails:** Check pyproject.toml syntax, ensure tomli/tomli-w installed
- **Release already exists:** Delete old release or bump version manually
- **Network errors:** Retry `make release`

### Runtime Issues

- **App won't open:** Users may need to right-click → Open first time (unsigned app warning)
- **Config not found:** App creates `~/.config/reviewinator/config.yaml` on first run
- **GitHub token issues:** User needs to update config with valid token

## Future Enhancements

### GitHub Actions Automation

Could add later:
- Workflow triggered by pushing to main or creating tags
- Automated builds on macOS runner
- Eliminates need for local `make release`

### App Updates

Could add later:
- Auto-update check on launch
- Download new versions from GitHub releases
- Notify user when update available

### Code Signing

Could add later if distributing widely:
- Apple Developer account ($99/year)
- Code sign with `codesign`
- Notarize with `notarytool`
- Eliminates security warnings

## Migration Notes

- **No breaking changes:** Existing `make run` continues to work for development
- **New dependencies:** py2app, tomli, tomli-w added as dev dependencies
- **New files:** setup.py, scripts/bump_version.py
- **Updated Makefile:** Adds build, release, _package, _publish targets

## Example Workflow

```bash
# One-time setup
brew install gh
gh auth login
uv sync --all-extras

# Development
make test          # Run tests
make build         # Build app locally
open dist/Reviewinator.app  # Test it

# Release (when ready)
make release       # Bumps 0.1.0 → 0.2.0, builds, publishes
git push && git push --tags

# User downloads Reviewinator-v0.2.0.app.zip from GitHub
# Unzips, opens, adds to Login Items
```
