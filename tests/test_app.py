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
            excluded_review_teams=[],
            created_pr_filter="any",
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


def test_menu_shows_repo_list_when_no_prs(sample_config, tmp_path):
    """Test menu shows repo list when no PRs but repo_activity exists."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from reviewinator.app import ReviewinatorApp
    from reviewinator.cache import Cache

    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
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
            },
        )

        app._do_update_menu()

        # Menu should contain repo items
        menu_items = [
            item.title for item in app.menu.values() if hasattr(item, "title") and item.title
        ]
        assert any("owner/repo1" in item for item in menu_items)
        assert any("owner/repo2" in item for item in menu_items)
        assert any("owner/repo3" in item for item in menu_items)
        assert "No pending items" not in menu_items


def test_menu_shows_up_to_20_repos(sample_config, tmp_path):
    """Test menu shows up to 20 repos with smart overflow."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from reviewinator.app import ReviewinatorApp
    from reviewinator.cache import Cache

    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)
        app.prs = []

        now = datetime.now(timezone.utc)
        # Create 25 repos with activity (all within lookback window)
        # Use hours instead of days to keep all within the 14-day window
        repo_activity = {f"owner/repo{i}": now - timedelta(hours=i) for i in range(25)}

        app.cache = Cache(
            seen_prs=set(), pr_statuses={}, last_checked=now, repo_activity=repo_activity
        )

        app._do_update_menu()

        menu_items = [
            item.title for item in app.menu.values() if hasattr(item, "title") and item.title
        ]

        # Should show first 20 repos
        repo_count = sum(
            1 for item in menu_items if "owner/repo" in item and "recent activity" in item
        )
        assert repo_count == 20

        # Should show "and N more..."
        assert any("and 5 more" in item for item in menu_items)


def test_menu_repo_click_opens_pr_page(sample_config, tmp_path):
    """Test clicking repo item opens GitHub PR page."""
    import webbrowser
    from datetime import datetime, timezone
    from unittest.mock import patch

    from reviewinator.app import ReviewinatorApp
    from reviewinator.cache import Cache

    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)
        app.prs = []

        now = datetime.now(timezone.utc)
        app.cache = Cache(
            seen_prs=set(), pr_statuses={}, last_checked=now, repo_activity={"owner/repo1": now}
        )

        app._do_update_menu()

        # Find repo menu item
        repo_item = None
        for item in app.menu.values():
            has_title = hasattr(item, "title") and item.title
            if has_title and "owner/repo1" in item.title:
                repo_item = item
                break

        assert repo_item is not None
        assert repo_item.callback is not None

        # Test callback opens correct URL
        with patch.object(webbrowser, "open") as mock_open:
            repo_item.callback(None)
            url = "https://github.com/owner/repo1/pulls"
            mock_open.assert_called_once_with(url)


def test_menu_filters_old_repos_from_display(sample_config, tmp_path):
    """Test menu only shows repos within activity window."""
    from datetime import datetime, timedelta, timezone
    from unittest.mock import patch

    from reviewinator.app import ReviewinatorApp
    from reviewinator.cache import Cache
    from reviewinator.config import Config

    config = Config(
        github_token="test",
        excluded_repos=[],
        excluded_review_teams=[],
        created_pr_filter="any",
        activity_lookback_days=14,
        refresh_interval=300,
    )

    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
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
            },
        )

        app._do_update_menu()

        menu_items = [
            item.title for item in app.menu.values() if hasattr(item, "title") and item.title
        ]
        assert any("owner/recent" in item for item in menu_items)
        assert not any("owner/old" in item for item in menu_items)


def test_menu_shows_no_pending_when_cache_empty(sample_config, tmp_path):
    """Test menu shows 'No pending items' when cache is empty."""
    from unittest.mock import patch

    from reviewinator.app import ReviewinatorApp
    from reviewinator.cache import Cache

    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)
        app.prs = []
        app.cache = Cache(seen_prs=set(), pr_statuses={}, last_checked=None, repo_activity={})

        app._do_update_menu()

        menu_items = [
            item.title for item in app.menu.values() if hasattr(item, "title") and item.title
        ]
        assert "No pending items" in menu_items
