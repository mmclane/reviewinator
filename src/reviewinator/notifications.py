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


def find_status_changes(
    prs: list[PullRequest], old_statuses: dict[int, str]
) -> list[tuple[PullRequest, str, str]]:
    """Find PRs whose review status changed.

    Args:
        prs: Current list of PRs.
        old_statuses: Previous status map (pr_id -> status).

    Returns:
        List of (pr, old_status, new_status) tuples for PRs with notable changes.
        Only includes transitions to "approved" or "changes_requested".
    """
    changes = []

    for pr in prs:
        # Only track status changes for created PRs
        if pr.type != "created" or pr.review_status is None:
            continue

        old_status = old_statuses.get(pr.id)
        new_status = pr.review_status

        # Only notify on transitions to approved or changes_requested
        if old_status != new_status and new_status in ["approved", "changes_requested"]:
            changes.append((pr, old_status or "unknown", new_status))

    return changes


def notify_status_change(pr: PullRequest, new_status: str) -> None:
    """Send notification for PR status change.

    Args:
        pr: The pull request that changed.
        new_status: The new status ("approved" or "changes_requested").
    """
    if new_status == "approved":
        message = f"PR #{pr.number} approved"
    elif new_status == "changes_requested":
        message = f"PR #{pr.number} needs changes"
    else:
        return

    try:
        pync.notify(
            message,
            title="Reviewinator",
            open=pr.url,
        )
    except Exception:
        pass  # Silently ignore notification failures
