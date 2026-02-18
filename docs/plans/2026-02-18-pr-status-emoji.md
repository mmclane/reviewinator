# PR Status Emoji Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Prepend a status emoji to each PR menu item so users can see review status at a glance.

**Architecture:** Single change to `PullRequest.format_menu_item()` in `github_client.py` — add a module-level `STATUS_EMOJI` dict and prepend the appropriate emoji based on `type` and `review_status`. No config, no new data, no other files.

**Tech Stack:** Python, pytest (run tests with `make test` from `/Users/mmclane/repos/personal/reviewinator`)

---

### Task 1: Add status emoji to PR menu items

**Files:**
- Modify: `src/reviewinator/github_client.py:1-44`
- Test: `tests/test_github_client.py` (class `TestPullRequestFormatting`)

**Current behavior** (for reference):
- Review request: `#142 Fix login bug (alice, 2h ago)`
- Created PR:     `#123 Test (waiting, 2h ago)`

**Target behavior:**
- Review request: `👀 #142 Fix login bug (alice, 2h ago)`
- Created waiting: `🕐 #123 Test (waiting, 2h ago)`
- Created approved: `✅ #91 Update deps (approved, 1h ago)`
- Created changes requested: `🔴 #79 Refactor auth (changes_requested, 5d ago)`
- Created commented: `💬 #88 Add docs (commented, 3d ago)`

---

**Step 1: Update the two existing format tests to assert the emoji prefix**

In `tests/test_github_client.py`, update `TestPullRequestFormatting`:

```python
class TestPullRequestFormatting:
    """Tests for PR display formatting."""

    def test_format_menu_item(self) -> None:
        """Should format review request PR with eyes emoji."""
        now = datetime(2026, 2, 13, 12, 0, 0, tzinfo=timezone.utc)
        pr = PullRequest(
            id=12345,
            number=142,
            title="Fix login bug",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/142",
            created_at=datetime(2026, 2, 13, 10, 0, 0, tzinfo=timezone.utc),
            type="review_request",
            review_status=None,
        )

        formatted = pr.format_menu_item(now)

        assert formatted == "👀 #142 Fix login bug (alice, 2h ago)"

    def test_format_menu_item_for_created_pr(self) -> None:
        """Test formatting created PR shows clock emoji for waiting status."""
        pr = PullRequest(
            id=1,
            number=123,
            title="Test",
            author="me",
            repo="owner/repo",
            url="https://url",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            type="created",
            review_status="waiting",
        )
        now = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
        result = pr.format_menu_item(now)
        assert result == "🕐 #123 Test (waiting, 2h ago)"

    def test_format_menu_item_approved(self) -> None:
        """Test formatting created PR shows checkmark for approved status."""
        pr = PullRequest(
            id=2,
            number=91,
            title="Update deps",
            author="me",
            repo="owner/repo",
            url="https://url",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            type="created",
            review_status="approved",
        )
        now = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        result = pr.format_menu_item(now)
        assert result == "✅ #91 Update deps (approved, 1h ago)"

    def test_format_menu_item_changes_requested(self) -> None:
        """Test formatting created PR shows red circle for changes_requested."""
        pr = PullRequest(
            id=3,
            number=79,
            title="Refactor auth",
            author="me",
            repo="owner/repo",
            url="https://url",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            type="created",
            review_status="changes_requested",
        )
        now = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        result = pr.format_menu_item(now)
        assert result == "🔴 #79 Refactor auth (changes_requested, 1h ago)"

    def test_format_menu_item_commented(self) -> None:
        """Test formatting created PR shows speech bubble for commented."""
        pr = PullRequest(
            id=4,
            number=88,
            title="Add docs",
            author="me",
            repo="owner/repo",
            url="https://url",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            type="created",
            review_status="commented",
        )
        now = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        result = pr.format_menu_item(now)
        assert result == "💬 #88 Add docs (commented, 1h ago)"

    def test_format_menu_item_unknown_status_falls_back_to_clock(self) -> None:
        """Test formatting created PR with unknown status uses clock fallback."""
        pr = PullRequest(
            id=5,
            number=99,
            title="Mystery PR",
            author="me",
            repo="owner/repo",
            url="https://url",
            created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
            type="created",
            review_status=None,
        )
        now = datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)
        result = pr.format_menu_item(now)
        assert result == "🕐 #99 Mystery PR (unknown, 1h ago)"
```

**Step 2: Run tests to confirm they fail**

```
make test
```

Expected: 6 failures in `TestPullRequestFormatting` — missing emoji prefix in output.

**Step 3: Update `github_client.py`**

Add `STATUS_EMOJI` dict after the imports (before the `@dataclass` line), and update `format_menu_item`:

```python
STATUS_EMOJI = {
    "review_request": "👀",
    "waiting": "🕐",
    "approved": "✅",
    "changes_requested": "🔴",
    "commented": "💬",
}
```

Replace the `format_menu_item` method body:

```python
def format_menu_item(self, now: datetime | None = None) -> str:
    """Format PR for menu display.

    Args:
        now: Current time for age calculation. Defaults to UTC now.

    Returns:
        Formatted string like "👀 #142 Fix login bug (alice, 2h ago)" for review requests
        or "✅ #142 Fix login bug (approved, 2h ago)" for created PRs.
    """
    if now is None:
        now = datetime.now(timezone.utc)
    age = format_age(self.created_at, now)

    if self.type == "created":
        status = self.review_status or "unknown"
        emoji = STATUS_EMOJI.get(status, "🕐")
        return f"{emoji} #{self.number} {self.title} ({status}, {age})"
    else:
        emoji = STATUS_EMOJI["review_request"]
        return f"{emoji} #{self.number} {self.title} ({self.author}, {age})"
```

**Step 4: Run tests to confirm all pass**

```
make test
```

Expected: all 84 tests pass (79 existing + 4 new + 2 updated).

**Step 5: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add status emoji prefix to PR menu items"
```
