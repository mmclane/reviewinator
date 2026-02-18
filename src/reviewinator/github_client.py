"""GitHub API client for fetching PR review requests."""

from dataclasses import dataclass
from datetime import datetime, timezone

from github import Github

from reviewinator.config import Config


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
    type: str  # "review_request" or "created"
    review_status: str | None  # "waiting", "approved", "changes_requested", "commented", or None

    def format_menu_item(self, now: datetime | None = None) -> str:
        """Format PR for menu display.

        Args:
            now: Current time for age calculation. Defaults to UTC now.

        Returns:
            Formatted string like "#142 Fix login bug (alice, 2h ago)" for review requests
            or "#142 Fix login bug (waiting, 2h ago)" for created PRs.
        """
        if now is None:
            now = datetime.now(timezone.utc)
        age = format_age(self.created_at, now)

        if self.type == "created":
            status = self.review_status or "unknown"
            return f"#{self.number} {self.title} ({status}, {age})"
        else:
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

    def __init__(self, github: Github, config: Config) -> None:
        """Initialize the client.

        Args:
            github: Authenticated PyGithub instance.
            config: Application configuration.
        """
        self._github = github
        self._config = config
        self._username: str | None = None

    @property
    def username(self) -> str:
        """Get the authenticated user's username (cached)."""
        if self._username is None:
            self._username = self._github.get_user().login
        return self._username

    def _get_review_status(self, pr) -> str:
        """Get the review status of a PR.

        Args:
            pr: PyGithub PullRequest object.

        Returns:
            Status string: "waiting", "approved", "changes_requested", or "commented".
        """
        reviews = list(pr.get_reviews())
        if not reviews:
            return "waiting"

        # Get the latest review state
        latest_review = reviews[-1]
        state = latest_review.state

        if state == "APPROVED":
            return "approved"
        elif state == "CHANGES_REQUESTED":
            return "changes_requested"
        elif state == "COMMENTED":
            return "commented"
        else:
            return "waiting"

    def _should_show_review_request(self, pr, username: str) -> bool:
        """Determine if a PR should be shown based on team filtering.

        Returns True if:
        - User is individually requested, OR
        - User is requested via any non-excluded team, OR
        - Unable to determine (fail open)

        Returns False only if:
        - Requested exclusively via excluded teams

        Args:
            pr: PyGithub PullRequest object.
            username: Username to check for.

        Returns:
            True if PR should be shown, False otherwise.
        """
        try:
            # Extract individual reviewers
            individual_reviewers = [user.login for user in (pr.requested_reviewers or [])]

            # Extract team reviewers as "org/slug"
            team_reviewers = []
            for team in pr.requested_teams or []:
                # Skip teams missing org or slug
                if not team.organization or not team.slug:
                    continue
                team_id = f"{team.organization.login}/{team.slug}"
                team_reviewers.append(team_id)

            # Show if individually requested
            if username in individual_reviewers:
                return True

            # Show if requested via any non-excluded team
            excluded_set = set(self._config.excluded_review_teams)
            if any(team not in excluded_set for team in team_reviewers):
                return True

            # Hide if only requested via excluded teams
            if team_reviewers and all(team in excluded_set for team in team_reviewers):
                return False

            # Fail open: show if no reviewers/teams or uncertain
            return True

        except Exception:
            # Fail open on any error
            return True

    def _fetch_created_prs(self, filter_type: str) -> list[PullRequest]:
        """Fetch PRs created by the current user.

        Args:
            filter_type: Filter type - "all", "waiting", "needs_attention", or "any".

        Returns:
            List of PullRequest objects with type="created".
        """
        query = f"is:pr is:open author:{self.username}"
        issues = self._github.search_issues(query)

        excluded_set = set(self._config.excluded_repos)
        prs = []

        for issue in issues:
            repo_name = issue.repository.full_name
            if repo_name in excluded_set:
                continue

            # Get the actual PR object to check reviews
            repo = self._github.get_repo(repo_name)
            pr_obj = repo.get_pull(issue.number)
            review_status = self._get_review_status(pr_obj)

            # Apply filter
            if filter_type == "waiting" and review_status != "waiting":
                continue
            elif filter_type == "needs_attention" and review_status != "changes_requested":
                continue
            elif filter_type == "any" and review_status not in ("waiting", "changes_requested", "approved"):
                continue

            pr = PullRequest(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                author=issue.user.login,
                repo=repo_name,
                url=issue.html_url,
                created_at=issue.created_at.replace(tzinfo=timezone.utc),
                type="created",
                review_status=review_status,
            )
            prs.append(pr)

        return prs

    def _fetch_review_requests(self) -> list[PullRequest]:
        """Fetch PRs where the current user is requested as reviewer.

        Returns:
            List of PullRequest objects with type="review_request".
        """
        query = f"is:pr is:open review-requested:{self.username}"
        issues = self._github.search_issues(query)

        excluded_set = set(self._config.excluded_repos)
        prs = []

        for issue in issues:
            repo_name = issue.repository.full_name
            if repo_name in excluded_set:
                continue

            # Only fetch full PR for team filtering if needed
            if self._config.excluded_review_teams:
                try:
                    repo = self._github.get_repo(repo_name)
                    pr_obj = repo.get_pull(issue.number)

                    if not self._should_show_review_request(pr_obj, self.username):
                        continue
                except Exception:
                    # Fail open: show PR if can't check teams
                    pass

            pr = PullRequest(
                id=issue.id,
                number=issue.number,
                title=issue.title,
                author=issue.user.login,
                repo=repo_name,
                url=issue.html_url,
                created_at=issue.created_at.replace(tzinfo=timezone.utc),
                type="review_request",
                review_status=None,
            )
            prs.append(pr)

        return prs

    def fetch_prs(self) -> list[PullRequest]:
        """Fetch all PRs (review requests and created PRs).

        Returns:
            Combined list of review request and created PRs.
        """
        review_requests = self._fetch_review_requests()
        created_prs = self._fetch_created_prs(self._config.created_pr_filter)
        return review_requests + created_prs
