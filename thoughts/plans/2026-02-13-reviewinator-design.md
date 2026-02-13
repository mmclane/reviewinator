# Reviewinator Design

A macOS menu bar app that shows pending GitHub PR reviews.

## Overview

- **Platform:** macOS menu bar app (Python + rumps)
- **Source:** GitHub PRs where user is a requested reviewer
- **Scope:** Filtered to repos specified in config file
- **Refresh:** Every 5 minutes (configurable)
- **Auth:** Personal Access Token

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Reviewinator                             │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────┐ │
│  │   rumps     │────│  GitHub     │────│  Notification   │ │
│  │  Menu Bar   │    │  Poller     │    │  Manager        │ │
│  └─────────────┘    └─────────────┘    └─────────────────┘ │
│         │                  │                    │           │
│         └──────────────────┼────────────────────┘           │
│                            │                                │
│              ┌─────────────┼─────────────┐                  │
│              │             │             │                  │
│      ┌───────▼───────┐ ┌───▼───────┐                        │
│      │  PR State     │ │  Config   │                        │
│      │  (in-memory)  │ │  (YAML)   │                        │
│      └───────────────┘ └───────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

### Components

- **Menu Bar (rumps):** Displays icon with count badge + color, renders dropdown menu
- **GitHub Poller:** Background timer fetching review requests via PyGithub
- **Notification Manager:** Triggers macOS notifications for new PRs
- **PR State:** In-memory tracking of current PRs
- **Config:** YAML file with GitHub token and repo list

## Menu Bar UI

### Icon Display

- Count badge showing number of pending reviews
- Color indicator: green = no reviews, red = reviews pending

### Dropdown Menu

```
┌─────────────────────────────────────────────────────┐
│ 𝗼𝗿𝗴/𝗿𝗲𝗽𝗼𝟭:                                           │
│   #142 Fix login bug (alice, 2h ago)                │
│   #138 Add feature (bob, 1d ago)                    │
│ 𝗼𝗿𝗴/𝗿𝗲𝗽𝗼𝟮:                                           │
│   #89 Fix weird bug (charlie, 3d ago)               │
│   #87 Other weird bug (alice, 5d ago)               │
│ ─────────────────────────────────────────────────── │
│ Check Now                                           │
│ ─────────────────────────────────────────────────── │
│ Quit                                                │
└─────────────────────────────────────────────────────┘
```

- Repo names are bold section headers with colon, not clickable
- PR format: `#<number> <title> (<author>, <age>)`
- Click PR to open in browser
- Repos with no pending reviews are hidden
- Empty state shows "No pending reviews"

### Age Formatting

- Under 1 hour: "Xm ago"
- Under 24 hours: "Xh ago"
- Under 7 days: "Xd ago"
- Over 7 days: "Xw ago"

## Configuration

### File Location

```
~/.config/reviewinator/
├── config.yaml          # User config (you manage)
└── cache.json           # PR state cache (auto-managed)
```

### config.yaml

```yaml
github_token: ghp_xxxxxxxxxxxx
repos:
  - owner/repo1
  - owner/repo2
  - org/repo3
refresh_interval: 300  # seconds (optional, defaults to 300)
```

### cache.json

```json
{
  "last_checked": "2026-02-13T10:30:00Z",
  "seen_prs": [142, 138, 89, 87, 23]
}
```

Stores PR IDs we've already notified about. Prevents notification spam on restart.

## Data Flow

### Startup Sequence

1. Load config from `~/.config/reviewinator/config.yaml`
2. Validate GitHub token (fail fast with error notification if invalid)
3. Load cache from `cache.json`
4. Initial fetch of PRs where you're a requested reviewer
5. Filter to configured repos
6. Notify only for PRs not in `seen_prs`
7. Display menu bar icon with count
8. Start polling timer

### Polling Cycle

```
Timer fires ──▶ Fetch PRs ──▶ Filter to config repos
                                      │
                                      ▼
Update menu ◀── Send notifs ◀── Diff against previous
bar & list      for new PRs     (update cache)
```

### GitHub API Usage

- Search query: `review-requested:<username>`
- Filtered client-side to repos in config
- ~2 API calls per poll, well within rate limits

### Error Handling

- Network failure: Keep showing stale data, show warning indicator
- Invalid token: Error notification on startup, quit
- API rate limit: Back off polling, show warning in dropdown

## Notifications

### When Notifications Fire

- New PR appears that's not in `seen_prs` cache
- Only on poll cycles, not on initial startup

### Notification Content

```
┌─────────────────────────────────────────┐
│ New Review Request                      │
│ org/repo1: #142 Fix login bug           │
│ From: alice                             │
└─────────────────────────────────────────┘
```

### Behavior

- Click notification opens PR in browser
- Multiple new PRs: one notification per PR
- Uses `pync` library (wrapper around macOS terminal-notifier)

### Cache Behavior

- On startup: Load cache, fetch PRs, notify only for new ones
- On poll: Update cache with any new PR IDs
- Cleanup: Remove IDs from cache if PR no longer in review queue

## Project Structure

```
reviewinator/
├── pyproject.toml           # Project config, dependencies
├── Makefile                 # Common commands
├── src/
│   └── reviewinator/
│       ├── __init__.py
│       ├── app.py           # Main entry point, rumps app
│       ├── github_client.py # GitHub API wrapper
│       ├── config.py        # Load/validate config.yaml
│       ├── cache.py         # Read/write cache.json
│       └── notifications.py # macOS notification wrapper
├── tests/
│   ├── conftest.py          # Shared fixtures
│   ├── test_config.py
│   ├── test_cache.py
│   ├── test_github_client.py
│   └── test_notifications.py
└── README.md
```

## Dependencies

```toml
[project]
dependencies = [
    "rumps",      # macOS menu bar
    "PyGithub",   # GitHub API
    "pync",       # macOS notifications
    "pyyaml",     # Config file parsing
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-cov",
    "ruff",       # Linting & formatting
]
```

## Makefile

```makefile
.PHONY: setup test lint run clean

setup:
	uv sync --all-extras

test:
	uv run pytest tests/ -v

test-cov:
	uv run pytest tests/ -v --cov=src/reviewinator --cov-report=term-missing

lint:
	uv run ruff check src/ tests/
	uv run ruff format --check src/ tests/

format:
	uv run ruff format src/ tests/
	uv run ruff check --fix src/ tests/

run:
	uv run python -m reviewinator

clean:
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage
```

## Development Workflow

Using TDD:

1. Write failing test
2. Implement minimal code to pass
3. Refactor
4. Run `make lint` before commits

## First-Time Setup

1. Create `~/.config/reviewinator/config.yaml`
2. Add GitHub PAT with `repo` scope
3. Add repos to monitor
4. Run `make setup && make run`
