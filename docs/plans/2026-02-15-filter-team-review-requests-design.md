# Filter Team Review Requests Design

**Date:** 2026-02-15

## Overview

Filter out PRs where you're requested as a reviewer exclusively via specific teams (like "all-engineers" or "everyone"), while still showing PRs where you're individually requested or requested via teams you care about.

## Problem

GitHub's `review-requested:{username}` search returns PRs where you're requested as a reviewer either:
1. Individually (directly assigned)
2. Via team membership (assigned to a team you're on)

Currently, reviewinator shows all these PRs without distinction. Large teams like "all-engineers" or "everyone" create noise - you see PRs you're not actually expected to review.

## User Requirements

Based on clarifying questions:
1. Filter out specific teams (specified in config via full team identifiers: "org/team-slug")
2. Show PR if requested individually OR via any non-filtered team
3. Hide PR ONLY if requested exclusively via filtered teams
4. Fail open - show PR if can't determine team info

## Architecture

**Current state:**
- GitHub search `review-requested:{username}` returns all PRs where you're requested
- No distinction between individual vs team review requests
- All matching PRs are displayed

**New state:**
- Add `excluded_review_teams` config field (list of "org/team-slug" strings)
- During fetch, get full PR object to check `requested_reviewers` and `requested_teams`
- Apply filtering logic:
  - Keep if you're individually requested
  - Keep if requested via any non-excluded team
  - Skip if requested ONLY via excluded teams
- Fail open: show PR if team info unavailable or error occurs

**Key principle:** Filter at fetch time so excluded PRs never enter the system (no notifications, no display, no cache pollution).

## Component Changes

### config.py

**Add field to Config dataclass:**
- `excluded_review_teams: list[str]` - List of "org/team-slug" identifiers to filter out

**Validation:**
- Defaults to empty list if not specified
- Must be a list type
- Each entry must match pattern: `^[a-zA-Z0-9-]+/[a-zA-Z0-9-]+$`
- Reject malformed entries with clear error message

**Example:**
```python
@dataclass
class Config:
    github_token: str
    excluded_repos: list[str]
    excluded_review_teams: list[str]
    created_pr_filter: str
    activity_lookback_days: int
    refresh_interval: int = 300
```

### github_client.py

**Update `_fetch_review_requests()` method:**

Current flow:
1. Search GitHub for review requests
2. Filter by excluded repos
3. Create PullRequest objects

New flow:
1. Search GitHub for review requests
2. Filter by excluded repos
3. **Get full PR object to check reviewers**
4. **Apply team filtering logic**
5. Create PullRequest objects only for PRs that pass filter

**Add helper method:**
```python
def _should_show_review_request(self, pr, username: str) -> bool:
    """Determine if a PR should be shown based on team filtering.

    Returns True if:
    - User is individually requested, OR
    - User is requested via any non-excluded team, OR
    - Unable to determine (fail open)

    Returns False only if:
    - Requested exclusively via excluded teams
    """
```

**Team data extraction:**
- `pr.requested_reviewers` → list of User objects → extract logins
- `pr.requested_teams` → list of Team objects → extract "org/slug" identifiers
- Handle missing/None/malformed data gracefully

### No changes needed

- **app.py** - Uses filtered results from github_client
- **cache.py** - Stores fewer PRs (filtered), which is good
- **notifications.py** - Only notifies for visible PRs

## Data Flow

### During Review Request Fetch

1. **GitHub search** returns issues where `review-requested:{username}`

2. **For each issue:**
   - Check if `repo in excluded_repos` → skip if yes
   - Get full PR object: `repo.get_pull(issue.number)`
   - Extract reviewer information:
     ```python
     individual_reviewers = [user.login for user in pr.requested_reviewers or []]
     team_reviewers = [
         f"{team.organization.login}/{team.slug}"
         for team in pr.requested_teams or []
         if team.organization and team.slug
     ]
     ```
   - Apply filter logic:
     ```python
     # Show if individually requested
     if username in individual_reviewers:
         show_pr = True
     # Show if requested via any non-excluded team
     elif any(team not in excluded_teams for team in team_reviewers):
         show_pr = True
     # Hide if only requested via excluded teams
     else:
         show_pr = False
     ```
   - If `show_pr`, create PullRequest object and add to results

3. **Return** filtered list of PullRequest objects

### Edge Cases

- **No reviewers:** `requested_reviewers=[]` and `requested_teams=[]` → show (fail open)
- **API error:** Can't get PR details → show (fail open)
- **Malformed data:** Missing org/slug on team → skip that team, continue
- **Empty filter:** `excluded_teams=[]` → show all (current behavior)
- **Mixed requests:** Individual + excluded team → show (individual takes precedence)

### Example Scenarios

**Scenario 1: Individual request overrides team filter**
- PR reviewers: `requested_reviewers=[alice, bob]`, `requested_teams=[org/all-engineers]`
- Your username: `alice`
- Excluded teams: `[org/all-engineers]`
- **Result: Show** (you're individually requested)

**Scenario 2: Non-excluded team**
- PR reviewers: `requested_reviewers=[]`, `requested_teams=[org/platform, org/all-engineers]`
- Your username: `alice`
- Excluded teams: `[org/all-engineers]`
- **Result: Show** (org/platform is not excluded)

**Scenario 3: Only excluded teams**
- PR reviewers: `requested_reviewers=[]`, `requested_teams=[org/all-engineers]`
- Your username: `alice`
- Excluded teams: `[org/all-engineers]`
- **Result: Hide** (only requested via excluded team)

## Error Handling

### Config Validation

- Missing `excluded_review_teams` → default to `[]`
- Not a list → ConfigError: "excluded_review_teams must be a list"
- Malformed entry → ConfigError: "excluded_review_teams entries must be in format 'org/team' (got: {entry})"
- Validation pattern: `^[a-zA-Z0-9-]+/[a-zA-Z0-9-]+$`

### Runtime Errors

- **API error getting PR:** Log warning, show PR (fail open)
- **Missing `requested_reviewers`/`requested_teams`:** Treat as empty list
- **Team missing `organization` or `slug`:** Skip that team, continue
- **Any exception during filtering:** Log error, show PR (fail open)

### Logging

Add logging for transparency:
- Filtered PR: "Filtered PR #{number} in {repo} (only requested via excluded teams: {teams})"
- Filter error: "Error checking teams for PR #{number}, showing anyway: {error}"

### Backward Compatibility

- Old configs without `excluded_review_teams` → works (defaults to `[]`)
- No breaking changes to existing functionality
- Purely additive feature

## Testing

### Config Tests (test_config.py)

- Test `excluded_review_teams` defaults to empty list
- Test loading config with `excluded_review_teams` list
- Test validation accepts valid "org/team" format
- Test validation rejects non-list values
- Test validation rejects malformed entries:
  - No slash: "orgteam"
  - Empty org: "/team"
  - Empty team: "org/"
  - Extra slashes: "org/team/extra"
  - Invalid characters: "org!/team@"

### GitHub Client Tests (test_github_client.py)

**Filtering logic:**
- Test PR with individual request → shown (even with excluded team)
- Test PR with only excluded team → hidden
- Test PR with only non-excluded team → shown
- Test PR with mix of excluded and non-excluded teams → shown
- Test PR with multiple excluded teams → hidden
- Test PR with no reviewers → shown (fail open)

**Edge cases:**
- Test empty `excluded_review_teams` config → all PRs shown
- Test API error getting PR details → shown (fail open)
- Test `requested_reviewers` is None → handled gracefully
- Test `requested_teams` is None → handled gracefully
- Test team missing `organization` → handled gracefully
- Test team missing `slug` → handled gracefully

**Mock setup:**
```python
# Mock PR with individual and team requests
mock_pr = Mock()
mock_pr.requested_reviewers = [Mock(login="alice"), Mock(login="bob")]
mock_team = Mock()
mock_team.organization = Mock(login="snapptinc")
mock_team.slug = "all-engineers"
mock_pr.requested_teams = [mock_team]
```

### Integration/Manual Testing

- Add team to `excluded_review_teams`, verify PRs from that team are hidden
- Verify individually requested PRs always shown
- Verify PRs from non-excluded teams are shown
- Check logs for "Filtered PR" messages
- Test with empty excluded list → all shown
- Test with team you're not on → no effect

## Example Configuration

```yaml
github_token: ghp_xxx
excluded_repos:
  - owner/archived-repo
excluded_review_teams:
  - snapptinc/all-engineers
  - snapptinc/everyone
  - myorg/pdt-snax
created_pr_filter: either
activity_lookback_days: 14
refresh_interval: 300
```

## Implementation Notes

1. **API call overhead:** Getting full PR object adds one API call per review request. This is acceptable since:
   - We already do this for created PRs (to check review status)
   - Review request count is typically small (< 20 PRs)
   - GitHub API rate limits are generous (5000/hour)

2. **Team identifier format:** Using "org/slug" matches the pattern of "owner/repo" and is unambiguous across organizations.

3. **Fail open philosophy:** When in doubt, show the PR. Better to see extra PRs than miss important review requests.

4. **Performance:** Filtering happens during fetch (once per refresh interval), not on every menu update. Minimal performance impact.
