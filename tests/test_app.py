"""Tests for the main app module."""

from unittest.mock import MagicMock, patch

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
        app.client.fetch_prs = MagicMock(return_value=[sample_pr])

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
        app.client.fetch_prs = MagicMock(return_value=[])

        # First run - no notifications
        app._poll()
        mock_notify.assert_not_called()

        # Second run with new PR - should notify
        app.client.fetch_prs = MagicMock(return_value=[sample_pr])
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
        app.client.fetch_prs = MagicMock(return_value=[sample_pr])

        app._poll()

        mock_notify.assert_not_called()

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    def test_menu_shows_green_check_when_no_prs(
        self, mock_load_cache: MagicMock, mock_github: MagicMock, sample_config: Config
    ) -> None:
        """Test that menu bar shows green check mark when no PRs."""
        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache()

        app = ReviewinatorApp(sample_config)
        app.prs = []
        app._do_update_menu()
        assert app.title == "✅"

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    @patch("reviewinator.app.save_cache")
    def test_fetch_updates_repo_activity(
        self,
        mock_save_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_github: MagicMock,
        mock_github_client: MagicMock,
        sample_config: Config,
    ) -> None:
        """Test that fetching PRs updates repo_activity in cache."""
        from datetime import datetime, timezone

        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache

        mock_load_cache.return_value = Cache(
            seen_prs=set(), pr_statuses={}, last_checked=None, repo_activity={}
        )

        app = ReviewinatorApp(sample_config)

        # Mock PRs from different repos
        pr1 = PullRequest(
            id=1,
            number=101,
            title="PR 1",
            author="user",
            repo="owner/repo1",
            url="http://example.com/1",
            created_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            type="review_request",
            review_status=None,
        )
        pr2 = PullRequest(
            id=2,
            number=102,
            title="PR 2",
            author="user",
            repo="owner/repo2",
            url="http://example.com/2",
            created_at=datetime(2024, 1, 2, tzinfo=timezone.utc),
            type="created",
            review_status="waiting",
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

    @patch("reviewinator.app.Github")
    @patch("reviewinator.app.load_cache")
    @patch("reviewinator.app.save_cache")
    def test_fetch_cleans_old_repo_activity(
        self,
        mock_save_cache: MagicMock,
        mock_load_cache: MagicMock,
        mock_github: MagicMock,
        mock_github_client: MagicMock,
    ) -> None:
        """Test that old repo activity entries are cleaned up."""
        from datetime import datetime, timedelta, timezone

        from reviewinator.app import ReviewinatorApp
        from reviewinator.cache import Cache
        from reviewinator.config import Config

        config = Config(
            github_token="test",
            excluded_repos=[],
            created_pr_filter="either",
            activity_lookback_days=14,
            refresh_interval=300,
        )

        now = datetime.now(timezone.utc)
        old_timestamp = now - timedelta(days=20)  # Older than lookback window

        mock_load_cache.return_value = Cache(
            seen_prs=set(),
            pr_statuses={},
            last_checked=None,
            repo_activity={
                "owner/old-repo": old_timestamp,
                "owner/recent-repo": now,
            },
        )

        app = ReviewinatorApp(config)

        # Fetch returns no PRs for old repo
        pr = PullRequest(
            id=1,
            number=101,
            title="PR",
            author="user",
            repo="owner/recent-repo",
            url="http://example.com/1",
            created_at=now,
            type="review_request",
            review_status=None,
        )

        mock_github_client.fetch_prs.return_value = [pr]
        app.client = mock_github_client
        app._fetch_and_update()

        # Old repo should be cleaned up
        assert "owner/old-repo" not in app.cache.repo_activity
        assert "owner/recent-repo" in app.cache.repo_activity
