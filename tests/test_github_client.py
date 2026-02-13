"""Tests for GitHub client module."""

from datetime import datetime, timezone

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
