# Repo Exclusion Filtering Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace inclusion-based repo filtering with exclusion-based filtering to automatically track all repos except those explicitly excluded.

**Architecture:** Remove separate review_request_repos and created_pr_repos fields. Add single excluded_repos list. Apply exclusion filter once in fetch_prs() after combining results from both fetch methods. Add "either" option to created_pr_filter.

**Tech Stack:** Python 3.12, PyGithub, pytest, YAML config

---

## Task 1: Update Config validation for excluded_repos

**Files:**
- Modify: `src/reviewinator/config.py:14-94`
- Test: `tests/test_config.py`

**Step 1: Write failing test for excluded_repos field**

Add to `tests/test_config.py`:

```python
def test_load_config_with_excluded_repos(tmp_path):
    """Test loading config with excluded_repos field."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos:
  - owner/repo1
  - owner/repo2
"""
    )
    config = load_config(config_file)
    assert config.excluded_repos == ["owner/repo1", "owner/repo2"]


def test_load_config_excluded_repos_defaults_to_empty_list(tmp_path):
    """Test excluded_repos defaults to empty list when not specified."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github_token: test_token\n")
    config = load_config(config_file)
    assert config.excluded_repos == []


def test_load_config_excluded_repos_must_be_list(tmp_path):
    """Test excluded_repos must be a list."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: "not-a-list"
"""
    )
    with pytest.raises(ConfigError, match="excluded_repos must be a list"):
        load_config(config_file)
```

**Step 2: Run tests to verify they fail**

Run: `make test`
Expected: FAIL - `AttributeError: 'Config' object has no attribute 'excluded_repos'`

**Step 3: Update Config dataclass to add excluded_repos field**

In `src/reviewinator/config.py`, update the Config dataclass (lines 14-21):

```python
@dataclass
class Config:
    """Application configuration."""

    github_token: str
    excluded_repos: list[str]
    created_pr_filter: str
    refresh_interval: int = 300
```

**Step 4: Update load_config to handle excluded_repos**

In `src/reviewinator/config.py`, update `load_config()` function (lines 34-94):

```python
def load_config(config_path: Path) -> Config:
    """Load and validate configuration from a YAML file.

    Args:
        config_path: Path to the config.yaml file.

    Returns:
        Validated Config object.

    Raises:
        ConfigError: If config file is missing or invalid.
    """
    if not config_path.exists():
        raise ConfigError(f"Config file not found: {config_path}")

    try:
        with config_path.open() as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise ConfigError(f"Invalid YAML: {e}")

    if not isinstance(data, dict):
        raise ConfigError("Config must be a YAML mapping")

    # Required fields
    if "github_token" not in data:
        raise ConfigError("Missing required field: github_token")

    # Optional fields with defaults
    excluded_repos = data.get("excluded_repos", [])
    if not isinstance(excluded_repos, list):
        raise ConfigError("excluded_repos must be a list")

    created_pr_filter = data.get("created_pr_filter", "either")
    valid_filters = ["all", "waiting", "needs_attention", "either"]
    if created_pr_filter not in valid_filters:
        raise ConfigError(
            f"created_pr_filter must be one of: {', '.join(valid_filters)} "
            f"(got: {created_pr_filter})"
        )

    refresh_interval = data.get("refresh_interval", 300)

    return Config(
        github_token=data["github_token"],
        excluded_repos=excluded_repos,
        created_pr_filter=created_pr_filter,
        refresh_interval=refresh_interval,
    )
```

**Step 5: Run tests to verify they pass**

Run: `make test`
Expected: Tests for excluded_repos pass, but other tests fail due to missing review_request_repos and created_pr_repos

**Step 6: Remove old repo list tests**

In `tests/test_config.py`, remove or update tests that reference `review_request_repos` or `created_pr_repos`. Find these tests:
- Tests validating review_request_repos
- Tests validating created_pr_repos
- Tests checking backward compatibility with "repos" field

Delete these tests entirely.

**Step 7: Run tests to verify config tests pass**

Run: `pytest tests/test_config.py -v`
Expected: All config tests pass

**Step 8: Commit config changes**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: replace repo inclusion lists with exclusion list

- Remove review_request_repos and created_pr_repos fields
- Add excluded_repos field (optional, defaults to empty list)
- Change created_pr_filter default to 'either'
- Add 'either' as valid created_pr_filter option
- Update tests for new config structure

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 2: Update created_pr_filter tests for "either" option

**Files:**
- Test: `tests/test_config.py`

**Step 1: Write test for created_pr_filter "either" option**

Add to `tests/test_config.py`:

```python
def test_load_config_created_pr_filter_either(tmp_path):
    """Test created_pr_filter accepts 'either' option."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
created_pr_filter: either
"""
    )
    config = load_config(config_file)
    assert config.created_pr_filter == "either"


def test_load_config_created_pr_filter_defaults_to_either(tmp_path):
    """Test created_pr_filter defaults to 'either'."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github_token: test_token\n")
    config = load_config(config_file)
    assert config.created_pr_filter == "either"
```

**Step 2: Run tests to verify they pass**

Run: `pytest tests/test_config.py::test_load_config_created_pr_filter_either -v`
Run: `pytest tests/test_config.py::test_load_config_created_pr_filter_defaults_to_either -v`
Expected: Both pass (already implemented in Task 1)

**Step 3: Commit test additions**

```bash
git add tests/test_config.py
git commit -m "test: add tests for created_pr_filter 'either' option

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 3: Update GitHubClient constructor to accept excluded_repos

**Files:**
- Modify: `src/reviewinator/github_client.py:74-93`
- Test: `tests/test_github_client.py`

**Step 1: Write failing test for GitHubClient with excluded_repos**

Add to `tests/test_github_client.py`:

```python
def test_github_client_accepts_excluded_repos(mock_github, mock_config):
    """Test GitHubClient accepts excluded_repos from config."""
    mock_config.excluded_repos = ["owner/excluded-repo"]
    client = GitHubClient(mock_github, mock_config)
    assert client._excluded_repos == ["owner/excluded-repo"]
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_github_client.py::test_github_client_accepts_excluded_repos -v`
Expected: FAIL - `AttributeError: 'GitHubClient' object has no attribute '_excluded_repos'`

**Step 3: Update GitHubClient.__init__ to store excluded_repos**

In `src/reviewinator/github_client.py`, update `__init__` method (lines 77-86):

```python
def __init__(self, github: Github, config: Config) -> None:
    """Initialize the client.

    Args:
        github: Authenticated PyGithub instance.
        config: Application configuration.
    """
    self._github = github
    self._config = config
    self._username: str | None = None
    self._excluded_repos = set(config.excluded_repos)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_github_client.py::test_github_client_accepts_excluded_repos -v`
Expected: FAIL - Need to update test to check for set, not list

**Step 5: Update test to check for set**

Update the test in `tests/test_github_client.py`:

```python
def test_github_client_accepts_excluded_repos(mock_github, mock_config):
    """Test GitHubClient accepts excluded_repos from config."""
    mock_config.excluded_repos = ["owner/excluded-repo"]
    client = GitHubClient(mock_github, mock_config)
    assert client._excluded_repos == {"owner/excluded-repo"}
```

**Step 6: Run test to verify it passes**

Run: `pytest tests/test_github_client.py::test_github_client_accepts_excluded_repos -v`
Expected: PASS

**Step 7: Commit constructor changes**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: store excluded_repos in GitHubClient

Convert excluded_repos list to set for O(1) lookup performance.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 4: Remove repo filtering from _fetch_review_requests

**Files:**
- Modify: `src/reviewinator/github_client.py:171-201`
- Test: `tests/test_github_client.py`

**Step 1: Write test verifying _fetch_review_requests returns all repos**

Add to `tests/test_github_client.py`:

```python
def test_fetch_review_requests_returns_all_repos(mock_github, mock_config):
    """Test _fetch_review_requests returns PRs from all repos without filtering."""
    mock_config.excluded_repos = ["owner/excluded-repo"]

    # Mock search results with PRs from different repos
    pr1 = Mock()
    pr1.id = 1
    pr1.number = 101
    pr1.title = "PR from included repo"
    pr1.user.login = "author1"
    pr1.repository.full_name = "owner/included-repo"
    pr1.html_url = "https://github.com/owner/included-repo/pull/101"
    pr1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    pr2 = Mock()
    pr2.id = 2
    pr2.number = 102
    pr2.title = "PR from excluded repo"
    pr2.user.login = "author2"
    pr2.repository.full_name = "owner/excluded-repo"
    pr2.html_url = "https://github.com/owner/excluded-repo/pull/102"
    pr2.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    mock_github.search_issues.return_value = [pr1, pr2]

    client = GitHubClient(mock_github, mock_config)
    results = client._fetch_review_requests()

    # Should return both PRs (no filtering in _fetch_review_requests)
    assert len(results) == 2
    assert results[0].repo == "owner/included-repo"
    assert results[1].repo == "owner/excluded-repo"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_github_client.py::test_fetch_review_requests_returns_all_repos -v`
Expected: FAIL - Current implementation filters to review_request_repos, which no longer exists

**Step 3: Update _fetch_review_requests to remove filtering**

In `src/reviewinator/github_client.py`, update `_fetch_review_requests()` (lines 171-201):

```python
def _fetch_review_requests(self) -> list[PullRequest]:
    """Fetch PRs where the current user is requested as reviewer.

    Returns:
        List of PullRequest objects with type="review_request".
    """
    query = f"is:pr is:open review-requested:{self.username}"
    issues = self._github.search_issues(query)

    prs = []

    for issue in issues:
        repo_name = issue.repository.full_name

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

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_github_client.py::test_fetch_review_requests_returns_all_repos -v`
Expected: PASS

**Step 5: Commit _fetch_review_requests changes**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "refactor: remove repo filtering from _fetch_review_requests

Filtering now happens in fetch_prs() after combining results.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 5: Update _fetch_created_prs to remove repo filtering and add "either" option

**Files:**
- Modify: `src/reviewinator/github_client.py:121-169`
- Test: `tests/test_github_client.py`

**Step 1: Write test for "either" filter option**

Add to `tests/test_github_client.py`:

```python
def test_fetch_created_prs_either_filter(mock_github, mock_config):
    """Test created_pr_filter='either' includes waiting and changes_requested."""
    mock_config.excluded_repos = []
    mock_config.created_pr_filter = "either"

    # Mock PRs with different review statuses
    waiting_issue = Mock()
    waiting_issue.id = 1
    waiting_issue.number = 101
    waiting_issue.title = "Waiting PR"
    waiting_issue.user.login = "user"
    waiting_issue.repository.full_name = "owner/repo"
    waiting_issue.html_url = "https://github.com/owner/repo/pull/101"
    waiting_issue.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    changes_issue = Mock()
    changes_issue.id = 2
    changes_issue.number = 102
    changes_issue.title = "Changes Requested PR"
    changes_issue.user.login = "user"
    changes_issue.repository.full_name = "owner/repo"
    changes_issue.html_url = "https://github.com/owner/repo/pull/102"
    changes_issue.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    approved_issue = Mock()
    approved_issue.id = 3
    approved_issue.number = 103
    approved_issue.title = "Approved PR"
    approved_issue.user.login = "user"
    approved_issue.repository.full_name = "owner/repo"
    approved_issue.html_url = "https://github.com/owner/repo/pull/103"
    approved_issue.created_at = datetime(2024, 1, 3, tzinfo=timezone.utc)

    mock_github.search_issues.return_value = [waiting_issue, changes_issue, approved_issue]

    # Mock repo and PR objects
    mock_repo = Mock()
    mock_github.get_repo.return_value = mock_repo

    waiting_pr = Mock()
    waiting_pr.get_reviews.return_value = []

    changes_pr = Mock()
    changes_review = Mock()
    changes_review.state = "CHANGES_REQUESTED"
    changes_pr.get_reviews.return_value = [changes_review]

    approved_pr = Mock()
    approved_review = Mock()
    approved_review.state = "APPROVED"
    approved_pr.get_reviews.return_value = [approved_review]

    mock_repo.get_pull.side_effect = [waiting_pr, changes_pr, approved_pr]

    client = GitHubClient(mock_github, mock_config)
    results = client._fetch_created_prs()

    # Should include waiting and changes_requested, exclude approved
    assert len(results) == 2
    assert results[0].review_status == "waiting"
    assert results[1].review_status == "changes_requested"
```

**Step 2: Write test for removing repo filtering from _fetch_created_prs**

Add to `tests/test_github_client.py`:

```python
def test_fetch_created_prs_returns_all_repos(mock_github, mock_config):
    """Test _fetch_created_prs returns PRs from all repos without filtering."""
    mock_config.excluded_repos = ["owner/excluded-repo"]
    mock_config.created_pr_filter = "all"

    pr1 = Mock()
    pr1.id = 1
    pr1.number = 101
    pr1.title = "PR from included repo"
    pr1.user.login = "user"
    pr1.repository.full_name = "owner/included-repo"
    pr1.html_url = "https://github.com/owner/included-repo/pull/101"
    pr1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    pr2 = Mock()
    pr2.id = 2
    pr2.number = 102
    pr2.title = "PR from excluded repo"
    pr2.user.login = "user"
    pr2.repository.full_name = "owner/excluded-repo"
    pr2.html_url = "https://github.com/owner/excluded-repo/pull/102"
    pr2.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    mock_github.search_issues.return_value = [pr1, pr2]

    mock_repo = Mock()
    mock_pr = Mock()
    mock_pr.get_reviews.return_value = []
    mock_repo.get_pull.return_value = mock_pr
    mock_github.get_repo.return_value = mock_repo

    client = GitHubClient(mock_github, mock_config)
    results = client._fetch_created_prs()

    # Should return both PRs (no filtering in _fetch_created_prs)
    assert len(results) == 2
    assert results[0].repo == "owner/included-repo"
    assert results[1].repo == "owner/excluded-repo"
```

**Step 3: Run tests to verify they fail**

Run: `pytest tests/test_github_client.py::test_fetch_created_prs_either_filter -v`
Run: `pytest tests/test_github_client.py::test_fetch_created_prs_returns_all_repos -v`
Expected: Both FAIL

**Step 4: Update _fetch_created_prs to remove repo filtering and add "either" logic**

In `src/reviewinator/github_client.py`, update `_fetch_created_prs()` (lines 121-169):

```python
def _fetch_created_prs(self) -> list[PullRequest]:
    """Fetch PRs created by the current user.

    Returns:
        List of PullRequest objects with type="created".
    """
    query = f"is:pr is:open author:{self.username}"
    issues = self._github.search_issues(query)

    filter_type = self._config.created_pr_filter
    prs = []

    for issue in issues:
        repo_name = issue.repository.full_name

        # Get the actual PR object to check reviews
        repo = self._github.get_repo(repo_name)
        pr_obj = repo.get_pull(issue.number)
        review_status = self._get_review_status(pr_obj)

        # Apply filter
        if filter_type == "waiting" and review_status != "waiting":
            continue
        elif filter_type == "needs_attention" and review_status != "changes_requested":
            continue
        elif filter_type == "either" and review_status not in ["waiting", "changes_requested"]:
            continue
        # filter_type == "all" includes everything

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

**Step 5: Run tests to verify they pass**

Run: `pytest tests/test_github_client.py::test_fetch_created_prs_either_filter -v`
Run: `pytest tests/test_github_client.py::test_fetch_created_prs_returns_all_repos -v`
Expected: Both PASS

**Step 6: Commit _fetch_created_prs changes**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add 'either' filter and remove repo filtering from _fetch_created_prs

- Add 'either' option to show PRs that are waiting OR changes_requested
- Remove repo filtering (now happens in fetch_prs)
- Simplify method signature (no longer needs repos parameter)

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 6: Update fetch_prs to apply exclusion filtering

**Files:**
- Modify: `src/reviewinator/github_client.py:203-214`
- Test: `tests/test_github_client.py`

**Step 1: Write test for exclusion filtering in fetch_prs**

Add to `tests/test_github_client.py`:

```python
def test_fetch_prs_excludes_repos(mock_github, mock_config):
    """Test fetch_prs excludes repos in excluded_repos list."""
    mock_config.excluded_repos = ["owner/excluded-repo"]
    mock_config.created_pr_filter = "all"

    # Mock review request from excluded repo
    review_pr = Mock()
    review_pr.id = 1
    review_pr.number = 101
    review_pr.title = "Review Request"
    review_pr.user.login = "author"
    review_pr.repository.full_name = "owner/excluded-repo"
    review_pr.html_url = "https://github.com/owner/excluded-repo/pull/101"
    review_pr.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    # Mock review request from included repo
    included_review_pr = Mock()
    included_review_pr.id = 2
    included_review_pr.number = 102
    included_review_pr.title = "Included Review"
    included_review_pr.user.login = "author"
    included_review_pr.repository.full_name = "owner/included-repo"
    included_review_pr.html_url = "https://github.com/owner/included-repo/pull/102"
    included_review_pr.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    # Mock created PR from excluded repo
    created_pr = Mock()
    created_pr.id = 3
    created_pr.number = 103
    created_pr.title = "Created PR"
    created_pr.user.login = "user"
    created_pr.repository.full_name = "owner/excluded-repo"
    created_pr.html_url = "https://github.com/owner/excluded-repo/pull/103"
    created_pr.created_at = datetime(2024, 1, 3, tzinfo=timezone.utc)

    # Mock created PR from included repo
    included_created_pr = Mock()
    included_created_pr.id = 4
    included_created_pr.number = 104
    included_created_pr.title = "Included Created PR"
    included_created_pr.user.login = "user"
    included_created_pr.repository.full_name = "owner/included-repo"
    included_created_pr.html_url = "https://github.com/owner/included-repo/pull/104"
    included_created_pr.created_at = datetime(2024, 1, 4, tzinfo=timezone.utc)

    # Mock search_issues to return different results for different queries
    def search_side_effect(query):
        if "review-requested" in query:
            return [review_pr, included_review_pr]
        elif "author:" in query:
            return [created_pr, included_created_pr]
        return []

    mock_github.search_issues.side_effect = search_side_effect

    # Mock repo and PR for created PRs
    mock_repo = Mock()
    mock_pr_obj = Mock()
    mock_pr_obj.get_reviews.return_value = []
    mock_repo.get_pull.return_value = mock_pr_obj
    mock_github.get_repo.return_value = mock_repo

    client = GitHubClient(mock_github, mock_config)
    results = client.fetch_prs()

    # Should only include PRs from owner/included-repo
    assert len(results) == 2
    assert all(pr.repo == "owner/included-repo" for pr in results)
    assert results[0].type == "review_request"
    assert results[1].type == "created"


def test_fetch_prs_includes_all_when_no_exclusions(mock_github, mock_config):
    """Test fetch_prs includes all repos when excluded_repos is empty."""
    mock_config.excluded_repos = []
    mock_config.created_pr_filter = "all"

    review_pr = Mock()
    review_pr.id = 1
    review_pr.number = 101
    review_pr.title = "Review Request"
    review_pr.user.login = "author"
    review_pr.repository.full_name = "owner/repo1"
    review_pr.html_url = "https://github.com/owner/repo1/pull/101"
    review_pr.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    created_pr = Mock()
    created_pr.id = 2
    created_pr.number = 102
    created_pr.title = "Created PR"
    created_pr.user.login = "user"
    created_pr.repository.full_name = "owner/repo2"
    created_pr.html_url = "https://github.com/owner/repo2/pull/102"
    created_pr.created_at = datetime(2024, 1, 2, tzinfo=timezone.utc)

    def search_side_effect(query):
        if "review-requested" in query:
            return [review_pr]
        elif "author:" in query:
            return [created_pr]
        return []

    mock_github.search_issues.side_effect = search_side_effect

    mock_repo = Mock()
    mock_pr_obj = Mock()
    mock_pr_obj.get_reviews.return_value = []
    mock_repo.get_pull.return_value = mock_pr_obj
    mock_github.get_repo.return_value = mock_repo

    client = GitHubClient(mock_github, mock_config)
    results = client.fetch_prs()

    # Should include PRs from both repos
    assert len(results) == 2
    assert results[0].repo == "owner/repo1"
    assert results[1].repo == "owner/repo2"
```

**Step 2: Run tests to verify they fail**

Run: `pytest tests/test_github_client.py::test_fetch_prs_excludes_repos -v`
Run: `pytest tests/test_github_client.py::test_fetch_prs_includes_all_when_no_exclusions -v`
Expected: Both FAIL - fetch_prs doesn't apply exclusion filtering yet

**Step 3: Update fetch_prs to apply exclusion filtering**

In `src/reviewinator/github_client.py`, update `fetch_prs()` (lines 203-214):

```python
def fetch_prs(self) -> list[PullRequest]:
    """Fetch all PRs (review requests and created PRs).

    Returns:
        Combined list of review request and created PRs, excluding repos
        in the excluded_repos list.
    """
    review_requests = self._fetch_review_requests()
    created_prs = self._fetch_created_prs()
    all_prs = review_requests + created_prs

    # Filter out excluded repos
    filtered_prs = [pr for pr in all_prs if pr.repo not in self._excluded_repos]

    return filtered_prs
```

**Step 4: Run tests to verify they pass**

Run: `pytest tests/test_github_client.py::test_fetch_prs_excludes_repos -v`
Run: `pytest tests/test_github_client.py::test_fetch_prs_includes_all_when_no_exclusions -v`
Expected: Both PASS

**Step 5: Run all github_client tests**

Run: `pytest tests/test_github_client.py -v`
Expected: All tests pass

**Step 6: Commit fetch_prs changes**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: apply exclusion filtering in fetch_prs

Combine results from both fetch methods, then filter out excluded repos
in a single pass. This centralizes filtering logic and improves
maintainability.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 7: Update app.py to use new config structure

**Files:**
- Modify: `src/reviewinator/app.py:38-40`

**Step 1: Update app.py to remove passing repo lists to GitHubClient**

In `src/reviewinator/app.py`, the GitHubClient constructor call is already correct (lines 38-40):

```python
# Set up GitHub client
github = Github(config.github_token)
self.client = GitHubClient(github, config)
```

No changes needed - GitHubClient already receives the full config object and extracts `excluded_repos` in its `__init__` method.

**Step 2: Verify app still works**

Run: `make test`
Expected: All tests pass

**Step 3: No commit needed (no changes)**

---

## Task 8: Update CLAUDE.md documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update config example in CLAUDE.md**

In `CLAUDE.md`, update the configuration section (around line 21):

```markdown
## Configuration

Create `~/.config/reviewinator/config.yaml`:
```yaml
github_token: ghp_your_token_here
excluded_repos:
  - owner/archived-repo
  - org/old-project
created_pr_filter: either  # Options: all, waiting, needs_attention, either
refresh_interval: 300  # optional, defaults to 300 seconds
```

The `excluded_repos` field is optional and lists repos to exclude from tracking.
The `created_pr_filter` field controls which of your created PRs to show:
- `either` (default): Show PRs waiting for review OR needing changes
- `waiting`: Show only PRs waiting for initial review
- `needs_attention`: Show only PRs with changes requested
- `all`: Show all your open PRs
```

**Step 2: Commit documentation update**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for exclusion-based filtering

Update config example to show excluded_repos instead of repo inclusion
lists. Add explanation of created_pr_filter options.

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 9: Run full test suite and verify

**Files:**
- None (verification only)

**Step 1: Run all tests**

Run: `make test`
Expected: All tests pass

**Step 2: Run linting**

Run: `make lint`
Expected: No linting errors

**Step 3: If linting fails, fix with format**

Run: `make format`
Run: `make lint`
Expected: All checks pass

**Step 4: Commit any formatting changes**

```bash
git add -A
git commit -m "style: apply linting fixes

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Task 10: Update user config file

**Files:**
- Modify: `~/.config/reviewinator/config.yaml`

**Step 1: Back up current config**

Run: `cp ~/.config/reviewinator/config.yaml ~/.config/reviewinator/config.yaml.backup`

**Step 2: Update config to new format**

Edit `~/.config/reviewinator/config.yaml` to remove `review_request_repos` and `created_pr_repos`, add `excluded_repos`:

Example:
```yaml
github_token: <your token>
excluded_repos: []  # Add any repos you want to exclude
created_pr_filter: either
refresh_interval: 300
```

**Step 3: Test the app**

Run: `make run`
Expected: App starts successfully and shows PRs from all repos

**Step 4: No commit needed (user config not in repo)**

---

## Task 11: Final verification and cleanup

**Files:**
- None (verification only)

**Step 1: Verify all tests pass**

Run: `make test-cov`
Expected: All tests pass with good coverage

**Step 2: Verify app runs correctly**

Run: `make run`
Expected: App starts, polls GitHub, shows PRs from all repos except excluded ones

**Step 3: Check git status**

Run: `git status`
Expected: Working tree clean

**Step 4: Review commit history**

Run: `git log --oneline -10`
Expected: See all commits from this implementation

**Step 5: Done!**

The implementation is complete. The app now uses exclusion-based filtering instead of inclusion-based filtering.
