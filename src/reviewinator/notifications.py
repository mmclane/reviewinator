"""macOS notifications for new PR review requests."""

import pync

from reviewinator.github_client import PullRequest


def find_new_prs(current_prs: list[PullRequest], seen_ids: set[int]) -> list[PullRequest]:
    """Find PRs that haven't been seen before.

    Args:
        current_prs: List of current PRs from GitHub.
        seen_ids: Set of PR IDs we've already notified about.

    Returns:
        List of PRs not in seen_ids.
    """
    return [pr for pr in current_prs if pr.id not in seen_ids]


def notify_new_pr(pr: PullRequest) -> None:
    """Send macOS notification for a new PR.

    Args:
        pr: The pull request to notify about.
    """
    try:
        pync.notify(
            message=f"#{pr.number} {pr.title}\nFrom: {pr.author}",
            title=f"New Review Request: {pr.repo}",
            open=pr.url,
        )
    except Exception:
        # Don't crash if notifications fail
        pass
