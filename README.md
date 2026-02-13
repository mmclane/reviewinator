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

```bash
# Clone the repo
git clone https://github.com/yourusername/reviewinator.git
cd reviewinator

# Install dependencies
make setup
```

## Configuration

Create `~/.config/reviewinator/config.yaml`:

```yaml
github_token: ghp_your_token_here
repos:
  - owner/repo1
  - org/repo2
refresh_interval: 300  # optional, defaults to 300 seconds
```

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

```bash
make setup      # Install dependencies
make test       # Run tests
make test-cov   # Run tests with coverage
make lint       # Check linting
make format     # Auto-fix formatting
```

## Architecture

- **app.py** - Main rumps menu bar app
- **github_client.py** - GitHub API wrapper
- **config.py** - YAML config loading
- **cache.py** - Tracks seen PRs to prevent notification spam
- **notifications.py** - macOS notifications via pync
