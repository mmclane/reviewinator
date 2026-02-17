# Filter Team Review Requests Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Filter out PRs where user is requested exclusively via specific teams, while showing PRs where individually requested or requested via non-excluded teams.

**Architecture:** Add `excluded_review_teams` config field with validation, then modify `_fetch_review_requests()` in GitHub client to check PR's `requested_reviewers` and `requested_teams` and filter based on whether user is individually requested or requested via non-excluded teams. Fail open on errors.

**Tech Stack:** Python 3.12, PyGithub, pytest, YAML config

---

## Task 1: Add Config Field with Validation

**Files:**
- Modify: `src/reviewinator/config.py`
- Test: `tests/test_config.py`

**Step 1: Write failing test for default empty list**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_defaults_to_empty_list(tmp_path):
    """Test that excluded_review_teams defaults to empty list if not specified."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    config = load_config(str(config_file))
    assert config.excluded_review_teams == []
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "Config object has no attribute 'excluded_review_teams'"

**Step 3: Add field to Config dataclass**

In `src/reviewinator/config.py`, add field to Config dataclass after `excluded_repos`:

```python
@dataclass
class Config:
    """Application configuration."""

    github_token: str
    excluded_repos: list[str]
    excluded_review_teams: list[str]
    created_pr_filter: str
    activity_lookback_days: int
    refresh_interval: int = 300
```

**Step 4: Update load_config to handle missing field**

In `src/reviewinator/config.py`, in `load_config()` function, after loading `data`:

```python
# Default excluded_review_teams to empty list if not present
if "excluded_review_teams" not in data:
    data["excluded_review_teams"] = []
```

**Step 5: Run test to verify it passes**

Run: `make test`
Expected: PASS

**Step 6: Commit**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: add excluded_review_teams config field with default"
```

---

## Task 2: Add Config Validation for Team Format

**Files:**
- Modify: `src/reviewinator/config.py`
- Test: `tests/test_config.py`

**Step 1: Write failing test for valid team format**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_accepts_valid_format(tmp_path):
    """Test that excluded_review_teams accepts valid 'org/team' format."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - snapptinc/all-engineers
  - myorg/team-foo
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    config = load_config(str(config_file))
    assert config.excluded_review_teams == ["snapptinc/all-engineers", "myorg/team-foo"]
```

**Step 2: Run test to verify it passes (should already pass)**

Run: `make test`
Expected: PASS (no validation yet, but loading works)

**Step 3: Write failing test for invalid team format (no slash)**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_rejects_no_slash(tmp_path):
    """Test that excluded_review_teams rejects entries without slash."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - invalidteam
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    with pytest.raises(ConfigError, match="excluded_review_teams entries must be in format 'org/team'"):
        load_config(str(config_file))
```

**Step 4: Run test to verify it fails**

Run: `make test`
Expected: FAIL (no validation yet, test expects ConfigError)

**Step 5: Write failing test for empty org**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_rejects_empty_org(tmp_path):
    """Test that excluded_review_teams rejects entries with empty org."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - /team
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    with pytest.raises(ConfigError, match="excluded_review_teams entries must be in format 'org/team'"):
        load_config(str(config_file))
```

**Step 6: Write failing test for empty team**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_rejects_empty_team(tmp_path):
    """Test that excluded_review_teams rejects entries with empty team."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
excluded_review_teams:
  - org/
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    with pytest.raises(ConfigError, match="excluded_review_teams entries must be in format 'org/team'"):
        load_config(str(config_file))
```

**Step 7: Write failing test for non-list value**

Add to `tests/test_config.py`:

```python
def test_excluded_review_teams_rejects_non_list(tmp_path):
    """Test that excluded_review_teams rejects non-list values."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
excluded_repos: []
excluded_review_teams: not-a-list
created_pr_filter: all
activity_lookback_days: 14
"""
    )
    with pytest.raises(ConfigError, match="excluded_review_teams must be a list"):
        load_config(str(config_file))
```

**Step 8: Run tests to verify they fail**

Run: `make test`
Expected: FAIL (validation not implemented yet)

**Step 9: Add validation to load_config**

In `src/reviewinator/config.py`, add validation after defaulting `excluded_review_teams`:

```python
# Validate excluded_review_teams
if not isinstance(data["excluded_review_teams"], list):
    raise ConfigError("excluded_review_teams must be a list")

import re
team_pattern = re.compile(r"^[a-zA-Z0-9-]+/[a-zA-Z0-9-]+$")
for team in data["excluded_review_teams"]:
    if not team_pattern.match(team):
        raise ConfigError(
            f"excluded_review_teams entries must be in format 'org/team' (got: {team})"
        )
```

**Step 10: Run tests to verify they pass**

Run: `make test`
Expected: PASS

**Step 11: Commit**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: add validation for excluded_review_teams format"
```

---

## Task 3: Add Helper Method for Team Filtering

**Files:**
- Modify: `src/reviewinator/github_client.py`
- Test: `tests/test_github_client.py`

**Step 1: Write failing test for individual reviewer (should show)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_individual_reviewer(mock_github):
    """Test that PR is shown when user is individually requested."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with individual reviewer and excluded team
    mock_pr = Mock()
    mock_user = Mock()
    mock_user.login = "testuser"
    mock_pr.requested_reviewers = [mock_user]

    mock_team = Mock()
    mock_org = Mock()
    mock_org.login = "testorg"
    mock_team.organization = mock_org
    mock_team.slug = "all-engineers"
    mock_pr.requested_teams = [mock_team]

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL with "GitHubClient has no attribute '_should_show_review_request'"

**Step 3: Write failing test for only excluded team (should hide)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_only_excluded_team(mock_github):
    """Test that PR is hidden when only requested via excluded team."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with only excluded team, no individual reviewers
    mock_pr = Mock()
    mock_pr.requested_reviewers = []

    mock_team = Mock()
    mock_org = Mock()
    mock_org.login = "testorg"
    mock_team.organization = mock_org
    mock_team.slug = "all-engineers"
    mock_pr.requested_teams = [mock_team]

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is False
```

**Step 4: Write failing test for non-excluded team (should show)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_non_excluded_team(mock_github):
    """Test that PR is shown when requested via non-excluded team."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with non-excluded team
    mock_pr = Mock()
    mock_pr.requested_reviewers = []

    mock_team = Mock()
    mock_org = Mock()
    mock_org.login = "testorg"
    mock_team.organization = mock_org
    mock_team.slug = "platform"
    mock_pr.requested_teams = [mock_team]

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 5: Write failing test for mixed teams (should show)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_mixed_teams(mock_github):
    """Test that PR is shown when requested via mix of excluded and non-excluded teams."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with both excluded and non-excluded teams
    mock_pr = Mock()
    mock_pr.requested_reviewers = []

    mock_team1 = Mock()
    mock_org1 = Mock()
    mock_org1.login = "testorg"
    mock_team1.organization = mock_org1
    mock_team1.slug = "all-engineers"

    mock_team2 = Mock()
    mock_org2 = Mock()
    mock_org2.login = "testorg"
    mock_team2.organization = mock_org2
    mock_team2.slug = "platform"

    mock_pr.requested_teams = [mock_team1, mock_team2]

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 6: Write failing test for empty reviewers (fail open - should show)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_no_reviewers_fail_open(mock_github):
    """Test that PR is shown when no reviewers/teams (fail open)."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with no reviewers or teams
    mock_pr = Mock()
    mock_pr.requested_reviewers = []
    mock_pr.requested_teams = []

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 7: Write failing test for None reviewers (fail open - should show)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_none_reviewers_fail_open(mock_github):
    """Test that PR is shown when requested_reviewers/teams are None (fail open)."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with None reviewers/teams
    mock_pr = Mock()
    mock_pr.requested_reviewers = None
    mock_pr.requested_teams = None

    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 8: Write failing test for team missing organization (should handle gracefully)**

Add to `tests/test_github_client.py`:

```python
def test_should_show_review_request_team_missing_org(mock_github):
    """Test that PR handles team missing organization gracefully."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )
    client = GitHubClient(mock_github, config)

    # Mock PR with team missing organization
    mock_pr = Mock()
    mock_pr.requested_reviewers = []

    mock_team = Mock()
    mock_team.organization = None
    mock_team.slug = "all-engineers"
    mock_pr.requested_teams = [mock_team]

    # Should fail open (show PR) when can't determine team info
    result = client._should_show_review_request(mock_pr, "testuser")
    assert result is True
```

**Step 9: Run tests to verify they fail**

Run: `make test`
Expected: FAIL (method not implemented)

**Step 10: Implement _should_show_review_request method**

In `src/reviewinator/github_client.py`, add method after `_get_review_status`:

```python
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
        individual_reviewers = [
            user.login for user in (pr.requested_reviewers or [])
        ]

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
```

**Step 11: Run tests to verify they pass**

Run: `make test`
Expected: PASS

**Step 12: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: add team filtering helper method"
```

---

## Task 4: Integrate Filtering into Fetch Logic

**Files:**
- Modify: `src/reviewinator/github_client.py`
- Test: `tests/test_github_client.py`

**Step 1: Write failing integration test**

Add to `tests/test_github_client.py`:

```python
def test_fetch_review_requests_filters_excluded_teams(mock_github):
    """Test that fetch_review_requests filters PRs based on excluded teams."""
    config = Config(
        github_token="test_token",
        excluded_repos=[],
        excluded_review_teams=["testorg/all-engineers"],
        created_pr_filter="all",
        activity_lookback_days=14,
    )

    # Mock search results
    mock_issue1 = Mock()
    mock_issue1.id = 1
    mock_issue1.number = 101
    mock_issue1.title = "PR 1 - individual request"
    mock_issue1.user.login = "author1"
    mock_issue1.repository.full_name = "testorg/repo1"
    mock_issue1.html_url = "https://github.com/testorg/repo1/pull/101"
    mock_issue1.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    mock_issue2 = Mock()
    mock_issue2.id = 2
    mock_issue2.number = 102
    mock_issue2.title = "PR 2 - only excluded team"
    mock_issue2.user.login = "author2"
    mock_issue2.repository.full_name = "testorg/repo1"
    mock_issue2.html_url = "https://github.com/testorg/repo1/pull/102"
    mock_issue2.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

    mock_github.search_issues.return_value = [mock_issue1, mock_issue2]

    # Mock repo.get_pull() for PR objects
    mock_repo = Mock()

    # PR 1: individually requested
    mock_pr1 = Mock()
    mock_user = Mock()
    mock_user.login = "testuser"
    mock_pr1.requested_reviewers = [mock_user]
    mock_pr1.requested_teams = []

    # PR 2: only excluded team
    mock_pr2 = Mock()
    mock_pr2.requested_reviewers = []
    mock_team = Mock()
    mock_org = Mock()
    mock_org.login = "testorg"
    mock_team.organization = mock_org
    mock_team.slug = "all-engineers"
    mock_pr2.requested_teams = [mock_team]

    mock_repo.get_pull = Mock(side_effect=lambda num: mock_pr1 if num == 101 else mock_pr2)
    mock_github.get_repo.return_value = mock_repo

    client = GitHubClient(mock_github, config)
    prs = client._fetch_review_requests()

    # Should only return PR 1 (individually requested)
    assert len(prs) == 1
    assert prs[0].number == 101
```

**Step 2: Run test to verify it fails**

Run: `make test`
Expected: FAIL (returns 2 PRs instead of 1, filtering not applied)

**Step 3: Modify _fetch_review_requests to apply filtering**

In `src/reviewinator/github_client.py`, modify `_fetch_review_requests()` method. Replace the current implementation with:

```python
def _fetch_review_requests(self) -> list[PullRequest]:
    """Fetch PRs where the current user is requested as reviewer.

    Returns:
        List of PullRequest objects with type=\"review_request\".
    """
    query = f"is:pr is:open review-requested:{self.username}"
    issues = self._github.search_issues(query)

    excluded_set = set(self._config.excluded_repos)
    prs = []

    for issue in issues:
        repo_name = issue.repository.full_name
        if repo_name in excluded_set:
            continue

        # Get full PR object to check reviewers/teams
        try:
            repo = self._github.get_repo(repo_name)
            pr_obj = repo.get_pull(issue.number)

            # Apply team filtering
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
```

**Step 4: Run test to verify it passes**

Run: `make test`
Expected: PASS

**Step 5: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: apply team filtering to review requests"
```

---

## Task 5: Update CLAUDE.md Documentation

**Files:**
- Modify: `CLAUDE.md`

**Step 1: Update configuration section**

In `CLAUDE.md`, update the configuration example to include `excluded_review_teams`:

```yaml
github_token: ghp_your_token_here
excluded_repos:
  - owner/archived-repo
excluded_review_teams:
  - org/team-slug
  - snapptinc/all-engineers
created_pr_filter: either
activity_lookback_days: 14
refresh_interval: 300
```

**Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md with excluded_review_teams config"
```

---

## Task 6: Run Full Test Suite and Verify

**Files:**
- All test files

**Step 1: Run full test suite**

Run: `make test`
Expected: All tests PASS

**Step 2: Run linter**

Run: `make lint`
Expected: No linting errors

**Step 3: Run formatter**

Run: `make format`
Expected: All files formatted correctly

**Step 4: Commit any formatting changes**

```bash
git add -A
git commit -m "style: apply formatting"
```

---

## Task 7: Manual Testing and User Config Update

**Files:**
- `~/.config/reviewinator/config.yaml`

**Step 1: Update user config**

Add to user's `~/.config/reviewinator/config.yaml`:

```yaml
excluded_review_teams:
  - snappt/pdt-snax
```

**Step 2: Run app manually**

Run: `make run`
Expected: App starts without errors, filters work correctly

**Step 3: Verify filtering behavior**

Check that:
- PRs where individually requested still show
- PRs only from excluded teams are filtered out
- PRs from non-excluded teams still show

**Step 4: Note completion**

Document in commit message that user config has been updated.

---

## Completion

After all tasks complete:
- All tests passing
- Linting clean
- User config updated with `snappt/pdt-snax` in excluded_review_teams
- Ready to push to main
