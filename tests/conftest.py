"""Shared test fixtures."""

from datetime import datetime, timezone

import pytest

from reviewinator.cache import Cache
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
        type="review_request",
        review_status=None,
    )


@pytest.fixture
def sample_cache():
    """Sample cache for testing."""
    return Cache(
        seen_prs={1, 2, 3},
        pr_statuses={1: "waiting", 2: "approved"},
        last_checked=datetime(2024, 1, 1, tzinfo=timezone.utc),
        repo_activity={},
    )


@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    from reviewinator.config import Config

    return Config(
        github_token="ghp_test123",
        excluded_repos=[],
        excluded_review_teams=[],
        created_pr_filter="either",
        activity_lookback_days=14,
        refresh_interval=300,
    )


@pytest.fixture
def mock_github_client():
    """Create a mock GitHubClient for testing."""
    from unittest.mock import MagicMock

    mock = MagicMock()
    mock.fetch_prs = MagicMock(return_value=[])
    return mock
