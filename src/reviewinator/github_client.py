"""GitHub API client for fetching PR review requests."""

from dataclasses import dataclass
from datetime import datetime, timezone


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
