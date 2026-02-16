# Repo Exclusion Filtering Design

**Date:** 2026-02-15

## Overview

Change reviewinator from using inclusion lists (specific repos to check) to exclusion lists (check all repos except these). This simplifies configuration and ensures all relevant PRs are visible by default.

## Current State

- Config defines two inclusion lists: `review_request_repos` and `created_pr_repos`
- GitHub client fetches all PRs via search, then filters TO repos in the lists
- Users must explicitly list every repo they want to monitor
- Easy to miss PRs from new repos or repos not in the config

## New State

- Config defines single exclusion list: `excluded_repos`
- GitHub client fetches all PRs via search, then filters OUT repos in the exclusion list
- Same exclusion list applies to both review requests and created PRs
- All repos included by default; only excluded repos are filtered out
- `created_pr_filter` gains new "either" option (default) for showing PRs that are waiting OR need attention

## Architecture

**Key principle:** Use GitHub's search to find all relevant PRs (already efficient), then apply exclusions after combining results. This minimizes API calls and leverages existing GitHub indexes.

**Data Flow:**

1. `_fetch_review_requests()` - Search GitHub for all review requests, no filtering
2. `_fetch_created_prs()` - Search GitHub for all created PRs, apply status filter only
3. `fetch_prs()` - Combine both lists, apply exclusion filter once to combined results

## Component Changes

### config.py

**Remove:**
- `review_request_repos` field from Config dataclass
- `created_pr_repos` field from Config dataclass
- Validation logic for old fields

**Add:**
- `excluded_repos: list[str]` field (defaults to empty list)
- Validation that `excluded_repos` is a list if present

**Update:**
- `created_pr_filter` validation to include "either" as valid option
- `created_pr_filter` default value to "either" (was "waiting")

### github_client.py

**Update `__init__`:**
- Accept single `excluded_repos` list instead of separate repo lists
- Store as instance variable for use in `fetch_prs()`

**Update `_fetch_review_requests()`:**
- Remove inclusion filtering logic
- Return all review requests from search (no repo filtering)

**Update `_fetch_created_prs()`:**
- Remove inclusion filtering logic
- Keep status filtering for `created_pr_filter`
- Add "either" option: include PRs with status "waiting" OR "changes_requested"

**Update `fetch_prs()`:**
- Call `_fetch_review_requests()`
- Call `_fetch_created_prs(created_pr_filter)`
- Combine both lists
- Filter out any PR where `pr.repo in excluded_repos`
- Return filtered combined list

### app.py

**Update `__init__`:**
- Pass `config.excluded_repos` to GitHubClient constructor
- No other changes needed

## Error Handling

### Config Validation
- If `github_token` missing: ConfigError "Missing required field: github_token"
- If `excluded_repos` is not a list: ConfigError "excluded_repos must be a list"
- If `created_pr_filter` invalid: ConfigError listing valid options

### Runtime Errors
- GitHub API errors handled by existing error handling in app.py (lines 184-190)
- No changes needed to runtime error handling

### Edge Cases
- Empty `excluded_repos` (or missing): all repos included ✓
- Repo in `excluded_repos` that has no PRs: harmless, just skipped ✓
- User has no PRs at all: returns empty list ✓

## Testing

### Config Tests (test_config.py)
- Loading config with `excluded_repos` field
- `excluded_repos` defaults to empty list when not specified
- `excluded_repos` must be a list (reject string, dict, etc.)
- `created_pr_filter` defaults to "either"
- `created_pr_filter` accepts all valid options: "all", "waiting", "needs_attention", "either"
- `created_pr_filter` rejects invalid options

### GitHub Client Tests (test_github_client.py)
- `fetch_prs()` excludes repos in `excluded_repos` list
- `fetch_prs()` includes all repos when `excluded_repos` is empty
- `fetch_prs()` applies exclusions to both review requests and created PRs
- `created_pr_filter="either"` includes PRs with status "waiting" or "changes_requested"
- `created_pr_filter="either"` excludes PRs with status "approved" or "commented"
- Update existing tests to use new config structure

### Integration/Manual Testing
- Run with empty `excluded_repos`, verify all repos appear
- Run with specific repos in `excluded_repos`, verify they don't appear
- Test each `created_pr_filter` option shows correct PRs

## Example Config

```yaml
github_token: ghp_xxx
excluded_repos:
  - personal/archived-project
  - company/old-monorepo
created_pr_filter: either  # default - show waiting OR needs attention
refresh_interval: 300
```

## Migration Notes

This is a breaking change. Users must update their config:
- Remove `review_request_repos` field
- Remove `created_pr_repos` field
- Add `excluded_repos` field (optional, defaults to empty list)
- `created_pr_filter` now defaults to "either"

Since there is only one user (the developer), no backward compatibility is needed.
