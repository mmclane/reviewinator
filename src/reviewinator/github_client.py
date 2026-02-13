"""GitHub API client for fetching PR review requests."""

from dataclasses import dataclass
from datetime import datetime, timezone

from github import Github


@dataclass
class PullRequest:
    """Represents a pull request awaiting review."""

    id: int
    number: int
    title: str
    author: str
    repo: str
    url: str
    created_at: datetime

    def format_menu_item(self, now: datetime | None = None) -> str:
        """Format PR for menu display.

        Args:
            now: Current time for age calculation. Defaults to UTC now.

        Returns:
            Formatted string like "#142 Fix login bug (alice, 2h ago)"
        """
        if now is None:
            now = datetime.now(timezone.utc)
        age = format_age(self.created_at, now)
        return f"#{self.number} {self.title} ({self.author}, {age})"


def format_age(created_at: datetime, now: datetime) -> str:
    """Format time difference as human-readable age.

    Args:
        created_at: When the PR was created.
        now: Current time.

    Returns:
        Formatted age string like "2h ago", "3d ago", etc.
    """
    delta = now - created_at
    total_minutes = int(delta.total_seconds() / 60)

    if total_minutes < 60:
        return f"{total_minutes}m ago"

    total_hours = total_minutes // 60
    if total_hours < 24:
        return f"{total_hours}h ago"

    total_days = total_hours // 24
    if total_days < 7:
        return f"{total_days}d ago"

    total_weeks = total_days // 7
    return f"{total_weeks}w ago"


class GitHubClient:
    """Client for fetching PR review requests from GitHub."""

    def __init__(self, github: Github, repos: list[str]) -> None:
        """Initialize the client.

        Args:
            github: Authenticated PyGithub instance.
            repos: List of repos to filter to (e.g., ["org/repo1", "owner/repo2"]).
        """
        self._github = github
        self._repos = set(repos)
        self._username: str | None = None

    @property
    def username(self) -> str:
        """Get the authenticated user's username (cached)."""
        if self._username is None:
            self._username = self._github.get_user().login
        return self._username

    def fetch_review_requests(self) -> list[PullRequest]:
        """Fetch PRs where the current user is requested as reviewer.

        Returns:
            List of PullRequest objects, filtered to configured repos.
        """
        query = f"is:pr is:open review-requested:{self.username}"
        issues = self._github.search_issues(query)

        prs = []
        for issue in issues:
            repo_name = issue.repository.full_name
            if repo_name not in self._repos:
                continue

            pr = PullRequest(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                author=issue.user.login,
                repo=repo_name,
                url=issue.html_url,
                created_at=issue.created_at.replace(tzinfo=timezone.utc),
            )
            prs.append(pr)

        return prs
