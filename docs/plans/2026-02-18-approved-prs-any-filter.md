# Approved PRs / Rename `either` to `any` Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Show approved PRs in the menu bar by extending the `either` filter (renamed `any`) to include `approved` review status.

**Architecture:** Three code changes (config validation, filter logic, live config file) plus test updates. No new data structures needed — `review_status="approved"` is already supported by the `PullRequest` dataclass and `_get_review_status`.

**Tech Stack:** Python, PyGithub, pytest, uv (run tests with `make test`)

---

### Task 1: Update config validation — replace `either` with `any`

**Files:**
- Modify: `src/reviewinator/config.py:84-90`
- Test: `tests/test_config.py`

**Step 1: Write two failing tests**

In `tests/test_config.py`, replace the two existing `either` tests:

```python
def test_load_config_created_pr_filter_any(self, tmp_path: Path) -> None:
    """Test created_pr_filter accepts 'any' option."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
github_token: test_token
created_pr_filter: any
"""
    )
    config = load_config(config_file)
    assert config.created_pr_filter == "any"

def test_load_config_created_pr_filter_defaults_to_any(self, tmp_path: Path) -> None:
    """Test created_pr_filter defaults to 'any'."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github_token: test_token\n")
    config = load_config(config_file)
    assert config.created_pr_filter == "any"

def test_load_config_created_pr_filter_either_rejected(self, tmp_path: Path) -> None:
    """Test created_pr_filter rejects old 'either' value."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("github_token: test_token\ncreated_pr_filter: either\n")
    with pytest.raises(ConfigError, match="created_pr_filter must be one of"):
        load_config(config_file)
```

**Step 2: Run tests to confirm they fail**

```
make test
```

Expected: 3 failures — `either` is still accepted, `any` is not, default is `either`.

**Step 3: Update config.py**

In `src/reviewinator/config.py`, change lines 84–90:

```python
created_pr_filter = data.get("created_pr_filter", "any")
valid_filters = ["all", "waiting", "needs_attention", "any"]
if created_pr_filter not in valid_filters:
    raise ConfigError(
        f"created_pr_filter must be one of: {', '.join(valid_filters)} "
        f"(got: {created_pr_filter})"
    )
```

**Step 4: Run tests to confirm they pass**

```
make test
```

Expected: all pass.

**Step 5: Commit**

```bash
git add src/reviewinator/config.py tests/test_config.py
git commit -m "feat: rename created_pr_filter 'either' to 'any'"
```

---

### Task 2: Update filter logic — include `approved` in `any`

**Files:**
- Modify: `src/reviewinator/github_client.py:198-203`
- Test: `tests/test_github_client.py`

**Step 1: Write failing tests**

Add to `tests/test_github_client.py` (a new `TestFetchCreatedPRs` class or add to existing):

```python
class TestFetchCreatedPRsFilter:
    """Tests for _fetch_created_prs filter behavior."""

    def _make_client(self, mock_github, filter_type):
        config = Config(
            github_token="test",
            excluded_repos=[],
            excluded_review_teams=[],
            created_pr_filter=filter_type,
            activity_lookback_days=14,
        )
        return GitHubClient(mock_github, config)

    def _make_issue(self, status_state):
        """Make a mock issue and a PR object with the given review state."""
        mock_issue = MagicMock()
        mock_issue.id = 1
        mock_issue.number = 42
        mock_issue.title = "Test PR"
        mock_issue.user.login = "me"
        mock_issue.repository.full_name = "org/repo"
        mock_issue.html_url = "https://github.com/org/repo/pull/42"
        mock_issue.created_at = datetime(2024, 1, 1, tzinfo=timezone.utc)

        mock_review = MagicMock()
        mock_review.state = status_state

        mock_pr_obj = MagicMock()
        mock_pr_obj.get_reviews.return_value = [mock_review]

        return mock_issue, mock_pr_obj

    def test_any_filter_includes_approved(self) -> None:
        """'any' filter should include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "approved"

    def test_any_filter_includes_waiting(self) -> None:
        """'any' filter should include waiting PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("PENDING")
        mock_pr_obj.get_reviews.return_value = []  # no reviews = waiting
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "waiting"

    def test_any_filter_includes_changes_requested(self) -> None:
        """'any' filter should include changes_requested PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("CHANGES_REQUESTED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "any")
        prs = client._fetch_created_prs("any")

        assert len(prs) == 1
        assert prs[0].review_status == "changes_requested"

    def test_waiting_filter_excludes_approved(self) -> None:
        """'waiting' filter should not include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "waiting")
        prs = client._fetch_created_prs("waiting")

        assert len(prs) == 0

    def test_needs_attention_filter_excludes_approved(self) -> None:
        """'needs_attention' filter should not include approved PRs."""
        mock_github = MagicMock()
        mock_github.get_user.return_value.login = "me"
        mock_issue, mock_pr_obj = self._make_issue("APPROVED")
        mock_github.search_issues.return_value = [mock_issue]
        mock_github.get_repo.return_value.get_pull.return_value = mock_pr_obj

        client = self._make_client(mock_github, "needs_attention")
        prs = client._fetch_created_prs("needs_attention")

        assert len(prs) == 0
```

**Step 2: Run tests to confirm they fail**

```
make test
```

Expected: `test_any_filter_includes_approved` fails — `any` is not a recognized filter so approved PRs are excluded.

**Step 3: Update github_client.py**

In `src/reviewinator/github_client.py`, change lines 198–203:

```python
# Apply filter
if filter_type == "waiting" and review_status != "waiting":
    continue
elif filter_type == "needs_attention" and review_status != "changes_requested":
    continue
elif filter_type == "any" and review_status not in ("waiting", "changes_requested", "approved"):
    continue
```

**Step 4: Run tests to confirm they pass**

```
make test
```

Expected: all pass.

**Step 5: Commit**

```bash
git add src/reviewinator/github_client.py tests/test_github_client.py
git commit -m "feat: extend 'any' filter to include approved PRs"
```

---

### Task 3: Fix stale `either` reference in existing test

**Files:**
- Modify: `tests/test_github_client.py:204` (the `test_fetch_review_requests_filters_to_configured_repos` test uses `created_pr_filter="either"`)

**Step 1: Update the two occurrences of `"either"` in test_github_client.py**

In `tests/test_github_client.py`, change both `created_pr_filter="either"` to `created_pr_filter="any"`:

- Line ~204 in `test_fetch_review_requests_filters_to_configured_repos`
- Line ~229 in `test_fetch_review_requests_searches_for_user`

**Step 2: Run all tests**

```
make test
```

Expected: all pass, no references to `"either"` remain.

**Step 3: Commit**

```bash
git add tests/test_github_client.py
git commit -m "test: update stale 'either' filter references to 'any'"
```

---

### Task 4: Update live config and documentation

**Files:**
- Modify: `~/.config/reviewinator/config.yaml`
- Modify: `config.example.yaml`
- Modify: `CLAUDE.md`

**Step 1: Update live config**

In `~/.config/reviewinator/config.yaml`, change:
```yaml
created_pr_filter: either
```
to:
```yaml
created_pr_filter: any
```

**Step 2: Update config.example.yaml**

Replace the `created_pr_filter` section comments and value:

```yaml
# Filter for which created PRs to show (optional, defaults to "any")
# Options:
#   - "any": Show PRs waiting for review, with changes requested, OR approved (default)
#   - "all": Show all open PRs you created
#   - "waiting": Only show PRs still waiting for initial review
#   - "needs_attention": Only show PRs with changes requested
created_pr_filter: any
```

**Step 3: Update CLAUDE.md**

In the Configuration section, replace the `created_pr_filter` comment block:

```yaml
created_pr_filter: any  # Options: all, waiting, needs_attention, any
```

And in the description below the code block, update:

```
The `created_pr_filter` field controls which of your created PRs to show:
- `any` (default): Show PRs waiting for review, needing changes, OR approved
- `waiting`: Show only PRs waiting for initial review
- `needs_attention`: Show only PRs with changes requested
- `all`: Show all your open PRs
```

**Step 4: Run lint and tests**

```
make lint
make test
```

Expected: all pass.

**Step 5: Commit**

```bash
git add config.example.yaml CLAUDE.md
git commit -m "docs: update created_pr_filter docs for 'any' filter"
```

Note: `~/.config/reviewinator/config.yaml` is outside the repo — no need to commit it.
