"""Main menu bar application."""

import threading
import webbrowser
from datetime import datetime, timedelta, timezone
from itertools import groupby

import rumps
from github import Github

from reviewinator.cache import get_cache_path, load_cache, save_cache
from reviewinator.config import Config, ConfigError, get_config_path, load_config
from reviewinator.github_client import GitHubClient, PullRequest
from reviewinator.notifications import (
    find_new_prs,
    find_status_changes,
    notify_new_pr,
    notify_status_change,
)


class ReviewinatorApp(rumps.App):
    """Menu bar application for GitHub PR reviews."""

    def __init__(self, config: Config) -> None:
        """Initialize the app.

        Args:
            config: Application configuration.
        """
        super().__init__("Reviewinator", title="⏳", quit_button=None)
        self.config = config
        self.cache = load_cache(get_cache_path())
        self.prs: list[PullRequest] = []
        self.is_first_run = True
        self._ui_update_pending = False

        # Set up GitHub client
        github = Github(config.github_token)
        self.client = GitHubClient(github, config)

        # Set up timer for polling
        self.timer = rumps.Timer(self._poll, config.refresh_interval)

        # Set up timer for UI updates on main thread (checks every 0.1s)
        self._ui_update_timer = rumps.Timer(self._ui_update_callback, 0.1)
        self._ui_update_timer.start()

    def _ui_update_callback(self, _) -> None:
        """Called periodically on main thread to check for pending UI updates."""
        if self._ui_update_pending:
            self._ui_update_pending = False
            self._do_update_menu()

    def _schedule_ui_update(self) -> None:
        """Schedule a UI update on the main thread."""
        self._ui_update_pending = True

    def _do_update_menu(self) -> None:
        """Rebuild the menu with current PRs (must run on main thread)."""
        self.menu.clear()

        # Split PRs by type
        review_requests = [pr for pr in self.prs if pr.type == "review_request"]
        created_prs = [pr for pr in self.prs if pr.type == "created"]

        # Show "Reviews for You" section if we have review requests
        if review_requests:
            header = rumps.MenuItem("Reviews for You:", callback=None)
            self.menu.add(header)

            sorted_prs = sorted(review_requests, key=lambda p: p.repo)
            for repo, repo_prs in groupby(sorted_prs, key=lambda p: p.repo):
                repo_header = rumps.MenuItem(f"  {repo}:", callback=None)
                self.menu.add(repo_header)

                now = datetime.now(timezone.utc)
                for pr in repo_prs:
                    item = rumps.MenuItem(
                        f"    {pr.format_menu_item(now)}",
                        callback=self._make_pr_callback(pr.url),
                    )
                    self.menu.add(item)

        # Show "Your PRs" section if we have created PRs
        if created_prs:
            if review_requests:  # Add separator if both sections exist
                self.menu.add(rumps.separator)

            header = rumps.MenuItem("Your PRs:", callback=None)
            self.menu.add(header)

            sorted_prs = sorted(created_prs, key=lambda p: p.repo)
            for repo, repo_prs in groupby(sorted_prs, key=lambda p: p.repo):
                repo_header = rumps.MenuItem(f"  {repo}:", callback=None)
                self.menu.add(repo_header)

                now = datetime.now(timezone.utc)
                for pr in repo_prs:
                    item = rumps.MenuItem(
                        f"    {pr.format_menu_item(now)}",
                        callback=self._make_pr_callback(pr.url),
                    )
                    self.menu.add(item)

        # Show "No pending items" or recent repos if both lists empty
        if not review_requests and not created_prs:
            # Calculate repos with recent activity
            cutoff_date = datetime.now(timezone.utc) - timedelta(
                days=self.config.activity_lookback_days
            )
            active_repos = {
                repo: timestamp
                for repo, timestamp in self.cache.repo_activity.items()
                if timestamp > cutoff_date
            }

            if active_repos:
                # Show recent activity header
                header = rumps.MenuItem("Recent Activity:", callback=None)
                self.menu.add(header)

                # Sort by most recent first
                sorted_repos = sorted(active_repos.items(), key=lambda x: x[1], reverse=True)

                # Show up to 20 repos
                display_limit = 20
                for repo, timestamp in sorted_repos[:display_limit]:
                    # Count PRs for this repo from cache
                    pr_count = sum(1 for pr in self.prs if pr.repo == repo)
                    if pr_count == 0:
                        # Estimate from cache if no current PRs
                        pr_count = "recent"

                    # Calculate age
                    now = datetime.now(timezone.utc)
                    age_delta = now - timestamp
                    if age_delta.days == 0:
                        age_str = "today"
                    elif age_delta.days == 1:
                        age_str = "1d ago"
                    else:
                        age_str = f"{age_delta.days}d ago"

                    # Format: "owner/repo (N PRs, Xd ago)"
                    if isinstance(pr_count, int):
                        title = f"  {repo} ({pr_count} PRs, {age_str})"
                    else:
                        title = f"  {repo} (recent activity)"

                    item = rumps.MenuItem(
                        title, callback=self._make_pr_callback(f"https://github.com/{repo}/pulls")
                    )
                    self.menu.add(item)

                # Show overflow if needed
                if len(active_repos) > display_limit:
                    overflow_count = len(active_repos) - display_limit
                    self.menu.add(rumps.MenuItem(f"  and {overflow_count} more...", callback=None))
            else:
                # No activity - show default message
                self.menu.add(rumps.MenuItem("No pending items", callback=None))

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Check Now", callback=self._on_check_now))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=self._on_quit))

        # Update title with dual counts
        self._update_title(review_requests, created_prs)

    def _update_title(self, review_requests: list, created_prs: list) -> None:
        """Update menu bar title based on PR counts.

        Args:
            review_requests: List of review request PRs.
            created_prs: List of created PRs.
        """
        review_count = len(review_requests)
        created_count = len(created_prs)

        if review_count == 0 and created_count == 0:
            self.title = "✅"
        elif review_count > 0 and created_count > 0:
            self.title = f"🔴 {review_count} | 📤 {created_count}"
        elif review_count > 0:
            self.title = f"🔴 {review_count}"
        else:  # created_count > 0
            self.title = f"📤 {created_count}"

    def _update_menu(self) -> None:
        """Rebuild the menu with current PRs."""
        # For backward compatibility, call _do_update_menu directly
        # This is used during initial menu build in run()
        self._do_update_menu()

    def _make_pr_callback(self, url: str):
        """Create a callback that opens a URL."""

        def callback(_):
            webbrowser.open(url)

        return callback

    def _poll(self, _=None) -> None:
        """Fetch PRs in background thread to avoid blocking UI."""
        thread = threading.Thread(target=self._fetch_and_update, daemon=True)
        thread.start()

    def _fetch_and_update(self) -> None:
        """Fetch PRs and update state (runs in background thread)."""
        try:
            self.prs = self.client.fetch_prs()

            # Update repo activity for all current PRs
            now = datetime.now(timezone.utc)
            for pr in self.prs:
                self.cache.repo_activity[pr.repo] = now

            # Clean up old repo activity entries
            cutoff = now - timedelta(days=self.config.activity_lookback_days)
            self.cache.repo_activity = {
                repo: timestamp
                for repo, timestamp in self.cache.repo_activity.items()
                if timestamp > cutoff
            }

            # Find new PRs and notify (skip on first run)
            if not self.is_first_run:
                new_prs = find_new_prs(self.prs, self.cache.seen_prs)
                for pr in new_prs:
                    notify_new_pr(pr)

                # Find status changes and notify
                status_changes = find_status_changes(self.prs, self.cache.pr_statuses)
                for pr, old_status, new_status in status_changes:
                    notify_status_change(pr, new_status)

            # Update cache
            self.cache.seen_prs = {pr.id for pr in self.prs}
            self.cache.pr_statuses = {
                pr.id: pr.review_status
                for pr in self.prs
                if pr.type == "created" and pr.review_status is not None
            }
            self.cache.last_checked = datetime.now(timezone.utc)
            save_cache(self.cache, get_cache_path())

            self.is_first_run = False

        except Exception as e:
            # On error, keep showing stale data
            rumps.notification(
                title="Reviewinator Error",
                subtitle="Failed to fetch PRs",
                message=str(e),
            )

        # Schedule UI update on main thread
        self._schedule_ui_update()

    @rumps.clicked("Check Now")
    def _on_check_now(self, _) -> None:
        """Handle Check Now menu item."""
        self.title = "⏳"
        self._poll()

    @rumps.clicked("Quit")
    def _on_quit(self, _) -> None:
        """Handle Quit menu item."""
        rumps.quit_application()

    def _initial_poll(self, _) -> None:
        """Do the initial poll after app starts, then start regular timer."""
        self._startup_timer.stop()
        self.title = "⏳"
        self._poll()
        self.timer.start()

    def run(self) -> None:
        """Start the application."""
        # Build initial menu (shows ⏳ title)
        self._update_menu()
        # Schedule initial poll after app starts (avoids blocking menu bar icon)
        self._startup_timer = rumps.Timer(self._initial_poll, 0.5)
        self._startup_timer.start()
        # Run the app
        super().run()


def main() -> None:
    """Entry point for the application."""
    try:
        config = load_config(get_config_path())
    except ConfigError as e:
        rumps.notification(
            title="Reviewinator",
            subtitle="Configuration Error",
            message=str(e),
        )
        return

    app = ReviewinatorApp(config)
    app.run()


if __name__ == "__main__":
    main()
