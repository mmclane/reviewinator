"""Tests for notifications module."""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

from reviewinator.github_client import PullRequest
from reviewinator.notifications import find_new_prs, notify_new_pr


class TestFindNewPrs:
    """Tests for find_new_prs function."""

    def test_find_new_prs_identifies_unseen(self) -> None:
        """Should return PRs not in seen set."""
        pr1 = PullRequest(
            id=1,
            number=10,
            title="PR 1",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/10",
            created_at=datetime.now(timezone.utc),
        )
        pr2 = PullRequest(
            id=2,
            number=20,
            title="PR 2",
            author="bob",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/20",
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
            id=1,
            number=10,
            title="PR 1",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/10",
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
            id=1,
            number=142,
            title="Fix login bug",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/142",
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
            id=1,
            number=142,
            title="Fix login bug",
            author="alice",
            repo="org/repo1",
            url="https://github.com/org/repo1/pull/142",
            created_at=datetime.now(timezone.utc),
        )

        # Should not raise
        notify_new_pr(pr)
