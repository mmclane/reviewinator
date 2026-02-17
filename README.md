# Reviewinator

A macOS menu bar app that shows pending GitHub PR reviews.

## Features

- Menu bar icon with count badge (🔴 3) or checkmark (✓) when clear
- PRs grouped by repository in dropdown menu
- Click any PR to open it in your browser
- macOS notifications for new review requests
- Automatic polling every 5 minutes (configurable)
- Filters to repos you specify

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

## Configuration

Create `~/.config/reviewinator/config.yaml`:

```yaml
github_token: ghp_your_token_here
excluded_repos: []
excluded_review_teams: []
created_pr_filter: either
activity_lookback_days: 14
refresh_interval: 300
```

See [CLAUDE.md](CLAUDE.md) for detailed configuration options.

To get a GitHub token:
1. Go to GitHub → Settings → Developer settings → Personal access tokens
2. Generate a new token with `repo` scope
3. Copy the token to your config file

## Usage

```bash
make run
```

The app will appear in your menu bar. Click the icon to see pending reviews.

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

## Architecture

- **app.py** - Main rumps menu bar app
- **github_client.py** - GitHub API wrapper
- **config.py** - YAML config loading
- **cache.py** - Tracks seen PRs to prevent notification spam
- **notifications.py** - macOS notifications via pync
