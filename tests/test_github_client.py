"""Tests for GitHub client module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from reviewinator.config import Config
from reviewinator.github_client import GitHubClient, PullRequest, format_age


@pytest.fixture
def mock_github():
    """Create mock GitHub instance."""
    return MagicMock()


@pytest.fixture
def client_with_excluded_teams(mock_github):
    """Create GitHubClient with excluded_review_teams configured."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    return GitHubClient(mock_github, config)


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
            excluded_repos=["other/repo"],
            excluded_review_teams=[],
            created_pr_filter="any",
            activity_lookback_days=14,
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
            excluded_repos=[],
            excluded_review_teams=[],
            created_pr_filter="any",
            activity_lookback_days=14,
        )
        client = GitHubClient(mock_github, config)
        client._fetch_review_requests()

        mock_github.search_issues.assert_called_once()
        call_args = mock_github.search_issues.call_args[0][0]
        assert "review-requested:testuser" in call_args
        assert "is:pr" in call_args
        assert "is:open" in call_args

    def test_should_show_review_request_individual_reviewer(
        self, client_with_excluded_teams
    ) -> None:
        """Should show PR when user is individually requested."""
        from unittest.mock import Mock

        # Mock PR with individual reviewer
        mock_pr = Mock()
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_pr.requested_reviewers = [mock_user]
        mock_pr.requested_teams = []

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_should_show_review_request_only_excluded_team(
        self, client_with_excluded_teams
    ) -> None:
        """Should hide PR when only requested via excluded team."""
        from unittest.mock import Mock

        # Mock PR with only excluded team
        mock_pr = Mock()
        mock_pr.requested_reviewers = []
        mock_team = Mock()
        mock_org = Mock()
        mock_org.login = "testorg"
        mock_team.organization = mock_org
        mock_team.slug = "all-engineers"
        mock_pr.requested_teams = [mock_team]

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is False

    def test_should_show_review_request_non_excluded_team(self, client_with_excluded_teams) -> None:
        """Should show PR when requested via non-excluded team."""
        from unittest.mock import Mock

        # Mock PR with non-excluded team
        mock_pr = Mock()
        mock_pr.requested_reviewers = []
        mock_team = Mock()
        mock_org = Mock()
        mock_org.login = "testorg"
        mock_team.organization = mock_org
        mock_team.slug = "team-b"
        mock_pr.requested_teams = [mock_team]

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_should_show_review_request_mixed_teams(self, client_with_excluded_teams) -> None:
        """Should show PR when mix of excluded and non-excluded teams."""
        from unittest.mock import Mock

        # Mock PR with both excluded and non-excluded teams
        mock_pr = Mock()
        mock_pr.requested_reviewers = []

        # Excluded team
        mock_team_a = Mock()
        mock_org = Mock()
        mock_org.login = "testorg"
        mock_team_a.organization = mock_org
        mock_team_a.slug = "all-engineers"

        # Non-excluded team
        mock_team_b = Mock()
        mock_team_b.organization = mock_org
        mock_team_b.slug = "team-b"

        mock_pr.requested_teams = [mock_team_a, mock_team_b]

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_should_show_review_request_no_reviewers_fail_open(
        self, client_with_excluded_teams
    ) -> None:
        """Should show PR when no reviewers (fail open)."""
        from unittest.mock import Mock

        # Mock PR with empty reviewers
        mock_pr = Mock()
        mock_pr.requested_reviewers = []
        mock_pr.requested_teams = []

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_should_show_review_request_none_reviewers_fail_open(
        self, client_with_excluded_teams
    ) -> None:
        """Should show PR when reviewers are None (fail open)."""
        from unittest.mock import Mock

        # Mock PR with None reviewers
        mock_pr = Mock()
        mock_pr.requested_reviewers = None
        mock_pr.requested_teams = None

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_should_show_review_request_team_missing_org(self, client_with_excluded_teams) -> None:
        """Should show PR when team missing org (fail open)."""
        from unittest.mock import Mock

        # Mock PR with team missing org
        mock_pr = Mock()
        mock_pr.requested_reviewers = []
        mock_team = Mock()
        mock_team.organization = None  # Missing org
        mock_team.slug = "all-engineers"
        mock_pr.requested_teams = [mock_team]

        result = client_with_excluded_teams._should_show_review_request(mock_pr, "testuser")
        assert result is True

    def test_fetch_review_requests_filters_excluded_teams(self) -> None:
        """Test that fetch_review_requests filters PRs based on excluded teams."""
        from unittest.mock import Mock

        mock_github = MagicMock()
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_github.get_user.return_value = mock_user

        config = Config(
            github_token="test_token",
            excluded_repos=[],
            excluded_review_teams=["testorg/all-engineers"],
            created_pr_filter="all",
            activity_lookback_days=14,
        )

        # Mock search results
        mock_issue1 = Mock()
        mock_issue1.id = 1
        mock_issue1.number = 101
        mock_issue1.title = "PR 1 - individual request"
        mock_issue1.user.login = "author1"
        mock_issue1.repository.full_name = "testorg/repo1"
        mock_issue1.html_url = "https://github.com/testorg/repo1/pull/101"
        mock_issue1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_issue2 = Mock()
        mock_issue2.id = 2
        mock_issue2.number = 102
        mock_issue2.title = "PR 2 - only excluded team"
        mock_issue2.user.login = "author2"
        mock_issue2.repository.full_name = "testorg/repo1"
        mock_issue2.html_url = "https://github.com/testorg/repo1/pull/102"
        mock_issue2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_github.search_issues.return_value = [mock_issue1, mock_issue2]

        # Mock repo.get_pull() for PR objects
        mock_repo = Mock()

        # PR 1: individually requested
        mock_pr1 = Mock()
        mock_user = Mock()
        mock_user.login = "testuser"
        mock_pr1.requested_reviewers = [mock_user]
        mock_pr1.requested_teams = []

        # PR 2: only excluded team
        mock_pr2 = Mock()
        mock_pr2.requested_reviewers = []
        mock_team = Mock()
        mock_org = Mock()
        mock_org.login = "testorg"
        mock_team.organization = mock_org
        mock_team.slug = "all-engineers"
        mock_pr2.requested_teams = [mock_team]

        mock_repo.get_pull = Mock(side_effect=lambda num: mock_pr1 if num == 101 else mock_pr2)
        mock_github.get_repo.return_value = mock_repo

        client = GitHubClient(mock_github, config)
        prs = client._fetch_review_requests()

        # Should only return PR 1 (individually requested)
        assert len(prs) == 1
        assert prs[0].number == 101


class TestFetchCreatedPRsFilter:
    """Tests for _fetch_created_prs filter behavior."""

    def _make_client(self, mock_github, filter_type):
        config = Config(
            github_token="test",
            excluded_repos=[],
            excluded_review_teams=[],
            created_pr_filter=filter_type,
            activity_lookback_days=14,
        )
        return GitHubClient(mock_github, config)

    def _make_issue(self, status_state):
        """Make a mock issue and a PR object with the given review state."""
        mock_issue = MagicMock()
        mock_issue.id = 1
        mock_issue.number = 42
        mock_issue.title = "Test PR"
        mock_issue.user.login = "me"
        mock_issue.repository.full_name = "org/repo"
        mock_issue.html_url = "https://github.com/org/repo/pull/42"
        mock_issue.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_review = MagicMock()
        mock_review.state = status_state

        mock_pr_obj = MagicMock()
        mock_pr_obj.get_reviews.return_value = [mock_review]

        return mock_issue, mock_pr_obj

    def test_any_filter_includes_approved(self) -> None:
        """'any' filter should include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "approved"

    def test_any_filter_includes_waiting(self) -> None:
        """'any' filter should include waiting PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("DUMMY")
        mock_pr_obj.get_reviews.return_value = []  # no reviews = waiting
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "waiting"

    def test_any_filter_includes_changes_requested(self) -> None:
        """'any' filter should include changes_requested PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("CHANGES_REQUESTED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "changes_requested"

    def test_waiting_filter_excludes_approved(self) -> None:
        """'waiting' filter should not include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "waiting")
        prs = client._fetch_created_prs("waiting")

        assert len(prs) == 0

    def test_needs_attention_filter_excludes_approved(self) -> None:
        """'needs_attention' filter should not include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "needs_attention")
        prs = client._fetch_created_prs("needs_attention")

        assert len(prs) == 0
