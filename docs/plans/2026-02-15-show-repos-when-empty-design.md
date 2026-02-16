# Show Repos When Empty Design

**Date:** 2026-02-15

## Overview

When there are no pending PRs to review or track, show a list of repos where the user has had recent PR activity. This provides visibility into which repos are being monitored and gives quick access to their PR pages.

## Current State

- App fetches PRs and displays them grouped by repo
- When no PRs exist, shows static "No pending items" message
- Cache stores seen PR IDs and review statuses
- No visibility into which repos are being monitored when empty

## Proposed State

- As PRs are fetched, track repo activity (repo name + last seen timestamp)
- Store repo activity in cache alongside existing data
- When no PRs exist, show repos with activity in last X days (configurable, default 14)
- Display up to 20 repos with activity info: "owner/repo (N PRs, Xd ago)"
- Show "and N more..." if more than 20 repos
- Clicking repo opens its PRs page on GitHub

## User Requirements

Based on clarifying questions:
1. Show repos from recent PR activity over the last X days
2. X should be configurable with default of 14 days
3. Clicking a repo opens its PRs page on GitHub
4. Display as flat list with activity info
5. Smart limit: show up to 20 repos, with "and N more..." if there are more

## Architecture

**Key principle:** Piggyback on existing PR fetch - no extra GitHub API calls. Use cache as the source of truth for recent repo activity.

**Approach:** Cache recent repos from PR fetching
- As PRs are fetched, track which repos they came from with timestamps
- Store this repo activity in the cache file alongside seen PRs
- When menu shows "no PRs", read from cache and display repos active within the lookback window
- Add `activity_lookback_days` config field (defaults to 14)

**Advantages:**
- No extra GitHub API calls - uses existing PR data
- Fast - data is already in cache
- Simple implementation - piggyback on existing fetch logic

**Trade-offs:**
- Only knows about repos after first run with this feature
- If cache is cleared, repo list disappears until next PR activity
- This is acceptable - "No pending items" shows once, then repos appear after first fetch

## Component Changes

### cache.py

**Add field to Cache dataclass:**
- `repo_activity: dict[str, datetime]` - Maps repo name to last seen timestamp

**Update functions:**
- `load_cache()` - Handle new `repo_activity` field, default to `{}` if missing
- `save_cache()` - Persist `repo_activity` to JSON

### config.py

**Add field to Config dataclass:**
- `activity_lookback_days: int = 14` - How many days back to show repos

**Update validation:**
- Validate `activity_lookback_days` is a positive integer
- Raise ConfigError if not: "activity_lookback_days must be a positive integer"

### app.py

**Update `_fetch_and_update()` (after PR fetch):**
- For each PR in `self.prs`, record: `self.cache.repo_activity[pr.repo] = datetime.now(timezone.utc)`
- Clean up old entries: remove repos with timestamps older than `now - timedelta(days=config.activity_lookback_days)`
- Save updated cache

**Update `_do_update_menu()` (empty state handling):**
- When `not review_requests and not created_prs`:
  - Calculate `cutoff_date = now - timedelta(days=config.activity_lookback_days)`
  - Filter repos: `active_repos = {repo: ts for repo, ts in cache.repo_activity.items() if ts > cutoff_date}`
  - Count PRs per repo from cache (based on seen_prs)
  - Sort by most recent timestamp (newest first)
  - Take first 20 repos, format as "owner/repo (N PRs, Xd ago)", add clickable menu items
  - Each item callback opens `https://github.com/{repo}/pulls`
  - If `len(active_repos) > 20`, add non-clickable item: "and {len(active_repos) - 20} more..."

### No changes needed

- **github_client.py** - Just uses existing PR data
- **notifications.py** - No notification changes

## Data Flow

### During PR Fetch (every refresh_interval)

1. `_fetch_and_update()` calls `client.fetch_prs()`
2. For each PR in results, record repo activity:
   ```python
   cache.repo_activity[pr.repo] = datetime.now(timezone.utc)
   ```
3. Clean up old entries:
   ```python
   cutoff = now - timedelta(days=config.activity_lookback_days)
   cache.repo_activity = {
       repo: ts for repo, ts in cache.repo_activity.items()
       if ts > cutoff
   }
   ```
4. Save updated cache to disk

### During Menu Update

1. `_do_update_menu()` checks if `review_requests` and `created_prs` are both empty
2. If empty:
   - Calculate `cutoff_date = now - timedelta(days=config.activity_lookback_days)`
   - Filter repos: `active_repos = {repo: ts for repo, ts in cache.repo_activity.items() if ts > cutoff_date}`
   - Count PRs per repo from cache data
   - Sort by most recent timestamp (newest first)
   - Take first 20 repos
   - Format each as "owner/repo (N PRs, Xd ago)"
   - Add clickable menu items with callback to open `https://github.com/{repo}/pulls`
   - If more than 20, add "and N more..." item

### Example Cache Data

```json
{
  "seen_prs": [...],
  "pr_statuses": {...},
  "repo_activity": {
    "mmclane/reviewinator": "2026-02-15T10:30:00Z",
    "snapptinc/fda-app-infra": "2026-02-14T15:22:00Z",
    "snapptinc/fde-datalake-infra": "2026-02-10T09:15:00Z"
  },
  "last_checked": "2026-02-15T10:30:00Z"
}
```

## Error Handling

### Config Validation
- If `activity_lookback_days` is missing: default to 14
- If `activity_lookback_days` is not a positive integer: raise ConfigError "activity_lookback_days must be a positive integer"

### Cache Loading
- If cache has no `repo_activity` field (old cache format): initialize as empty dict `{}`
- If cache has malformed timestamps: skip those entries silently

### Menu Display Edge Cases
- If cache is empty (fresh install): show "No pending items" - repos will appear after first PR fetch
- If all repo activity is older than lookback window: show "No pending items"
- If PR count calculation fails for a repo: show "owner/repo (recent activity)" without count

### Runtime Errors
- Cache save/load errors already handled by existing error handling in app.py
- No new GitHub API calls, so no new API error cases

## Testing

### Config Tests (test_config.py)
- Test `activity_lookback_days` defaults to 14
- Test `activity_lookback_days` accepts positive integers (1, 7, 30, 90)
- Test `activity_lookback_days` rejects negative values
- Test `activity_lookback_days` rejects zero
- Test `activity_lookback_days` rejects non-integer values

### Cache Tests (test_cache.py)
- Test loading cache with `repo_activity` field
- Test loading old cache without `repo_activity` field (backward compatibility)
- Test saving cache with `repo_activity`
- Test roundtrip save/load preserves repo activity data
- Test datetime serialization/deserialization works correctly

### App Tests (test_app.py)
- Test menu shows "No pending items" when cache is empty and no PRs
- Test menu shows repo list when no PRs but repo_activity exists
- Test repo list shows up to 20 repos sorted by recent activity (newest first)
- Test "and N more..." appears when more than 20 repos
- Test clicking repo item opens correct GitHub PR page URL
- Test repo activity is updated after PR fetch
- Test old repo activity is cleaned up (entries beyond lookback window removed)
- Test excluded repos don't appear in empty state list
- Test activity info formatting ("N PRs, Xd ago")

### Integration/Manual Testing
- Run app with no PRs, verify empty state shows repos from cache
- Add a repo to excluded_repos, verify it doesn't appear in empty state list
- Change activity_lookback_days in config, verify repo list updates accordingly
- Clear cache, verify "No pending items" shows initially, then repos appear after first fetch
- Verify clicking repos opens correct GitHub PR page

## Example UI

**When no PRs (with repo activity in cache):**
```
Recent Activity:
  mmclane/reviewinator (2 PRs, 1d ago)
  snapptinc/fda-app-infra (5 PRs, 3d ago)
  snapptinc/fde-datalake-infra (1 PR, 7d ago)
  ... (15 more entries) ...
  and 5 more...
───────
Check Now
───────
Quit
```

**When no PRs (empty cache - fresh install):**
```
No pending items
───────
Check Now
───────
Quit
```

## Migration Notes

- Backward compatible - old cache files without `repo_activity` will work (empty state shows "No pending items" until first fetch)
- New config field `activity_lookback_days` is optional with sensible default
- No breaking changes to existing functionality
