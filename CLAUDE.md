# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reviewinator is a macOS menu bar app that shows pending GitHub PR reviews. It polls GitHub for PRs where you're requested as a reviewer and PRs you've created, excluding configured repos, and sends macOS notifications for new review requests.

## Development Commands

```bash
make setup      # Install dependencies with uv
make test       # Run tests
make test-cov   # Run tests with coverage
make lint       # Check linting and formatting
make format     # Auto-fix linting and formatting
make run        # Run the app
make clean      # Clean build artifacts
```

## Architecture

- **app.py** - Main rumps menu bar app, orchestrates polling and UI
- **github_client.py** - GitHub API wrapper using PyGithub, fetches review requests
- **config.py** - Loads and validates `~/.config/reviewinator/config.yaml`
- **cache.py** - Persists seen PR IDs to `~/.config/reviewinator/cache.json`
- **notifications.py** - Sends macOS notifications via pync

## Development Workflow

Using TDD:
1. Write failing test
2. Implement minimal code to pass
3. Refactor
4. Run `make lint` before commits

## Configuration

Create `~/.config/reviewinator/config.yaml`:
```yaml
github_token: ghp_your_token_here
excluded_repos:
  - owner/archived-repo
  - org/old-project
created_pr_filter: either  # Options: all, waiting, needs_attention, either
refresh_interval: 300  # optional, defaults to 300 seconds
```

The `excluded_repos` field is optional and lists repos to exclude from tracking.
The `created_pr_filter` field controls which of your created PRs to show:
- `either` (default): Show PRs waiting for review OR needing changes
- `waiting`: Show only PRs waiting for initial review
- `needs_attention`: Show only PRs with changes requested
- `all`: Show all your open PRs
