"""Main menu bar application."""

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
        super().__init__("Reviewinator", quit_button=None)
        self.config = config
        self.cache = load_cache(get_cache_path())
        self.prs: list[PullRequest] = []
        self.is_first_run = True

        # Set up GitHub client
        github = Github(config.github_token)
        self.client = GitHubClient(github, config.repos)

        # Set up timer for polling
        self.timer = rumps.Timer(self._poll, config.refresh_interval)

    def _update_menu(self) -> None:
        """Rebuild the menu with current PRs."""
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
            self.title = "✓"  # Green check for no reviews
        else:
            self.title = f"🔴 {count}"  # Red indicator with count

    def _make_pr_callback(self, url: str):
        """Create a callback that opens a URL."""

        def callback(_):
            webbrowser.open(url)

        return callback

    def _poll(self, _=None) -> None:
        """Fetch PRs and update state."""
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

        self._update_menu()

    @rumps.clicked("Check Now")
    def _on_check_now(self, _) -> None:
        """Handle Check Now menu item."""
        self._poll()

    @rumps.clicked("Quit")
    def _on_quit(self, _) -> None:
        """Handle Quit menu item."""
        rumps.quit_application()

    def run(self) -> None:
        """Start the application."""
        # Do initial poll
        self._poll()
        # Start timer
        self.timer.start()
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
