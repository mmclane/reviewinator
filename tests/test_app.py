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
