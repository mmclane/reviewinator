"""Shared test fixtures."""

from datetime import datetime, timezone

import pytest

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
    )


@pytest.fixture
def sample_config():
    """Create a sample config for testing."""
    from reviewinator.config import Config

    return Config(
        github_token="ghp_test123",
        repos=["org/repo1", "org/repo2"],
        refresh_interval=300,
    )
