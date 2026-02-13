# Reviewinator Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a macOS menu bar app that shows pending GitHub PR reviews with notifications.

**Architecture:** Python app using rumps for menu bar UI, PyGithub for GitHub API, pync for notifications. Config stored in YAML, PR cache in JSON. Background polling every 5 minutes.

**Tech Stack:** Python 3.11+, rumps, PyGithub, pync, pyyaml, pytest, ruff, uv

---

## Task 1: Project Scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `Makefile`
- Create: `src/reviewinator/__init__.py`
- Create: `tests/__init__.py`

**Step 1: Create pyproject.toml**

```toml
[project]
name = "reviewinator"
version = "0.1.0"
description = "macOS menu bar app showing pending GitHub PR reviews"
requires-python = ">=3.11"
dependencies = [
    "rumps>=0.4.0",
    "PyGithub>=2.1.0",
    "pync>=2.0.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.1.0",
]

[project.scripts]
reviewinator = "reviewinator.app:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/reviewinator"]

[tool.ruff]
line-length = 100
src = ["src", "tests"]

[tool.ruff.lint]
select = ["E", "F", "I", "W"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

**Step 2: Create Makefile**

```makefile
.PHONY: setup test test-cov lint format run clean

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
	rm -rf .pytest_cache .ruff_cache __pycache__ .coverage dist build *.egg-info
```

**Step 3: Create package structure**

Create `src/reviewinator/__init__.py`:
```python
"""Reviewinator - macOS menu bar app for GitHub PR reviews."""

__version__ = "0.1.0"
```

Create `tests/__init__.py`:
```python
"""Reviewinator test suite."""
```

**Step 4: Initialize uv and verify setup**

Run: `uv sync --all-extras`
Expected: Dependencies installed successfully

**Step 5: Verify tests run (empty)**

Run: `make test`
Expected: "no tests ran" or similar (no tests yet)

**Step 6: Commit**

```bash
git add pyproject.toml Makefile src/ tests/
git commit -m "feat: scaffold project with pyproject.toml and Makefile"
```

---

## Task 2: Config Module

**Files:**
- Create: `src/reviewinator/config.py`
- Create: `tests/test_config.py`

**Step 1: Write failing test for config loading**

Create `tests/test_config.py`:
```python
"""Tests for config module."""

import pytest
from pathlib import Path
from reviewinator.config import load_config, Config, ConfigError


class TestLoadConfig:
    """Tests for load_config function."""

    def test_load_valid_config(self, tmp_path: Path) -> None:
        """Should load a valid config file."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos:
  - owner/repo1
  - org/repo2
refresh_interval: 600
""")
        config = load_config(config_file)

        assert config.github_token == "ghp_test123"
        assert config.repos == ["owner/repo1", "org/repo2"]
        assert config.refresh_interval == 600

    def test_load_config_default_refresh_interval(self, tmp_path: Path) -> None:
        """Should use default refresh_interval when not specified."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos:
  - owner/repo1
""")
        config = load_config(config_file)

        assert config.refresh_interval == 300

    def test_load_config_missing_token_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when github_token is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
repos:
  - owner/repo1
""")
        with pytest.raises(ConfigError, match="github_token"):
            load_config(config_file)

    def test_load_config_missing_repos_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when repos is missing."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
""")
        with pytest.raises(ConfigError, match="repos"):
            load_config(config_file)

    def test_load_config_empty_repos_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when repos list is empty."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
github_token: ghp_test123
repos: []
""")
        with pytest.raises(ConfigError, match="repos"):
            load_config(config_file)

    def test_load_config_file_not_found_raises(self, tmp_path: Path) -> None:
        """Should raise ConfigError when file doesn't exist."""
        config_file = tmp_path / "nonexistent.yaml"

        with pytest.raises(ConfigError, match="not found"):
            load_config(config_file)


class TestConfigPaths:
    """Tests for config path utilities."""

    def test_default_config_dir(self) -> None:
        """Should return ~/.config/reviewinator as default."""
        from reviewinator.config import get_config_dir

        config_dir = get_config_dir()
        assert config_dir == Path.home() / ".config" / "reviewinator"

    def test_default_config_path(self) -> None:
        """Should return ~/.config/reviewinator/config.yaml as default."""
        from reviewinator.config import get_config_path

        config_path = get_config_path()
        assert config_path == Path.home() / ".config" / "reviewinator" / "config.yaml"
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "ModuleNotFoundError" or "ImportError"

**Step 3: Write minimal implementation**

Create `src/reviewinator/config.py`:
```python
"""Configuration loading and validation."""

from dataclasses import dataclass
from pathlib import Path

import yaml


class ConfigError(Exception):
    """Raised when configuration is invalid or missing."""


@dataclass
class Config:
    """Application configuration."""

    github_token: str
    repos: list[str]
    refresh_interval: int = 300


def get_config_dir() -> Path:
    """Return the default configuration directory."""
    return Path.home() / ".config" / "reviewinator"


def get_config_path() -> Path:
    """Return the default configuration file path."""
    return get_config_dir() / "config.yaml"


def load_config(config_path: Path) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If config file is missing or invalid.
    """
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    with open(config_path) as f:
        data = yaml.safe_load(f)

    if not data:
        data = {}

    if "github_token" not in data:
        raise ConfigError("Missing required field: github_token")

    if "repos" not in data or not data["repos"]:
        raise ConfigError("Missing or empty required field: repos")

    return Config(
        github_token=data["github_token"],
        repos=data["repos"],
        refresh_interval=data.get("refresh_interval", 300),
    )
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: All tests PASS

**Step 5: Run lint**

Run: `make lint`
Expected: No errors (fix any issues)

**Step 6: Commit**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: add config module with YAML loading and validation"
```

---

## Task 3: Cache Module

**Files:**
- Create: `src/reviewinator/cache.py`
- Create: `tests/test_cache.py`

**Step 1: Write failing test for cache**

Create `tests/test_cache.py`:
```python
"""Tests for cache module."""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from reviewinator.cache import Cache, load_cache, save_cache


class TestCache:
    """Tests for Cache dataclass."""

    def test_cache_defaults(self) -> None:
        """Should have empty defaults."""
        cache = Cache()
        assert cache.seen_prs == set()
        assert cache.last_checked is None

    def test_cache_with_values(self) -> None:
        """Should store provided values."""
        now = datetime.now(timezone.utc)
        cache = Cache(seen_prs={1, 2, 3}, last_checked=now)
        assert cache.seen_prs == {1, 2, 3}
        assert cache.last_checked == now


class TestLoadCache:
    """Tests for load_cache function."""

    def test_load_existing_cache(self, tmp_path: Path) -> None:
        """Should load cache from existing file."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(json.dumps({
            "last_checked": "2026-02-13T10:30:00+00:00",
            "seen_prs": [142, 138, 89]
        }))

        cache = load_cache(cache_file)

        assert cache.seen_prs == {142, 138, 89}
        assert cache.last_checked == datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)

    def test_load_nonexistent_cache_returns_empty(self, tmp_path: Path) -> None:
        """Should return empty cache when file doesn't exist."""
        cache_file = tmp_path / "nonexistent.json"

        cache = load_cache(cache_file)

        assert cache.seen_prs == set()
        assert cache.last_checked is None

    def test_load_corrupted_cache_returns_empty(self, tmp_path: Path) -> None:
        """Should return empty cache when file is corrupted."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json {{{")

        cache = load_cache(cache_file)

        assert cache.seen_prs == set()
        assert cache.last_checked is None


class TestSaveCache:
    """Tests for save_cache function."""

    def test_save_cache(self, tmp_path: Path) -> None:
        """Should save cache to file."""
        cache_file = tmp_path / "cache.json"
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        cache = Cache(seen_prs={1, 2, 3}, last_checked=now)

        save_cache(cache, cache_file)

        data = json.loads(cache_file.read_text())
        assert set(data["seen_prs"]) == {1, 2, 3}
        assert data["last_checked"] == "2026-02-13T10:30:00+00:00"

    def test_save_cache_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        cache_file = tmp_path / "subdir" / "cache.json"
        cache = Cache(seen_prs={1}, last_checked=None)

        save_cache(cache, cache_file)

        assert cache_file.exists()

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Should preserve data through save/load cycle."""
        cache_file = tmp_path / "cache.json"
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        original = Cache(seen_prs={10, 20, 30}, last_checked=now)

        save_cache(original, cache_file)
        loaded = load_cache(cache_file)

        assert loaded.seen_prs == original.seen_prs
        assert loaded.last_checked == original.last_checked


class TestCacheHelpers:
    """Tests for cache helper functions."""

    def test_get_cache_path(self) -> None:
        """Should return ~/.config/reviewinator/cache.json."""
        from reviewinator.cache import get_cache_path

        cache_path = get_cache_path()
        assert cache_path == Path.home() / ".config" / "reviewinator" / "cache.json"
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**

Create `src/reviewinator/cache.py`:
```python
"""Cache for tracking seen PRs."""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class Cache:
    """Stores state about PRs we've already seen."""

    seen_prs: set[int] = field(default_factory=set)
    last_checked: datetime | None = None


def get_cache_path() -> Path:
    """Return the default cache file path."""
    return Path.home() / ".config" / "reviewinator" / "cache.json"


def load_cache(cache_path: Path) -> Cache:
    """Load cache from file.

    Args:
        cache_path: Path to the cache.json file.

    Returns:
        Cache object. Returns empty cache if file doesn't exist or is corrupted.
    """
    if not cache_path.exists():
        return Cache()

    try:
        with open(cache_path) as f:
            data = json.load(f)

        last_checked = None
        if data.get("last_checked"):
            last_checked = datetime.fromisoformat(data["last_checked"])

        return Cache(
            seen_prs=set(data.get("seen_prs", [])),
            last_checked=last_checked,
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return Cache()


def save_cache(cache: Cache, cache_path: Path) -> None:
    """Save cache to file.

    Args:
        cache: Cache object to save.
        cache_path: Path to save to.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "seen_prs": list(cache.seen_prs),
        "last_checked": cache.last_checked.isoformat() if cache.last_checked else None,
    }

    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: All tests PASS

**Step 5: Run lint**

Run: `make lint`
Expected: No errors

**Step 6: Commit**

```bash
git add src/reviewinator/cache.py tests/test_cache.py
git commit -m "feat: add cache module for tracking seen PRs"
```

---

## Task 4: GitHub Client Module

**Files:**
- Create: `src/reviewinator/github_client.py`
- Create: `tests/test_github_client.py`

**Step 1: Write failing test for PR data model and formatting**

Create `tests/test_github_client.py`:
```python
"""Tests for GitHub client module."""

from datetime import datetime, timezone

import pytest

from reviewinator.github_client import PullRequest, format_age


class TestPullRequest:
    """Tests for PullRequest dataclass."""

    def test_pull_request_creation(self) -> None:
        """Should create PR with all fields."""
        pr = PullRequest(
            id=12345,
            number=142,
            title="Fix login bug",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/142",
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        )

        assert pr.id == 12345
        assert pr.number == 142
        assert pr.title == "Fix login bug"
        assert pr.author == "alice"
        assert pr.repo == "org/repo1"
        assert pr.url == "https://github.com/org/repo1/pull/142"


class TestFormatAge:
    """Tests for format_age function."""

    def test_format_age_minutes(self) -> None:
        """Should format as Xm ago for < 1 hour."""
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        created = datetime(2026, 2, 13, 10, 15, 0, tzinfo=timezone.utc)

        assert format_age(created, now) == "15m ago"

    def test_format_age_hours(self) -> None:
        """Should format as Xh ago for < 24 hours."""
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        created = datetime(2026, 2, 13, 5, 30, 0, tzinfo=timezone.utc)

        assert format_age(created, now) == "5h ago"

    def test_format_age_days(self) -> None:
        """Should format as Xd ago for < 7 days."""
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        created = datetime(2026, 2, 10, 10, 30, 0, tzinfo=timezone.utc)

        assert format_age(created, now) == "3d ago"

    def test_format_age_weeks(self) -> None:
        """Should format as Xw ago for >= 7 days."""
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        created = datetime(2026, 1, 30, 10, 30, 0, tzinfo=timezone.utc)

        assert format_age(created, now) == "2w ago"

    def test_format_age_just_created(self) -> None:
        """Should show 0m ago for just created."""
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        created = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)

        assert format_age(created, now) == "0m ago"


class TestPullRequestFormatting:
    """Tests for PR display formatting."""

    def test_format_menu_item(self) -> None:
        """Should format PR for menu display."""
        now = datetime(2026, 2, 13, 12, 0, 0, tzinfo=timezone.utc)
        pr = PullRequest(
            id=12345,
            number=142,
            title="Fix login bug",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/142",
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
        )

        formatted = pr.format_menu_item(now)

        assert formatted == "#142 Fix login bug (alice, 2h ago)"
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**

Create `src/reviewinator/github_client.py`:
```python
"""GitHub API client for fetching PR review requests."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class PullRequest:
    """Represents a pull request awaiting review."""

    id: int
    number: int
    title: str
    author: str
    repo: str
    url: str
    created_at: datetime

    def format_menu_item(self, now: datetime | None = None) -> str:
        """Format PR for menu display.

        Args:
            now: Current time for age calculation. Defaults to UTC now.

        Returns:
            Formatted string like "#142 Fix login bug (alice, 2h ago)"
        """
        if now is None:
            now = datetime.now(timezone.utc)
        age = format_age(self.created_at, now)
        return f"#{self.number} {self.title} ({self.author}, {age})"


def format_age(created_at: datetime, now: datetime) -> str:
    """Format time difference as human-readable age.

    Args:
        created_at: When the PR was created.
        now: Current time.

    Returns:
        Formatted age string like "2h ago", "3d ago", etc.
    """
    delta = now - created_at
    total_minutes = int(delta.total_seconds() / 60)

    if total_minutes < 60:
        return f"{total_minutes}m ago"

    total_hours = total_minutes // 60
    if total_hours < 24:
        return f"{total_hours}h ago"

    total_days = total_hours // 24
    if total_days < 7:
        return f"{total_days}d ago"

    total_weeks = total_days // 7
    return f"{total_weeks}w ago"
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: All tests PASS

**Step 5: Run lint**

Run: `make lint`
Expected: No errors

**Step 6: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add PullRequest model and age formatting"
```

---

## Task 5: GitHub Client - Fetch PRs

**Files:**
- Modify: `src/reviewinator/github_client.py`
- Modify: `tests/test_github_client.py`

**Step 1: Write failing test for fetching PRs**

Add to `tests/test_github_client.py`:
```python
from unittest.mock import MagicMock, patch


class TestGitHubClient:
    """Tests for GitHubClient class."""

    def test_fetch_review_requests_filters_to_configured_repos(self) -> None:
        """Should only return PRs from configured repos."""
        from reviewinator.github_client import GitHubClient

        mock_github = MagicMock()
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        # Create mock issues (GitHub search returns issues for PRs)
        mock_issue1 = MagicMock()
        mock_issue1.id = 1
        mock_issue1.number = 10
        mock_issue1.title = "PR in configured repo"
        mock_issue1.user.login = "alice"
        mock_issue1.repository.full_name = "org/repo1"
        mock_issue1.html_url = "https://github.com/org/repo1/pull/10"
        mock_issue1.created_at = datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc)

        mock_issue2 = MagicMock()
        mock_issue2.id = 2
        mock_issue2.number = 20
        mock_issue2.title = "PR in non-configured repo"
        mock_issue2.user.login = "bob"
        mock_issue2.repository.full_name = "other/repo"
        mock_issue2.html_url = "https://github.com/other/repo/pull/20"
        mock_issue2.created_at = datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc)

        mock_github.search_issues.return_value = [mock_issue1, mock_issue2]

        client = GitHubClient(mock_github, repos=["org/repo1", "org/repo2"])
        prs = client.fetch_review_requests()

        assert len(prs) == 1
        assert prs[0].repo == "org/repo1"
        assert prs[0].number == 10

    def test_fetch_review_requests_searches_for_user(self) -> None:
        """Should search for PRs requesting review from current user."""
        from reviewinator.github_client import GitHubClient

        mock_github = MagicMock()
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user
        mock_github.search_issues.return_value = []

        client = GitHubClient(mock_github, repos=["org/repo1"])
        client.fetch_review_requests()

        mock_github.search_issues.assert_called_once()
        call_args = mock_github.search_issues.call_args[0][0]
        assert "review-requested:testuser" in call_args
        assert "is:pr" in call_args
        assert "is:open" in call_args
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "ImportError" for GitHubClient

**Step 3: Write minimal implementation**

Add to `src/reviewinator/github_client.py`:
```python
from github import Github


class GitHubClient:
    """Client for fetching PR review requests from GitHub."""

    def __init__(self, github: Github, repos: list[str]) -> None:
        """Initialize the client.

        Args:
            github: Authenticated PyGithub instance.
            repos: List of repos to filter to (e.g., ["org/repo1", "owner/repo2"]).
        """
        self._github = github
        self._repos = set(repos)
        self._username: str | None = None

    @property
    def username(self) -> str:
        """Get the authenticated user's username (cached)."""
        if self._username is None:
            self._username = self._github.get_user().login
        return self._username

    def fetch_review_requests(self) -> list[PullRequest]:
        """Fetch PRs where the current user is requested as reviewer.

        Returns:
            List of PullRequest objects, filtered to configured repos.
        """
        query = f"is:pr is:open review-requested:{self.username}"
        issues = self._github.search_issues(query)

        prs = []
        for issue in issues:
            repo_name = issue.repository.full_name
            if repo_name not in self._repos:
                continue

            pr = PullRequest(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                author=issue.user.login,
                repo=repo_name,
                url=issue.html_url,
                created_at=issue.created_at.replace(tzinfo=timezone.utc),
            )
            prs.append(pr)

        return prs
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: All tests PASS

**Step 5: Run lint**

Run: `make lint`
Expected: No errors

**Step 6: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add GitHubClient for fetching review requests"
```

---

## Task 6: Notifications Module

**Files:**
- Create: `src/reviewinator/notifications.py`
- Create: `tests/test_notifications.py`

**Step 1: Write failing test for notifications**

Create `tests/test_notifications.py`:
```python
"""Tests for notifications module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from reviewinator.github_client import PullRequest
from reviewinator.notifications import notify_new_pr, find_new_prs


class TestFindNewPrs:
    """Tests for find_new_prs function."""

    def test_find_new_prs_identifies_unseen(self) -> None:
        """Should return PRs not in seen set."""
        pr1 = PullRequest(
            id=1, number=10, title="PR 1", author="alice",
            repo="org/repo1", url="https://github.com/org/repo1/pull/10",
            created_at=datetime.now(timezone.utc),
        )
        pr2 = PullRequest(
            id=2, number=20, title="PR 2", author="bob",
            repo="org/repo1", url="https://github.com/org/repo1/pull/20",
            created_at=datetime.now(timezone.utc),
        )

        current_prs = [pr1, pr2]
        seen_ids = {1}  # PR 1 already seen

        new_prs = find_new_prs(current_prs, seen_ids)

        assert len(new_prs) == 1
        assert new_prs[0].id == 2

    def test_find_new_prs_empty_when_all_seen(self) -> None:
        """Should return empty list when all PRs are seen."""
        pr1 = PullRequest(
            id=1, number=10, title="PR 1", author="alice",
            repo="org/repo1", url="https://github.com/org/repo1/pull/10",
            created_at=datetime.now(timezone.utc),
        )

        new_prs = find_new_prs([pr1], {1})

        assert new_prs == []


class TestNotifyNewPr:
    """Tests for notify_new_pr function."""

    @patch("reviewinator.notifications.pync")
    def test_notify_sends_notification(self, mock_pync: MagicMock) -> None:
        """Should send macOS notification with PR details."""
        pr = PullRequest(
            id=1, number=142, title="Fix login bug", author="alice",
            repo="org/repo1", url="https://github.com/org/repo1/pull/142",
            created_at=datetime.now(timezone.utc),
        )

        notify_new_pr(pr)

        mock_pync.notify.assert_called_once()
        call_kwargs = mock_pync.notify.call_args[1]
        assert "org/repo1" in call_kwargs["title"]
        assert "#142" in call_kwargs["message"]
        assert "Fix login bug" in call_kwargs["message"]
        assert call_kwargs["open"] == pr.url

    @patch("reviewinator.notifications.pync")
    def test_notify_handles_pync_error(self, mock_pync: MagicMock) -> None:
        """Should not raise when pync fails."""
        mock_pync.notify.side_effect = Exception("notification failed")
        pr = PullRequest(
            id=1, number=142, title="Fix login bug", author="alice",
            repo="org/repo1", url="https://github.com/org/repo1/pull/142",
            created_at=datetime.now(timezone.utc),
        )

        # Should not raise
        notify_new_pr(pr)
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "ImportError"

**Step 3: Write minimal implementation**

Create `src/reviewinator/notifications.py`:
```python
"""macOS notifications for new PR review requests."""

import pync

from reviewinator.github_client import PullRequest


def find_new_prs(current_prs: list[PullRequest], seen_ids: set[int]) -> list[PullRequest]:
    """Find PRs that haven't been seen before.

    Args:
        current_prs: List of current PRs from GitHub.
        seen_ids: Set of PR IDs we've already notified about.

    Returns:
        List of PRs not in seen_ids.
    """
    return [pr for pr in current_prs if pr.id not in seen_ids]


def notify_new_pr(pr: PullRequest) -> None:
    """Send macOS notification for a new PR.

    Args:
        pr: The pull request to notify about.
    """
    try:
        pync.notify(
            message=f"#{pr.number} {pr.title}\nFrom: {pr.author}",
            title=f"New Review Request: {pr.repo}",
            open=pr.url,
        )
    except Exception:
        # Don't crash if notifications fail
        pass
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: All tests PASS

**Step 5: Run lint**

Run: `make lint`
Expected: No errors

**Step 6: Commit**

```bash
git add src/reviewinator/notifications.py tests/test_notifications.py
git commit -m "feat: add notifications module for macOS alerts"
```

---

## Task 7: Menu Bar App - Core Structure

**Files:**
- Create: `src/reviewinator/app.py`
- Create: `src/reviewinator/__main__.py`

**Step 1: Create main app module**

Create `src/reviewinator/app.py`:
```python
"""Main menu bar application."""

import webbrowser
from datetime import datetime, timezone
from itertools import groupby

import rumps
from github import Github

from reviewinator.cache import Cache, get_cache_path, load_cache, save_cache
from reviewinator.config import Config, ConfigError, get_config_path, load_config
from reviewinator.github_client import GitHubClient, PullRequest
from reviewinator.notifications import find_new_prs, notify_new_pr


class ReviewinatorApp(rumps.App):
    """Menu bar application for GitHub PR reviews."""

    def __init__(self, config: Config) -> None:
        """Initialize the app.

        Args:
            config: Application configuration.
        """
        super().__init__("Reviewinator", quit_button=None)
        self.config = config
        self.cache = load_cache(get_cache_path())
        self.prs: list[PullRequest] = []
        self.is_first_run = True

        # Set up GitHub client
        github = Github(config.github_token)
        self.client = GitHubClient(github, config.repos)

        # Set up timer for polling
        self.timer = rumps.Timer(self._poll, config.refresh_interval)

    def _update_menu(self) -> None:
        """Rebuild the menu with current PRs."""
        self.menu.clear()

        if not self.prs:
            self.menu.add(rumps.MenuItem("No pending reviews", callback=None))
        else:
            # Group PRs by repo
            sorted_prs = sorted(self.prs, key=lambda p: p.repo)
            for repo, repo_prs in groupby(sorted_prs, key=lambda p: p.repo):
                # Bold repo header (using MenuItem with callback=None makes it non-clickable)
                header = rumps.MenuItem(f"{repo}:", callback=None)
                self.menu.add(header)

                # PR items under the repo
                now = datetime.now(timezone.utc)
                for pr in repo_prs:
                    item = rumps.MenuItem(
                        f"  {pr.format_menu_item(now)}",
                        callback=self._make_pr_callback(pr.url),
                    )
                    self.menu.add(item)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Check Now", callback=self._on_check_now))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=self._on_quit))

        # Update title with count and color indicator
        count = len(self.prs)
        if count == 0:
            self.title = "✓"  # Green check for no reviews
        else:
            self.title = f"🔴 {count}"  # Red indicator with count

    def _make_pr_callback(self, url: str):
        """Create a callback that opens a URL."""
        def callback(_):
            webbrowser.open(url)
        return callback

    def _poll(self, _=None) -> None:
        """Fetch PRs and update state."""
        try:
            self.prs = self.client.fetch_review_requests()

            # Find new PRs and notify (skip on first run)
            if not self.is_first_run:
                new_prs = find_new_prs(self.prs, self.cache.seen_prs)
                for pr in new_prs:
                    notify_new_pr(pr)

            # Update cache
            self.cache.seen_prs = {pr.id for pr in self.prs}
            self.cache.last_checked = datetime.now(timezone.utc)
            save_cache(self.cache, get_cache_path())

            self.is_first_run = False

        except Exception as e:
            # On error, keep showing stale data
            rumps.notification(
                title="Reviewinator Error",
                subtitle="Failed to fetch PRs",
                message=str(e),
            )

        self._update_menu()

    @rumps.clicked("Check Now")
    def _on_check_now(self, _) -> None:
        """Handle Check Now menu item."""
        self._poll()

    @rumps.clicked("Quit")
    def _on_quit(self, _) -> None:
        """Handle Quit menu item."""
        rumps.quit_application()

    def run(self) -> None:
        """Start the application."""
        # Do initial poll
        self._poll()
        # Start timer
        self.timer.start()
        # Run the app
        super().run()


def main() -> None:
    """Entry point for the application."""
    try:
        config = load_config(get_config_path())
    except ConfigError as e:
        rumps.notification(
            title="Reviewinator",
            subtitle="Configuration Error",
            message=str(e),
        )
        return

    app = ReviewinatorApp(config)
    app.run()


if __name__ == "__main__":
    main()
```

**Step 2: Create __main__.py for module execution**

Create `src/reviewinator/__main__.py`:
```python
"""Allow running as python -m reviewinator."""

from reviewinator.app import main

if __name__ == "__main__":
    main()
```

**Step 3: Run lint**

Run: `make lint`
Expected: No errors

**Step 4: Commit**

```bash
git add src/reviewinator/app.py src/reviewinator/__main__.py
git commit -m "feat: add main menu bar app with polling and notifications"
```

---

## Task 8: App Integration Tests

**Files:**
- Create: `tests/test_app.py`
- Create: `tests/conftest.py`

**Step 1: Create shared fixtures**

Create `tests/conftest.py`:
```python
"""Shared test fixtures."""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from reviewinator.github_client import PullRequest


@pytest.fixture
def sample_pr() -> PullRequest:
    """Create a sample PR for testing."""
    return PullRequest(
        id=12345,
        number=142,
        title="Fix login bug",
        author="alice",
        repo="org/repo1",
        url="https://github.com/org/repo1/pull/142",
        created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
    )


@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    from reviewinator.config import Config
    return Config(
        github_token="ghp_test123",
        repos=["org/repo1", "org/repo2"],
        refresh_interval=300,
    )
```

**Step 2: Create app tests**

Create `tests/test_app.py`:
```python
"""Tests for the main app module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from reviewinator.config import Config
from reviewinator.github_client import PullRequest


class TestReviewinatorApp:
    """Tests for ReviewinatorApp class."""

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    def test_app_initialization(
        self, mock_load_cache: MagicMock, mock_github: MagicMock, sample_config: Config
    ) -> None:
        """Should initialize with config and empty state."""
        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache()

        app = ReviewinatorApp(sample_config)

        assert app.config == sample_config
        assert app.prs == []
        assert app.is_first_run is True

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    @patch("reviewinator.app.save_cache")
    def test_poll_updates_prs(
        self,
        mock_save_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_github: MagicMock,
        sample_config: Config,
        sample_pr: PullRequest,
    ) -> None:
        """Should update PRs after polling."""
        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache()

        app = ReviewinatorApp(sample_config)
        app.client.fetch_review_requests = MagicMock(return_value=[sample_pr])

        app._poll()

        assert len(app.prs) == 1
        assert app.prs[0] == sample_pr
        assert app.is_first_run is False

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    @patch("reviewinator.app.save_cache")
    @patch("reviewinator.app.notify_new_pr")
    def test_poll_notifies_new_prs_after_first_run(
        self,
        mock_notify: MagicMock,
        mock_save_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_github: MagicMock,
        sample_config: Config,
        sample_pr: PullRequest,
    ) -> None:
        """Should send notifications for new PRs after first run."""
        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache()

        app = ReviewinatorApp(sample_config)
        app.client.fetch_review_requests = MagicMock(return_value=[])

        # First run - no notifications
        app._poll()
        mock_notify.assert_not_called()

        # Second run with new PR - should notify
        app.client.fetch_review_requests = MagicMock(return_value=[sample_pr])
        app._poll()
        mock_notify.assert_called_once_with(sample_pr)

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    @patch("reviewinator.app.save_cache")
    @patch("reviewinator.app.notify_new_pr")
    def test_poll_skips_notification_on_first_run(
        self,
        mock_notify: MagicMock,
        mock_save_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_github: MagicMock,
        sample_config: Config,
        sample_pr: PullRequest,
    ) -> None:
        """Should not notify on first run even with PRs."""
        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache()

        app = ReviewinatorApp(sample_config)
        app.client.fetch_review_requests = MagicMock(return_value=[sample_pr])

        app._poll()

        mock_notify.assert_not_called()
```

**Step 3: Run tests**

Run: `make test`
Expected: All tests PASS

**Step 4: Run lint**

Run: `make lint`
Expected: No errors

**Step 5: Commit**

```bash
git add tests/conftest.py tests/test_app.py
git commit -m "test: add integration tests for main app"
```

---

## Task 9: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update CLAUDE.md with project details**

Replace contents of `CLAUDE.md`:
```markdown
# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reviewinator is a macOS menu bar app that shows pending GitHub PR reviews. It polls GitHub for PRs where you're requested as a reviewer, filters to configured repos, and sends macOS notifications for new review requests.

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
repos:
  - owner/repo1
  - org/repo2
refresh_interval: 300  # optional, defaults to 300 seconds
```
```

**Step 2: Run lint on any modified files**

Run: `make lint`
Expected: No errors

**Step 3: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with project details"
```

---

## Task 10: Final Verification

**Step 1: Run full test suite**

Run: `make test-cov`
Expected: All tests pass with good coverage

**Step 2: Run linting**

Run: `make lint`
Expected: No errors

**Step 3: Verify app runs (manual)**

Run: `make run`
Expected: Menu bar icon appears (will fail without config file, which is expected)

**Step 4: Final commit and summary**

```bash
git log --oneline -10
```

Review commits and verify all tasks complete.
