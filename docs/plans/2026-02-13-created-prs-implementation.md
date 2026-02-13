# Created PRs Tracking Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add functionality to track PRs created by the user with review status display and notifications.

**Architecture:** Refactor to unified PR model with type field, extend GitHubClient to fetch both review requests and created PRs, update menu rendering to show two sections with separate counts.

**Tech Stack:** Python, PyGithub, rumps, pytest, pydantic (for config validation)

---

## Task 1: Extend PullRequest Model

**Files:**
- Modify: `src/reviewinator/github_client.py:10-33`
- Test: `tests/test_github_client.py`

**Step 1: Write failing tests for new PR fields**

Add to `tests/test_github_client.py`:

```python
def test_pull_request_with_review_request_type():
    """Test PR with type='review_request'."""
    pr = PullRequest(
        id=1,
        number=123,
        title="Test PR",
        author="alice",
        repo="owner/repo",
        url="https://github.com/owner/repo/pull/123",
        created_at=datetime.now(timezone.utc),
        type="review_request",
        review_status=None,
    )
    assert pr.type == "review_request"
    assert pr.review_status is None


def test_pull_request_with_created_type():
    """Test PR with type='created' and review status."""
    pr = PullRequest(
        id=2,
        number=456,
        title="My PR",
        author="me",
        repo="owner/repo",
        url="https://github.com/owner/repo/pull/456",
        created_at=datetime.now(timezone.utc),
        type="created",
        review_status="waiting",
    )
    assert pr.type == "created"
    assert pr.review_status == "waiting"
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL with "TypeError: __init__() got unexpected keyword argument 'type'"

**Step 3: Add type and review_status fields to PullRequest**

In `src/reviewinator/github_client.py`, update the PullRequest dataclass:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `make test`

Expected: PASS (new tests pass, but existing tests will FAIL - we'll fix them next)

**Step 5: Update format_menu_item to handle both types**

Add test first:

```python
def test_format_menu_item_for_created_pr():
    """Test formatting created PR shows status instead of author."""
    pr = PullRequest(
        id=1,
        number=123,
        title="Test",
        author="me",
        repo="owner/repo",
        url="https://url",
        created_at=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
        type="created",
        review_status="waiting",
    )
    now = datetime(2024, 1, 1, 14, 0, tzinfo=timezone.utc)
    result = pr.format_menu_item(now)
    assert result == "#123 Test (waiting, 2h ago)"
```

Update `format_menu_item()` method:

```python
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
```

**Step 6: Fix existing tests**

Update all existing PR construction in tests to include `type` and `review_status`:

In `tests/test_github_client.py`, update `test_pull_request_creation`:

```python
def test_pull_request_creation():
    """Test creating a PullRequest object."""
    created = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
    pr = PullRequest(
        id=123,
        number=42,
        title="Fix bug",
        author="alice",
        repo="owner/repo",
        url="https://github.com/owner/repo/pull/42",
        created_at=created,
        type="review_request",
        review_status=None,
    )
    assert pr.id == 123
    assert pr.number == 42
    assert pr.title == "Fix bug"
    assert pr.author == "alice"
    assert pr.repo == "owner/repo"
    assert pr.created_at == created
    assert pr.type == "review_request"
    assert pr.review_status is None
```

Update `test_format_menu_item` similarly.

**Step 7: Run all tests**

Run: `make test`

Expected: PASS

**Step 8: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add type and review_status fields to PullRequest

Added type field to distinguish review_request vs created PRs.
Added review_status field for created PR status tracking.
Updated format_menu_item to show status for created PRs.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Extend Config Model

**Files:**
- Modify: `src/reviewinator/config.py`
- Test: `tests/test_config.py`

**Step 1: Write failing tests for new config fields**

Add to `tests/test_config.py`:

```python
def test_load_config_with_created_pr_repos(tmp_path: Path) -> None:
    """Test loading config with created_pr_repos."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "github_token: test_token\n"
        "review_request_repos:\n"
        "  - owner/repo1\n"
        "created_pr_repos:\n"
        "  - owner/repo2\n"
        "created_pr_filter: waiting\n"
    )
    config = load_config(config_file)
    assert config.github_token == "test_token"
    assert config.review_request_repos == ["owner/repo1"]
    assert config.created_pr_repos == ["owner/repo2"]
    assert config.created_pr_filter == "waiting"


def test_load_config_defaults_created_pr_repos_to_empty(tmp_path: Path) -> None:
    """Test config without created_pr_repos defaults to empty list."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "github_token: test_token\n"
        "review_request_repos:\n"
        "  - owner/repo1\n"
    )
    config = load_config(config_file)
    assert config.created_pr_repos == []
    assert config.created_pr_filter == "waiting"  # default


def test_load_config_backward_compat_repos(tmp_path: Path) -> None:
    """Test backward compatibility with 'repos' field."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "github_token: test_token\n"
        "repos:\n"
        "  - owner/repo1\n"
    )
    config = load_config(config_file)
    assert config.review_request_repos == ["owner/repo1"]


def test_load_config_invalid_created_pr_filter_raises(tmp_path: Path) -> None:
    """Test invalid created_pr_filter raises error."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "github_token: test_token\n"
        "review_request_repos:\n"
        "  - owner/repo1\n"
        "created_pr_filter: invalid\n"
    )
    with pytest.raises(ConfigError, match="created_pr_filter must be one of"):
        load_config(config_file)
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL

**Step 3: Update Config dataclass**

In `src/reviewinator/config.py`:

```python
@dataclass
class Config:
    """Application configuration."""

    github_token: str
    review_request_repos: list[str]
    created_pr_repos: list[str]
    created_pr_filter: str
    refresh_interval: int = 300
```

**Step 4: Update load_config function**

```python
def load_config(path: Path) -> Config:
    """Load and validate configuration from YAML file.

    Args:
        path: Path to config file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If config is missing or invalid.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    try:
        with path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ConfigError("Config must be a YAML mapping")

    # Required fields
    if "github_token" not in data:
        raise ConfigError("Missing required field: github_token")

    # Handle backward compatibility: repos -> review_request_repos
    if "review_request_repos" in data:
        review_request_repos = data["review_request_repos"]
    elif "repos" in data:
        review_request_repos = data["repos"]
    else:
        raise ConfigError("Missing required field: review_request_repos (or repos)")

    if not isinstance(review_request_repos, list) or not review_request_repos:
        raise ConfigError("review_request_repos must be a non-empty list")

    # Optional fields with defaults
    created_pr_repos = data.get("created_pr_repos", [])
    if not isinstance(created_pr_repos, list):
        raise ConfigError("created_pr_repos must be a list")

    created_pr_filter = data.get("created_pr_filter", "waiting")
    if created_pr_filter not in ["all", "waiting", "needs_attention"]:
        raise ConfigError(
            f"created_pr_filter must be one of: all, waiting, needs_attention (got: {created_pr_filter})"
        )

    refresh_interval = data.get("refresh_interval", 300)

    return Config(
        github_token=data["github_token"],
        review_request_repos=review_request_repos,
        created_pr_repos=created_pr_repos,
        created_pr_filter=created_pr_filter,
        refresh_interval=refresh_interval,
    )
```

**Step 5: Run tests to verify they pass**

Run: `make test`

Expected: PASS (but app tests will fail - we'll fix them)

**Step 6: Fix existing config tests**

Update tests that create Config objects to include new fields. Update `tests/test_config.py` test fixtures.

**Step 7: Run all tests**

Run: `make test`

Expected: PASS

**Step 8: Commit**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: add config fields for created PR tracking

Added review_request_repos (renamed from repos for clarity).
Added created_pr_repos and created_pr_filter fields.
Maintained backward compatibility with 'repos' field.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Add GitHub Client Methods for Created PRs

**Files:**
- Modify: `src/reviewinator/github_client.py`
- Test: `tests/test_github_client.py`

**Step 1: Write test for _get_review_status helper**

Add to `tests/test_github_client.py`:

```python
from unittest.mock import MagicMock


def test_get_review_status_no_reviews():
    """Test review status when PR has no reviews."""
    mock_pr = MagicMock()
    mock_pr.get_reviews.return_value = []

    client = GitHubClient(MagicMock(), [])
    status = client._get_review_status(mock_pr)
    assert status == "waiting"


def test_get_review_status_approved():
    """Test review status when latest review is approved."""
    mock_review1 = MagicMock()
    mock_review1.state = "COMMENTED"
    mock_review2 = MagicMock()
    mock_review2.state = "APPROVED"

    mock_pr = MagicMock()
    mock_pr.get_reviews.return_value = [mock_review1, mock_review2]

    client = GitHubClient(MagicMock(), [])
    status = client._get_review_status(mock_pr)
    assert status == "approved"


def test_get_review_status_changes_requested():
    """Test review status when latest review requests changes."""
    mock_review = MagicMock()
    mock_review.state = "CHANGES_REQUESTED"

    mock_pr = MagicMock()
    mock_pr.get_reviews.return_value = [mock_review]

    client = GitHubClient(MagicMock(), [])
    status = client._get_review_status(mock_pr)
    assert status == "changes_requested"


def test_get_review_status_commented():
    """Test review status when only comments exist."""
    mock_review = MagicMock()
    mock_review.state = "COMMENTED"

    mock_pr = MagicMock()
    mock_pr.get_reviews.return_value = [mock_review]

    client = GitHubClient(MagicMock(), [])
    status = client._get_review_status(mock_pr)
    assert status == "commented"
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL with "AttributeError: 'GitHubClient' object has no attribute '_get_review_status'"

**Step 3: Implement _get_review_status method**

In `src/reviewinator/github_client.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `make test`

Expected: PASS

**Step 5: Write test for _fetch_created_prs**

Add to `tests/test_github_client.py`:

```python
def test_fetch_created_prs_filters_by_repos():
    """Test fetching created PRs filters to configured repos."""
    mock_github = MagicMock()
    mock_user = MagicMock()
    mock_user.login = "testuser"
    mock_github.get_user.return_value = mock_user

    # Mock PR in configured repo
    mock_pr1 = MagicMock()
    mock_pr1.id = 1
    mock_pr1.number = 123
    mock_pr1.title = "My PR"
    mock_pr1.user.login = "testuser"
    mock_pr1.repository.full_name = "owner/repo1"
    mock_pr1.html_url = "https://url1"
    mock_pr1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)
    mock_pr1.get_reviews.return_value = []

    # Mock PR in non-configured repo
    mock_pr2 = MagicMock()
    mock_pr2.repository.full_name = "other/repo"

    mock_github.search_issues.return_value = [mock_pr1, mock_pr2]

    client = GitHubClient(mock_github, ["owner/repo1"])
    prs = client._fetch_created_prs(["owner/repo1"], "all")

    assert len(prs) == 1
    assert prs[0].number == 123
    assert prs[0].type == "created"
    assert prs[0].review_status == "waiting"
    mock_github.search_issues.assert_called_once_with("is:pr is:open author:testuser")
```

**Step 6: Run test to verify it fails**

Run: `make test`

Expected: FAIL

**Step 7: Implement _fetch_created_prs method**

In `src/reviewinator/github_client.py`:

```python
def _fetch_created_prs(self, repos: list[str], filter_type: str) -> list[PullRequest]:
    """Fetch PRs created by the current user.

    Args:
        repos: List of repos to filter to.
        filter_type: Filter type - "all", "waiting", or "needs_attention".

    Returns:
        List of PullRequest objects with type="created".
    """
    if not repos:
        return []

    query = f"is:pr is:open author:{self.username}"
    issues = self._github.search_issues(query)

    repos_set = set(repos)
    prs = []

    for issue in issues:
        repo_name = issue.repository.full_name
        if repo_name not in repos_set:
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
```

**Step 8: Run tests**

Run: `make test`

Expected: PASS

**Step 9: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add methods to fetch created PRs

Added _get_review_status to determine PR review state.
Added _fetch_created_prs to fetch user's created PRs with filtering.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Refactor GitHubClient to Unified fetch_prs

**Files:**
- Modify: `src/reviewinator/github_client.py`
- Test: `tests/test_github_client.py`

**Step 1: Write tests for refactored methods**

Add to `tests/test_github_client.py`:

```python
def test_fetch_prs_combines_both_types():
    """Test fetch_prs returns both review requests and created PRs."""
    mock_github = MagicMock()
    mock_user = MagicMock()
    mock_user.login = "testuser"
    mock_github.get_user.return_value = mock_user

    # Mock review request PR
    mock_issue1 = MagicMock()
    mock_issue1.id = 1
    mock_issue1.number = 100
    mock_issue1.title = "Review this"
    mock_issue1.user.login = "alice"
    mock_issue1.repository.full_name = "owner/repo1"
    mock_issue1.html_url = "https://url1"
    mock_issue1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Mock created PR
    mock_issue2 = MagicMock()
    mock_issue2.id = 2
    mock_issue2.number = 200
    mock_issue2.title = "My PR"
    mock_issue2.user.login = "testuser"
    mock_issue2.repository.full_name = "owner/repo2"
    mock_issue2.html_url = "https://url2"
    mock_issue2.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    mock_pr = MagicMock()
    mock_pr.get_reviews.return_value = []

    def search_side_effect(query):
        if "review-requested" in query:
            return [mock_issue1]
        else:
            return [mock_issue2]

    mock_github.search_issues.side_effect = search_side_effect
    mock_repo = MagicMock()
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo

    config = Config(
        github_token="token",
        review_request_repos=["owner/repo1"],
        created_pr_repos=["owner/repo2"],
        created_pr_filter="all",
    )

    client = GitHubClient(mock_github, config)
    prs = client.fetch_prs()

    assert len(prs) == 2
    review_prs = [p for p in prs if p.type == "review_request"]
    created_prs = [p for p in prs if p.type == "created"]
    assert len(review_prs) == 1
    assert len(created_prs) == 1
```

**Step 2: Run test to verify it fails**

Run: `make test`

Expected: FAIL

**Step 3: Refactor GitHubClient __init__ to take Config**

Update `src/reviewinator/github_client.py`:

```python
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
```

**Step 4: Rename fetch_review_requests to _fetch_review_requests**

Make it private and update to return type="review_request":

```python
def _fetch_review_requests(self) -> list[PullRequest]:
    """Fetch PRs where the current user is requested as reviewer.

    Returns:
        List of PullRequest objects with type="review_request".
    """
    query = f"is:pr is:open review-requested:{self.username}"
    issues = self._github.search_issues(query)

    repos_set = set(self._config.review_request_repos)
    prs = []

    for issue in issues:
        repo_name = issue.repository.full_name
        if repo_name not in repos_set:
            continue

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
```

**Step 5: Add new fetch_prs public method**

```python
def fetch_prs(self) -> list[PullRequest]:
    """Fetch all PRs (review requests and created PRs).

    Returns:
        Combined list of review request and created PRs.
    """
    review_requests = self._fetch_review_requests()
    created_prs = self._fetch_created_prs(
        self._config.created_pr_repos,
        self._config.created_pr_filter,
    )
    return review_requests + created_prs
```

**Step 6: Fix import in test file**

Update `tests/test_github_client.py` to import Config:

```python
from reviewinator.config import Config
```

**Step 7: Update all existing tests**

Update tests to pass Config instead of repos list to GitHubClient.

**Step 8: Run tests**

Run: `make test`

Expected: PASS (but app tests will fail)

**Step 9: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "refactor: unify PR fetching into fetch_prs method

Renamed fetch_review_requests to _fetch_review_requests (private).
Added fetch_prs public method that combines review requests and created PRs.
Updated GitHubClient to take Config instead of repos list.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update App to Use New GitHubClient

**Files:**
- Modify: `src/reviewinator/app.py`
- Test: `tests/test_app.py`

**Step 1: Update app initialization**

In `src/reviewinator/app.py`, update the `__init__` method:

```python
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
    self.client = GitHubClient(github, config)  # Pass config instead of repos

    # ... rest unchanged
```

**Step 2: Update _fetch_and_update method**

Change `fetch_review_requests` to `fetch_prs`:

```python
def _fetch_and_update(self) -> None:
    """Fetch PRs and update state (runs in background thread)."""
    try:
        self.prs = self.client.fetch_prs()  # Changed from fetch_review_requests

        # ... rest unchanged
```

**Step 3: Fix tests**

Update `tests/test_app.py` to create Config objects and update mocks.

**Step 4: Run tests**

Run: `make test`

Expected: PASS

**Step 5: Commit**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "refactor: update app to use unified fetch_prs

Updated app to call fetch_prs instead of fetch_review_requests.
Pass Config to GitHubClient instead of repos list.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Update Menu Rendering for Dual Sections

**Files:**
- Modify: `src/reviewinator/app.py:54-88`
- Test: `tests/test_app.py`

**Step 1: Write tests for dual section rendering**

Add to `tests/test_app.py`:

```python
def test_menu_shows_two_sections_when_both_types_present(sample_config):
    """Test menu shows both sections when review requests and created PRs exist."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        # Create one review request and one created PR
        review_pr = PullRequest(
            id=1, number=100, title="Review this", author="alice",
            repo="owner/repo1", url="https://url1",
            created_at=datetime.now(timezone.utc),
            type="review_request", review_status=None
        )
        created_pr = PullRequest(
            id=2, number=200, title="My PR", author="me",
            repo="owner/repo2", url="https://url2",
            created_at=datetime.now(timezone.utc),
            type="created", review_status="waiting"
        )

        app.prs = [review_pr, created_pr]
        app._do_update_menu()

        # Check menu has both sections
        menu_titles = [str(item.title) for item in app.menu.values()]
        assert "Reviews for You:" in menu_titles
        assert "Your PRs:" in menu_titles


def test_menu_shows_only_review_section_when_no_created_prs(sample_config):
    """Test menu only shows review section when no created PRs."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        review_pr = PullRequest(
            id=1, number=100, title="Review this", author="alice",
            repo="owner/repo1", url="https://url1",
            created_at=datetime.now(timezone.utc),
            type="review_request", review_status=None
        )

        app.prs = [review_pr]
        app._do_update_menu()

        menu_titles = [str(item.title) for item in app.menu.values()]
        assert "Reviews for You:" in menu_titles or "owner/repo1:" in menu_titles
        assert "Your PRs:" not in menu_titles


def test_menu_shows_only_created_section_when_no_reviews(sample_config):
    """Test menu only shows created section when no review requests."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        created_pr = PullRequest(
            id=2, number=200, title="My PR", author="me",
            repo="owner/repo2", url="https://url2",
            created_at=datetime.now(timezone.utc),
            type="created", review_status="waiting"
        )

        app.prs = [created_pr]
        app._do_update_menu()

        menu_titles = [str(item.title) for item in app.menu.values()]
        assert "Your PRs:" in menu_titles or "owner/repo2:" in menu_titles
        assert "Reviews for You:" not in menu_titles
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL

**Step 3: Update _do_update_menu to split by type**

In `src/reviewinator/app.py`:

```python
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

    # Show "No pending items" if both lists empty
    if not review_requests and not created_prs:
        self.menu.add(rumps.MenuItem("No pending items", callback=None))

    self.menu.add(rumps.separator)
    self.menu.add(rumps.MenuItem("Check Now", callback=self._on_check_now))
    self.menu.add(rumps.separator)
    self.menu.add(rumps.MenuItem("Quit", callback=self._on_quit))

    # Update title with dual counts (next task)
    self._update_title(review_requests, created_prs)
```

**Step 4: Add stub for _update_title**

```python
def _update_title(self, review_requests: list[PullRequest], created_prs: list[PullRequest]) -> None:
    """Update menu bar title based on PR counts."""
    # Temporary - will implement in next task
    count = len(self.prs)
    if count == 0:
        self.title = "✅"
    else:
        self.title = f"🔴 {count}"
```

**Step 5: Run tests**

Run: `make test`

Expected: PASS

**Step 6: Commit**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "feat: split menu into two sections for PR types

Updated menu rendering to show separate 'Reviews for You' and 'Your PRs' sections.
Added separator between sections when both exist.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update Menu Bar Title for Dual Counts

**Files:**
- Modify: `src/reviewinator/app.py:_update_title`
- Test: `tests/test_app.py`

**Step 1: Write tests for dual count titles**

Add to `tests/test_app.py`:

```python
def test_title_shows_dual_counts_when_both_types(sample_config):
    """Test title shows both counts when review requests and created PRs exist."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        review_pr = PullRequest(
            id=1, number=100, title="Review", author="alice",
            repo="repo1", url="url1", created_at=datetime.now(timezone.utc),
            type="review_request", review_status=None
        )
        created_pr = PullRequest(
            id=2, number=200, title="Mine", author="me",
            repo="repo2", url="url2", created_at=datetime.now(timezone.utc),
            type="created", review_status="waiting"
        )

        app.prs = [review_pr, created_pr]
        app._do_update_menu()
        assert app.title == "🔴 1 | 📤 1"


def test_title_shows_only_review_count_when_no_created(sample_config):
    """Test title shows only review count when no created PRs."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        review_pr = PullRequest(
            id=1, number=100, title="Review", author="alice",
            repo="repo1", url="url1", created_at=datetime.now(timezone.utc),
            type="review_request", review_status=None
        )

        app.prs = [review_pr]
        app._do_update_menu()
        assert app.title == "🔴 1"


def test_title_shows_only_created_count_when_no_reviews(sample_config):
    """Test title shows only created count when no review requests."""
    with patch("reviewinator.app.Github"), patch("reviewinator.app.load_cache"):
        app = ReviewinatorApp(sample_config)

        created_pr = PullRequest(
            id=2, number=200, title="Mine", author="me",
            repo="repo2", url="url2", created_at=datetime.now(timezone.utc),
            type="created", review_status="waiting"
        )

        app.prs = [created_pr]
        app._do_update_menu()
        assert app.title == "📤 1"
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL

**Step 3: Implement _update_title**

In `src/reviewinator/app.py`:

```python
def _update_title(self, review_requests: list[PullRequest], created_prs: list[PullRequest]) -> None:
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
```

**Step 4: Run tests**

Run: `make test`

Expected: PASS

**Step 5: Commit**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "feat: update title to show dual counts

Menu bar title now shows separate counts for review requests and created PRs.
Format: '🔴 X | 📤 Y' when both exist, single indicator otherwise.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 8: Update Cache for PR Status Tracking

**Files:**
- Modify: `src/reviewinator/cache.py`
- Test: `tests/test_cache.py`

**Step 1: Write tests for pr_statuses field**

Add to `tests/test_cache.py`:

```python
def test_cache_with_pr_statuses():
    """Test cache includes pr_statuses."""
    cache = Cache(
        seen_prs={1, 2, 3},
        pr_statuses={1: "waiting", 2: "approved"},
        last_checked=datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc),
    )
    assert cache.pr_statuses == {1: "waiting", 2: "approved"}


def test_cache_defaults_pr_statuses_to_empty():
    """Test cache defaults pr_statuses to empty dict."""
    cache = Cache(
        seen_prs=set(),
        last_checked=None,
    )
    assert cache.pr_statuses == {}


def test_save_and_load_cache_with_pr_statuses(tmp_path: Path):
    """Test saving and loading cache preserves pr_statuses."""
    cache_file = tmp_path / "cache.json"

    cache = Cache(
        seen_prs={1, 2},
        pr_statuses={1: "waiting", 2: "approved"},
        last_checked=datetime(2024, 1, 1, tzinfo=timezone.utc),
    )
    save_cache(cache, cache_file)

    loaded = load_cache(cache_file)
    assert loaded.pr_statuses == {1: "waiting", 2: "approved"}
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL

**Step 3: Update Cache dataclass**

In `src/reviewinator/cache.py`:

```python
@dataclass
class Cache:
    """Cache for tracking seen PRs and their statuses."""

    seen_prs: set[int]
    pr_statuses: dict[int, str] = field(default_factory=dict)
    last_checked: datetime | None = None
```

**Step 4: Update save_cache and load_cache**

Update serialization to handle dict:

```python
def save_cache(cache: Cache, path: Path) -> None:
    """Save cache to JSON file.

    Args:
        cache: Cache object to save.
        path: Path to cache file.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "seen_prs": list(cache.seen_prs),
        "pr_statuses": cache.pr_statuses,  # Already a dict
        "last_checked": cache.last_checked.isoformat() if cache.last_checked else None,
    }

    with path.open("w") as f:
        json.dump(data, f, indent=2)


def load_cache(path: Path) -> Cache:
    """Load cache from JSON file.

    Args:
        path: Path to cache file.

    Returns:
        Cache object, or empty Cache if file doesn't exist or is corrupted.
    """
    if not path.exists():
        return Cache(seen_prs=set(), pr_statuses={}, last_checked=None)

    try:
        with path.open() as f:
            data = json.load(f)

        last_checked = None
        if data.get("last_checked"):
            last_checked = datetime.fromisoformat(data["last_checked"])

        return Cache(
            seen_prs=set(data.get("seen_prs", [])),
            pr_statuses=data.get("pr_statuses", {}),
            last_checked=last_checked,
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return Cache(seen_prs=set(), pr_statuses={}, last_checked=None)
```

**Step 5: Run tests**

Run: `make test`

Expected: PASS

**Step 6: Commit**

```bash
git add src/reviewinator/cache.py tests/test_cache.py
git commit -m "feat: add pr_statuses to cache for status tracking

Added pr_statuses dict to track PR review status changes.
Updated save/load to handle new field.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Add Status Change Notifications

**Files:**
- Modify: `src/reviewinator/notifications.py`
- Modify: `src/reviewinator/app.py`
- Test: `tests/test_notifications.py`

**Step 1: Write tests for status change detection**

Add to `tests/test_notifications.py`:

```python
def test_find_status_changes_detects_approved():
    """Test finding PRs that changed to approved status."""
    pr = PullRequest(
        id=1, number=100, title="PR", author="me",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="created", review_status="approved"
    )

    old_statuses = {1: "waiting"}
    changes = find_status_changes([pr], old_statuses)

    assert len(changes) == 1
    assert changes[0][0] == pr
    assert changes[0][1] == "waiting"
    assert changes[0][2] == "approved"


def test_find_status_changes_detects_changes_requested():
    """Test finding PRs that changed to changes_requested status."""
    pr = PullRequest(
        id=2, number=200, title="PR", author="me",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="created", review_status="changes_requested"
    )

    old_statuses = {2: "waiting"}
    changes = find_status_changes([pr], old_statuses)

    assert len(changes) == 1
    assert changes[0][2] == "changes_requested"


def test_find_status_changes_ignores_unchanged():
    """Test no changes detected when status unchanged."""
    pr = PullRequest(
        id=3, number=300, title="PR", author="me",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="created", review_status="waiting"
    )

    old_statuses = {3: "waiting"}
    changes = find_status_changes([pr], old_statuses)

    assert len(changes) == 0


def test_find_status_changes_ignores_review_requests():
    """Test status changes only tracked for created PRs."""
    pr = PullRequest(
        id=4, number=400, title="PR", author="alice",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="review_request", review_status=None
    )

    old_statuses = {}
    changes = find_status_changes([pr], old_statuses)

    assert len(changes) == 0
```

**Step 2: Run tests to verify they fail**

Run: `make test`

Expected: FAIL

**Step 3: Implement find_status_changes**

In `src/reviewinator/notifications.py`:

```python
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
```

**Step 4: Write test for notification message**

```python
@patch("reviewinator.notifications.pync")
def test_notify_status_change_approved(mock_pync: MagicMock) -> None:
    """Test notification sent when PR is approved."""
    pr = PullRequest(
        id=1, number=100, title="My PR", author="me",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="created", review_status="approved"
    )

    notify_status_change(pr, "approved")

    mock_pync.notify.assert_called_once()
    call_args = mock_pync.notify.call_args[1]
    assert "PR #100 approved" in call_args["message"]


@patch("reviewinator.notifications.pync")
def test_notify_status_change_changes_requested(mock_pync: MagicMock) -> None:
    """Test notification sent when changes requested."""
    pr = PullRequest(
        id=2, number=200, title="My PR", author="me",
        repo="repo", url="url", created_at=datetime.now(timezone.utc),
        type="created", review_status="changes_requested"
    )

    notify_status_change(pr, "changes_requested")

    mock_pync.notify.assert_called_once()
    call_args = mock_pync.notify.call_args[1]
    assert "PR #200 needs changes" in call_args["message"]
```

**Step 5: Implement notify_status_change**

```python
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
```

**Step 6: Run tests**

Run: `make test`

Expected: PASS

**Step 7: Update app to use status change notifications**

In `src/reviewinator/app.py`, update `_fetch_and_update`:

```python
def _fetch_and_update(self) -> None:
    """Fetch PRs and update state (runs in background thread)."""
    try:
        self.prs = self.client.fetch_prs()

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
        # ... rest unchanged
```

**Step 8: Update imports**

Add to top of `src/reviewinator/app.py`:

```python
from reviewinator.notifications import find_new_prs, find_status_changes, notify_new_pr, notify_status_change
```

**Step 9: Run tests**

Run: `make test`

Expected: PASS

**Step 10: Commit**

```bash
git add src/reviewinator/notifications.py src/reviewinator/app.py tests/test_notifications.py
git commit -m "feat: add notifications for PR status changes

Added find_status_changes to detect status transitions.
Added notify_status_change to send notifications for approved/changes_requested.
Updated app to track and notify on status changes.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Update Documentation and Sample Config

**Files:**
- Modify: `README.md` (if exists)
- Create: `config.example.yaml`

**Step 1: Create example config file**

Create `config.example.yaml`:

```yaml
# Reviewinator Configuration Example

# GitHub personal access token
# Create at: https://github.com/settings/tokens
# Requires: repo scope
github_token: ghp_your_token_here

# Repos to monitor for review requests (where you're asked to review)
review_request_repos:
  - owner/repo1
  - org/repo2

# Repos to monitor for PRs you created (optional)
# If not specified or empty, created PR tracking is disabled
created_pr_repos:
  - owner/repo1
  - org/repo3

# Filter for which created PRs to show (optional, defaults to "waiting")
# Options:
#   - "all": Show all open PRs you created
#   - "waiting": Only show PRs still waiting for review
#   - "needs_attention": Only show PRs with changes requested
created_pr_filter: waiting

# How often to check for updates, in seconds (optional, defaults to 300)
refresh_interval: 300
```

**Step 2: Update README if it exists**

Check if README exists and update with new config fields.

**Step 3: Commit**

```bash
git add config.example.yaml README.md
git commit -m "docs: update config example and documentation

Added example config showing new created_pr_repos and created_pr_filter fields.
Updated documentation with new features.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Testing Checklist

Before considering this complete, verify:

- [ ] All unit tests pass (`make test`)
- [ ] Test coverage maintained or improved (`make test-cov`)
- [ ] No linting errors (`make lint`)
- [ ] Manual testing:
  - [ ] App shows review requests when configured
  - [ ] App shows created PRs when configured
  - [ ] Menu bar icon shows correct counts for both types
  - [ ] Status changes trigger notifications
  - [ ] Backward compatible with old config format (repos field)
  - [ ] Works when created_pr_repos is empty/missing

## Reference Skills

- **TDD:** @superpowers:test-driven-development - Use TDD workflow throughout
- **Verification:** @superpowers:verification-before-completion - Verify all tests pass before claiming completion
