# Show Repos When Empty Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show a list of recently active repos when there are no pending PRs, providing visibility into monitored repos and quick access to their PR pages.

**Architecture:** Track repo activity timestamps in cache as PRs are fetched. When menu is empty, display repos active within configurable lookback window (default 14 days), sorted by recency, with smart limit of 20 repos.

**Tech Stack:** Python 3.12, PyGithub, pytest, YAML config, JSON cache

---

## Task 1: Add activity_lookback_days to Config

**Files:**
- Modify: `src/reviewinator/config.py:14-20`
- Test: `tests/test_config.py`

**Step 1: Write failing test for activity_lookback_days field**

Add to `tests/test_config.py`:

```python
def test_load_config_activity_lookback_days_defaults_to_14(tmp_path):
    """Test activity_lookback_days defaults to 14."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github_token: test_token\n")
    config = load_config(config_file)
    assert config.activity_lookback_days == 14


def test_load_config_activity_lookback_days_custom_value(tmp_path):
    """Test activity_lookback_days accepts custom positive integer."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
activity_lookback_days: 30
"""
    )
    config = load_config(config_file)
    assert config.activity_lookback_days == 30


def test_load_config_activity_lookback_days_rejects_negative(tmp_path):
    """Test activity_lookback_days rejects negative values."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
activity_lookback_days: -5
"""
    )
    with pytest.raises(ConfigError, match="activity_lookback_days must be a positive integer"):
        load_config(config_file)


def test_load_config_activity_lookback_days_rejects_zero(tmp_path):
    """Test activity_lookback_days rejects zero."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
activity_lookback_days: 0
"""
    )
    with pytest.raises(ConfigError, match="activity_lookback_days must be a positive integer"):
        load_config(config_file)
```

**Step 2: Run tests to verify they fail**

Run: `make test`
Expected: FAIL - `AttributeError: 'Config' object has no attribute 'activity_lookback_days'`

**Step 3: Add activity_lookback_days to Config dataclass**

In `src/reviewinator/config.py`, update Config dataclass (lines 14-20):

```python
@dataclass
class Config:
    """Application configuration."""

    github_token: str
    excluded_repos: list[str]
    created_pr_filter: str
    activity_lookback_days: int
    refresh_interval: int = 300
```

**Step 4: Update load_config to handle activity_lookback_days**

In `src/reviewinator/config.py`, update `load_config()` function (add after line 72):

```python
    activity_lookback_days = data.get("activity_lookback_days", 14)
    if not isinstance(activity_lookback_days, int) or activity_lookback_days <= 0:
        raise ConfigError("activity_lookback_days must be a positive integer")
```

And update the Config constructor call (around line 76):

```python
    return Config(
        github_token=data["github_token"],
        excluded_repos=excluded_repos,
        created_pr_filter=created_pr_filter,
        activity_lookback_days=activity_lookback_days,
        refresh_interval=refresh_interval,
    )
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_config.py -v`
Expected: All config tests pass

**Step 6: Commit config changes**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: add activity_lookback_days config field

Add configurable lookback window for showing repos with recent activity.
Defaults to 14 days, must be a positive integer.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Add repo_activity to Cache

**Files:**
- Modify: `src/reviewinator/cache.py:8-13`
- Test: `tests/test_cache.py`

**Step 1: Write failing test for repo_activity field**

Add to `tests/test_cache.py`:

```python
from datetime import datetime, timezone


def test_cache_with_repo_activity():
    """Test Cache with repo_activity field."""
    now = datetime.now(timezone.utc)
    cache = Cache(
        seen_prs={1, 2, 3},
        pr_statuses={1: "waiting", 2: "approved"},
        last_checked=now,
        repo_activity={"owner/repo1": now, "owner/repo2": now},
    )
    assert cache.repo_activity == {"owner/repo1": now, "owner/repo2": now}


def test_load_cache_with_repo_activity(tmp_path):
    """Test loading cache with repo_activity field."""
    cache_file = tmp_path / "cache.json"
    now = datetime.now(timezone.utc)
    cache_file.write_text(
        json.dumps({
            "seen_prs": [1, 2],
            "pr_statuses": {"1": "waiting"},
            "last_checked": now.isoformat(),
            "repo_activity": {
                "owner/repo1": now.isoformat(),
                "owner/repo2": now.isoformat(),
            }
        })
    )
    cache = load_cache(cache_file)
    assert len(cache.repo_activity) == 2
    assert "owner/repo1" in cache.repo_activity
    assert "owner/repo2" in cache.repo_activity


def test_load_cache_without_repo_activity_backward_compat(tmp_path):
    """Test loading old cache without repo_activity field (backward compatibility)."""
    cache_file = tmp_path / "cache.json"
    now = datetime.now(timezone.utc)
    cache_file.write_text(
        json.dumps({
            "seen_prs": [1, 2],
            "pr_statuses": {"1": "waiting"},
            "last_checked": now.isoformat(),
        })
    )
    cache = load_cache(cache_file)
    assert cache.repo_activity == {}


def test_save_cache_with_repo_activity(tmp_path):
    """Test saving cache with repo_activity field."""
    cache_file = tmp_path / "cache.json"
    now = datetime.now(timezone.utc)
    cache = Cache(
        seen_prs={1, 2},
        pr_statuses={1: "waiting"},
        last_checked=now,
        repo_activity={"owner/repo1": now, "owner/repo2": now},
    )
    save_cache(cache, cache_file)

    with cache_file.open() as f:
        data = json.load(f)

    assert "repo_activity" in data
    assert "owner/repo1" in data["repo_activity"]
    assert "owner/repo2" in data["repo_activity"]


def test_cache_repo_activity_roundtrip(tmp_path):
    """Test repo_activity survives save/load roundtrip."""
    cache_file = tmp_path / "cache.json"
    now = datetime.now(timezone.utc)
    original = Cache(
        seen_prs={1},
        pr_statuses={},
        last_checked=now,
        repo_activity={"owner/repo": now},
    )
    save_cache(original, cache_file)
    loaded = load_cache(cache_file)

    assert "owner/repo" in loaded.repo_activity
    # Datetimes should be equal (within a second due to JSON serialization)
    assert abs((loaded.repo_activity["owner/repo"] - now).total_seconds()) < 1
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cache.py -v`
Expected: FAIL - `TypeError: __init__() got an unexpected keyword argument 'repo_activity'`

**Step 3: Add repo_activity to Cache dataclass**

In `src/reviewinator/cache.py`, update Cache dataclass (lines 8-13):

```python
@dataclass
class Cache:
    """Cache for seen PRs and repo activity."""

    seen_prs: set[int]
    pr_statuses: dict[int, str]
    last_checked: datetime | None
    repo_activity: dict[str, datetime]
```

**Step 4: Update load_cache to handle repo_activity**

In `src/reviewinator/cache.py`, update `load_cache()` function (around line 34):

```python
def load_cache(cache_path: Path) -> Cache:
    """Load cache from a JSON file.

    Args:
        cache_path: Path to the cache.json file.

    Returns:
        Cache object, or empty cache if file doesn't exist or is corrupted.
    """
    if not cache_path.exists():
        return Cache(
            seen_prs=set(),
            pr_statuses={},
            last_checked=None,
            repo_activity={},
        )

    try:
        with cache_path.open() as f:
            data = json.load(f)

        seen_prs = set(data.get("seen_prs", []))
        pr_statuses = {int(k): v for k, v in data.get("pr_statuses", {}).items()}

        last_checked = None
        if "last_checked" in data and data["last_checked"]:
            last_checked = datetime.fromisoformat(data["last_checked"])

        # Load repo_activity with backward compatibility
        repo_activity = {}
        if "repo_activity" in data:
            for repo, timestamp_str in data["repo_activity"].items():
                try:
                    repo_activity[repo] = datetime.fromisoformat(timestamp_str)
                except (ValueError, TypeError):
                    # Skip malformed timestamps
                    pass

        return Cache(
            seen_prs=seen_prs,
            pr_statuses=pr_statuses,
            last_checked=last_checked,
            repo_activity=repo_activity,
        )
    except (json.JSONDecodeError, KeyError):
        # Return empty cache on corruption
        return Cache(
            seen_prs=set(),
            pr_statuses={},
            last_checked=None,
            repo_activity={},
        )
```

**Step 5: Update save_cache to persist repo_activity**

In `src/reviewinator/cache.py`, update `save_cache()` function:

```python
def save_cache(cache: Cache, cache_path: Path) -> None:
    """Save cache to a JSON file.

    Args:
        cache: Cache object to save.
        cache_path: Path to the cache.json file.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "seen_prs": list(cache.seen_prs),
        "pr_statuses": {str(k): v for k, v in cache.pr_statuses.items()},
        "last_checked": cache.last_checked.isoformat() if cache.last_checked else None,
        "repo_activity": {
            repo: timestamp.isoformat()
            for repo, timestamp in cache.repo_activity.items()
        },
    }

    with cache_path.open("w") as f:
        json.dump(data, f, indent=2)
```

**Step 6: Run tests to verify they pass**

Run: `pytest tests/test_cache.py -v`
Expected: All cache tests pass

**Step 7: Update tests/conftest.py fixture**

Update the `sample_cache` fixture in `tests/conftest.py` to include `repo_activity`:

```python
@pytest.fixture
def sample_cache():
    """Sample cache for testing."""
    return Cache(
        seen_prs={1, 2, 3},
        pr_statuses={1: "waiting", 2: "approved"},
        last_checked=datetime(2024, 1, 1, tzinfo=timezone.utc),
        repo_activity={},
    )
```

**Step 8: Run all tests to verify nothing broke**

Run: `make test`
Expected: All tests pass

**Step 9: Commit cache changes**

```bash
git add src/reviewinator/cache.py tests/test_cache.py tests/conftest.py
git commit -m "feat: add repo_activity to cache

Store repo activity timestamps to track which repos have had recent PRs.
Includes backward compatibility for old cache format.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Track repo activity during PR fetch

**Files:**
- Modify: `src/reviewinator/app.py:156-194`
- Test: `tests/test_app.py`

**Step 1: Write failing test for repo activity tracking**

Add to `tests/test_app.py`:

```python
def test_fetch_updates_repo_activity(mock_github_client, sample_config, tmp_path):
    """Test that fetching PRs updates repo_activity in cache."""
    cache_path = tmp_path / "cache.json"
    app = ReviewinatorApp(sample_config)
    app.cache = Cache(seen_prs=set(), pr_statuses={}, last_checked=None, repo_activity={})

    # Mock PRs from different repos
    pr1 = PullRequest(
        id=1, number=101, title="PR 1", author="user",
        repo="owner/repo1", url="http://example.com/1",
        created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        type="review_request", review_status=None
    )
    pr2 = PullRequest(
        id=2, number=102, title="PR 2", author="user",
        repo="owner/repo2", url="http://example.com/2",
        created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
        type="created", review_status="waiting"
    )

    mock_github_client.fetch_prs.return_value = [pr1, pr2]
    app.client = mock_github_client
    app._fetch_and_update()

    # Verify both repos are in repo_activity
    assert "owner/repo1" in app.cache.repo_activity
    assert "owner/repo2" in app.cache.repo_activity
    # Timestamps should be recent (within last minute)
    now = datetime.now(timezone.utc)
    for repo, timestamp in app.cache.repo_activity.items():
        assert (now - timestamp).total_seconds() < 60


def test_fetch_cleans_old_repo_activity(mock_github_client, tmp_path):
    """Test that old repo activity entries are cleaned up."""
    from datetime import timedelta

    config = Config(
        github_token="test",
        excluded_repos=[],
        created_pr_filter="either",
        activity_lookback_days=14,
        refresh_interval=300
    )

    app = ReviewinatorApp(config)
    now = datetime.now(timezone.utc)
    old_timestamp = now - timedelta(days=20)  # Older than lookback window

    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=None,
        repo_activity={
            "owner/old-repo": old_timestamp,
            "owner/recent-repo": now,
        }
    )

    # Fetch returns no PRs for old repo
    pr = PullRequest(
        id=1, number=101, title="PR", author="user",
        repo="owner/recent-repo", url="http://example.com/1",
        created_at=now, type="review_request", review_status=None
    )

    mock_github_client.fetch_prs.return_value = [pr]
    app.client = mock_github_client
    app._fetch_and_update()

    # Old repo should be cleaned up
    assert "owner/old-repo" not in app.cache.repo_activity
    assert "owner/recent-repo" in app.cache.repo_activity
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py::test_fetch_updates_repo_activity -v`
Run: `pytest tests/test_app.py::test_fetch_cleans_old_repo_activity -v`
Expected: Both FAIL - repo_activity not being updated

**Step 3: Update _fetch_and_update to track repo activity**

In `src/reviewinator/app.py`, update `_fetch_and_update()` method (around line 156):

```python
def _fetch_and_update(self) -> None:
    """Fetch PRs and update state (runs in background thread)."""
    try:
        self.prs = self.client.fetch_prs()

        # Update repo activity for all current PRs
        now = datetime.now(timezone.utc)
        for pr in self.prs:
            self.cache.repo_activity[pr.repo] = now

        # Clean up old repo activity entries
        cutoff = now - timedelta(days=self.config.activity_lookback_days)
        self.cache.repo_activity = {
            repo: timestamp
            for repo, timestamp in self.cache.repo_activity.items()
            if timestamp > cutoff
        }

        # Find new PRs and notify (skip on first run)
        if not self.is_first_run:
            new_prs = find_new_prs(self.prs, self.cache.seen_prs)
            for pr in new_prs:
                notify_new_pr(pr)

            # Find status changes and notify
            status_changes = find_status_changes(self.prs, self.cache.pr_statuses)
            for pr, old_status, new_status in status_changes:
                notify_status_change(pr, new_status)

        # Update cache
        self.cache.seen_prs = {pr.id for pr in self.prs}
        self.cache.pr_statuses = {
            pr.id: pr.review_status
            for pr in self.prs
            if pr.type == "created" and pr.review_status is not None
        }
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

    # Schedule UI update on main thread
    self._schedule_ui_update()
```

**Step 4: Add timedelta import at top of file**

In `src/reviewinator/app.py`, add to imports (line 6):

```python
from datetime import datetime, timezone, timedelta
```

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_app.py::test_fetch_updates_repo_activity -v`
Run: `pytest tests/test_app.py::test_fetch_cleans_old_repo_activity -v`
Expected: Both PASS

**Step 6: Commit repo activity tracking**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "feat: track repo activity during PR fetch

Update cache with repo timestamps as PRs are fetched.
Clean up entries older than activity_lookback_days window.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Display repos when no PRs

**Files:**
- Modify: `src/reviewinator/app.py:59-116`
- Test: `tests/test_app.py`

**Step 1: Write failing tests for repo display**

Add to `tests/test_app.py`:

```python
def test_menu_shows_repo_list_when_no_prs(sample_config, tmp_path):
    """Test menu shows repo list when no PRs but repo_activity exists."""
    from datetime import timedelta

    app = ReviewinatorApp(sample_config)
    app.prs = []  # No PRs

    now = datetime.now(timezone.utc)
    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=now,
        repo_activity={
            "owner/repo1": now - timedelta(days=1),
            "owner/repo2": now - timedelta(days=3),
            "owner/repo3": now - timedelta(days=7),
        }
    )

    app._do_update_menu()

    # Menu should contain repo items
    menu_items = [item.title for item in app.menu.values() if item.title]
    assert any("owner/repo1" in item for item in menu_items)
    assert any("owner/repo2" in item for item in menu_items)
    assert any("owner/repo3" in item for item in menu_items)
    assert "No pending items" not in menu_items


def test_menu_shows_up_to_20_repos(sample_config, tmp_path):
    """Test menu shows up to 20 repos with smart overflow."""
    from datetime import timedelta

    app = ReviewinatorApp(sample_config)
    app.prs = []

    now = datetime.now(timezone.utc)
    # Create 25 repos with activity
    repo_activity = {
        f"owner/repo{i}": now - timedelta(days=i)
        for i in range(25)
    }

    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=now,
        repo_activity=repo_activity
    )

    app._do_update_menu()

    menu_items = [item.title for item in app.menu.values() if item.title]

    # Should show first 20 repos
    repo_count = sum(1 for item in menu_items if "owner/repo" in item and "PRs," in item)
    assert repo_count == 20

    # Should show "and N more..."
    assert any("and 5 more" in item for item in menu_items)


def test_menu_repo_click_opens_pr_page(sample_config, tmp_path):
    """Test clicking repo item opens GitHub PR page."""
    import webbrowser
    from unittest.mock import patch

    app = ReviewinatorApp(sample_config)
    app.prs = []

    now = datetime.now(timezone.utc)
    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=now,
        repo_activity={"owner/repo1": now}
    )

    app._do_update_menu()

    # Find repo menu item
    repo_item = None
    for item in app.menu.values():
        if item.title and "owner/repo1" in item.title:
            repo_item = item
            break

    assert repo_item is not None
    assert repo_item.callback is not None

    # Test callback opens correct URL
    with patch.object(webbrowser, 'open') as mock_open:
        repo_item.callback(None)
        mock_open.assert_called_once_with("https://github.com/owner/repo1/pulls")


def test_menu_filters_old_repos_from_display(sample_config, tmp_path):
    """Test menu only shows repos within activity window."""
    from datetime import timedelta

    config = Config(
        github_token="test",
        excluded_repos=[],
        created_pr_filter="either",
        activity_lookback_days=14,
        refresh_interval=300
    )

    app = ReviewinatorApp(config)
    app.prs = []

    now = datetime.now(timezone.utc)
    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=now,
        repo_activity={
            "owner/recent": now - timedelta(days=5),
            "owner/old": now - timedelta(days=20),  # Beyond 14 day window
        }
    )

    app._do_update_menu()

    menu_items = [item.title for item in app.menu.values() if item.title]
    assert any("owner/recent" in item for item in menu_items)
    assert not any("owner/old" in item for item in menu_items)


def test_menu_shows_no_pending_when_cache_empty(sample_config, tmp_path):
    """Test menu shows 'No pending items' when cache is empty."""
    app = ReviewinatorApp(sample_config)
    app.prs = []
    app.cache = Cache(
        seen_prs=set(),
        pr_statuses={},
        last_checked=None,
        repo_activity={}
    )

    app._do_update_menu()

    menu_items = [item.title for item in app.menu.values() if item.title]
    assert "No pending items" in menu_items
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_app.py::test_menu_shows_repo_list_when_no_prs -v`
Expected: FAIL - menu still shows "No pending items"

**Step 3: Update _do_update_menu to display repos**

In `src/reviewinator/app.py`, update `_do_update_menu()` method (around line 106):

```python
        # Show "No pending items" or recent repos if both lists empty
        if not review_requests and not created_prs:
            # Calculate repos with recent activity
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.config.activity_lookback_days
            )
            active_repos = {
                repo: timestamp
                for repo, timestamp in self.cache.repo_activity.items()
                if timestamp > cutoff_date
            }

            if active_repos:
                # Show recent activity header
                header = rumps.MenuItem("Recent Activity:", callback=None)
                self.menu.add(header)

                # Sort by most recent first
                sorted_repos = sorted(
                    active_repos.items(),
                    key=lambda x: x[1],
                    reverse=True
                )

                # Show up to 20 repos
                display_limit = 20
                for repo, timestamp in sorted_repos[:display_limit]:
                    # Count PRs for this repo from cache
                    pr_count = sum(
                        1 for pr in self.prs
                        if pr.repo == repo
                    )
                    if pr_count == 0:
                        # Estimate from cache if no current PRs
                        pr_count = "recent"

                    # Calculate age
                    now = datetime.now(timezone.utc)
                    age_delta = now - timestamp
                    if age_delta.days == 0:
                        age_str = "today"
                    elif age_delta.days == 1:
                        age_str = "1d ago"
                    else:
                        age_str = f"{age_delta.days}d ago"

                    # Format: "owner/repo (N PRs, Xd ago)"
                    if isinstance(pr_count, int):
                        title = f"  {repo} ({pr_count} PRs, {age_str})"
                    else:
                        title = f"  {repo} (recent activity)"

                    item = rumps.MenuItem(
                        title,
                        callback=self._make_pr_callback(f"https://github.com/{repo}/pulls")
                    )
                    self.menu.add(item)

                # Show overflow if needed
                if len(active_repos) > display_limit:
                    overflow_count = len(active_repos) - display_limit
                    self.menu.add(rumps.MenuItem(
                        f"  and {overflow_count} more...",
                        callback=None
                    ))
            else:
                # No activity - show default message
                self.menu.add(rumps.MenuItem("No pending items", callback=None))
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_app.py::test_menu_shows_repo_list_when_no_prs -v`
Run: `pytest tests/test_app.py::test_menu_shows_up_to_20_repos -v`
Run: `pytest tests/test_app.py::test_menu_repo_click_opens_pr_page -v`
Run: `pytest tests/test_app.py::test_menu_filters_old_repos_from_display -v`
Run: `pytest tests/test_app.py::test_menu_shows_no_pending_when_cache_empty -v`
Expected: All PASS

**Step 5: Run all tests**

Run: `make test`
Expected: All tests pass

**Step 6: Commit menu display changes**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "feat: display repos with recent activity when no PRs

Show up to 20 repos sorted by recent activity when menu is empty.
Each item shows repo name, PR count estimate, and time since last activity.
Clicking opens the repo's PR page on GitHub.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update configuration section**

In `CLAUDE.md`, update the configuration section (around line 38):

```markdown
## Configuration

Create `~/.config/reviewinator/config.yaml`:
```yaml
github_token: ghp_your_token_here
excluded_repos:
  - owner/archived-repo
  - org/old-project
created_pr_filter: either  # Options: all, waiting, needs_attention, either
activity_lookback_days: 14  # Days to show repos with recent activity (default: 14)
refresh_interval: 300  # optional, defaults to 300 seconds
```

The `excluded_repos` field is optional and lists repos to exclude from tracking.

The `created_pr_filter` field controls which of your created PRs to show:
- `either` (default): Show PRs waiting for review OR needing changes
- `waiting`: Show only PRs waiting for initial review
- `needs_attention`: Show only PRs with changes requested
- `all`: Show all your open PRs

The `activity_lookback_days` field controls how far back to look for repo activity
when showing repos in the empty state (default: 14 days).
```

**Step 2: Commit documentation update**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for repo activity feature

Add documentation for activity_lookback_days config field.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Run full test suite and verify

**Files:**
- None (verification only)

**Step 1: Run all tests**

Run: `make test`
Expected: All tests pass

**Step 2: Run linting**

Run: `make lint`
Expected: No linting errors

**Step 3: If linting fails, fix with format**

Run: `make format`
Run: `make lint`
Expected: All checks pass

**Step 4: Commit any formatting changes (if needed)**

```bash
git add -A
git commit -m "style: apply linting fixes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update user config file

**Files:**
- Modify: `~/.config/reviewinator/config.yaml`

**Step 1: Add activity_lookback_days to config**

Edit `~/.config/reviewinator/config.yaml` and add the new field:

```yaml
github_token: <your token>
excluded_repos: []
created_pr_filter: either
activity_lookback_days: 14
refresh_interval: 300
```

**Step 2: Test the app**

Run: `make run`
Expected: App starts successfully

**Step 3: Test empty state**

- Wait for PR fetch to complete
- If you have no PRs, verify repos with recent activity appear
- Click a repo and verify it opens the PR page in browser

**Step 4: No commit needed (user config not in repo)**

---

## Task 8: Final verification

**Files:**
- None (verification only)

**Step 1: Verify all tests pass with coverage**

Run: `make test-cov`
Expected: All tests pass with good coverage

**Step 2: Check git status**

Run: `git status`
Expected: Working tree clean (except IDEAS.md if modified)

**Step 3: Review commit history**

Run: `git log --oneline -8`
Expected: See all commits from this implementation

**Step 4: Done!**

The implementation is complete. The app now shows repos with recent activity when there are no pending PRs.
