"""Tests for GitHub client module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from reviewinator.github_client import GitHubClient, PullRequest, format_age


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
            type="review_request",
            review_status=None,
        )

        assert pr.id == 12345
        assert pr.number == 142
        assert pr.title == "Fix login bug"
        assert pr.author == "alice"
        assert pr.repo == "org/repo1"
        assert pr.url == "https://github.com/org/repo1/pull/142"

    def test_pull_request_with_review_request_type(self) -> None:
        """Test PR with type='review_request'."""
        pr = PullRequest(
            id=1,
            number=123,
            title="Test PR",
            author="alice",
            repo="owner/repo",
            url="https://github.com/owner/repo/pull/123",
            created_at=datetime.now(timezone.utc),
            type="review_request",
            review_status=None,
        )
        assert pr.type == "review_request"
        assert pr.review_status is None

    def test_pull_request_with_created_type(self) -> None:
        """Test PR with type='created' and review status."""
        pr = PullRequest(
            id=2,
            number=456,
            title="My PR",
            author="me",
            repo="owner/repo",
            url="https://github.com/owner/repo/pull/456",
            created_at=datetime.now(timezone.utc),
            type="created",
            review_status="waiting",
        )
        assert pr.type == "created"
        assert pr.review_status == "waiting"


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
            type="review_request",
            review_status=None,
        )

        formatted = pr.format_menu_item(now)

        assert formatted == "#142 Fix login bug (alice, 2h ago)"

    def test_format_menu_item_for_created_pr(self) -> None:
        """Test formatting created PR shows status instead of author."""
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
        assert result == "#123 Test (waiting, 2h ago)"


class TestGitHubClient:
    """Tests for GitHubClient class."""

    def test_fetch_review_requests_filters_to_configured_repos(self) -> None:
        """Should only return PRs from configured repos."""
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

        from reviewinator.config import Config

        config = Config(
            github_token="test",
            review_request_repos=["org/repo1", "org/repo2"],
            created_pr_repos=[],
            created_pr_filter="waiting",
        )
        client = GitHubClient(mock_github, config)
        prs = client._fetch_review_requests()

        assert len(prs) == 1
        assert prs[0].repo == "org/repo1"
        assert prs[0].number == 10

    def test_fetch_review_requests_searches_for_user(self) -> None:
        """Should search for PRs requesting review from current user."""
        mock_github = MagicMock()
        mock_user = MagicMock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user
        mock_github.search_issues.return_value = []

        from reviewinator.config import Config

        config = Config(
            github_token="test",
            review_request_repos=["org/repo1"],
            created_pr_repos=[],
            created_pr_filter="waiting",
        )
        client = GitHubClient(mock_github, config)
        client._fetch_review_requests()

        mock_github.search_issues.assert_called_once()
        call_args = mock_github.search_issues.call_args[0][0]
        assert "review-requested:testuser" in call_args
        assert "is:pr" in call_args
        assert "is:open" in call_args
