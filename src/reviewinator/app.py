"""Main menu bar application."""

import threading
import webbrowser
from datetime import datetime, timezone
from itertools import groupby

import rumps
from github import Github

from reviewinator.cache import get_cache_path, load_cache, save_cache
from reviewinator.config import Config, ConfigError, get_config_path, load_config
from reviewinator.github_client import GitHubClient, PullRequest
from reviewinator.notifications import find_new_prs, notify_new_pr


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
        self.client = GitHubClient(github, config.review_request_repos)

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

        if not self.prs:
            self.menu.add(rumps.MenuItem("No pending reviews", callback=None))
        else:
            # Group PRs by repo
            sorted_prs = sorted(self.prs, key=lambda p: p.repo)
            for repo, repo_prs in groupby(sorted_prs, key=lambda p: p.repo):
                # Bold repo header (using MenuItem with callback=None makes it non-clickable)
                header = rumps.MenuItem(f"{repo}:", callback=None)
                self.menu.add(header)

                # PR items under the repo
                now = datetime.now(timezone.utc)
                for pr in repo_prs:
                    item = rumps.MenuItem(
                        f"  {pr.format_menu_item(now)}",
                        callback=self._make_pr_callback(pr.url),
                    )
                    self.menu.add(item)

        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Check Now", callback=self._on_check_now))
        self.menu.add(rumps.separator)
        self.menu.add(rumps.MenuItem("Quit", callback=self._on_quit))

        # Update title with count and color indicator
        count = len(self.prs)
        if count == 0:
            self.title = "✅"  # Green check for no reviews
        else:
            self.title = f"🔴 {count}"  # Red indicator with count

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
            self.prs = self.client.fetch_review_requests()

            # Find new PRs and notify (skip on first run)
            if not self.is_first_run:
                new_prs = find_new_prs(self.prs, self.cache.seen_prs)
                for pr in new_prs:
                    notify_new_pr(pr)

            # Update cache
            self.cache.seen_prs = {pr.id for pr in self.prs}
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
