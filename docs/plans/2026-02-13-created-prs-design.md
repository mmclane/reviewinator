# Created PRs Tracking Design

**Date:** 2026-02-13
**Status:** Approved

## Overview

Add functionality to track and display PRs that the user created (not just PRs where they're requested as reviewer). The feature will show review status for created PRs and send notifications when they're approved or changes are requested.

## Architecture Overview

We'll refactor the `PullRequest` dataclass to include a `type` field that distinguishes between "review_request" and "created" PRs. For created PRs, we'll add a `review_status` field that tracks the state (e.g., "waiting", "approved", "changes_requested").

The `GitHubClient` will have a single `fetch_prs()` method that:
1. Searches for PRs where user is requested as reviewer (filtered by `review_request_repos`)
2. Searches for PRs created by user (filtered by `created_pr_repos` with configurable state filter)
3. Returns a unified list of PRs with their types

The app will maintain a single `self.prs` list but render it in two sections based on PR type. The menu bar icon will show separate counts: `🔴 {review_count} | 📤 {created_count}`.

Configuration will be extended with:
- `created_pr_repos`: list of repos to track created PRs (optional, defaults to empty)
- `created_pr_filter`: which states to show ("all", "waiting", "needs_attention")

## Data Model & Components

### Enhanced PullRequest dataclass

```python
@dataclass
class PullRequest:
    id: int
    number: int
    title: str
    author: str
    repo: str
    url: str
    created_at: datetime
    type: str  # NEW: "review_request" or "created"
    review_status: str | None  # NEW: "waiting", "approved", "changes_requested", "commented"
```

### Config Changes

```yaml
github_token: ghp_...
review_request_repos:  # RENAMED from "repos"
  - owner/repo1
created_pr_repos:  # NEW
  - owner/repo2
created_pr_filter: "waiting"  # NEW: "all", "waiting", or "needs_attention"
refresh_interval: 300
```

**Backward compatibility:** Config files without `review_request_repos` will use `repos` (deprecated but supported). If `created_pr_repos` is missing, default to empty list (feature disabled).

### GitHubClient Refactor

- Rename `fetch_review_requests()` to `fetch_prs()`
- Add `_fetch_review_requests()` private method - returns list of PRs with type="review_request"
- Add `_fetch_created_prs()` private method - returns list of PRs with type="created" and review_status
- Add `_get_review_status(pr)` helper - queries GitHub API for review state and returns status string
- `fetch_prs()` combines both lists and returns unified result

### App Changes

- Single `self.prs` list (already exists, just contains both types now)
- Update `_do_update_menu()` to split PRs by type and render two sections
- Update title logic to show dual counts: `🔴 {review_count} | 📤 {created_count}`
- Update notification logic to handle created PR status changes

## Menu Rendering & Display

### Menu Bar Icon States

- No PRs at all: `✅`
- Only review requests: `🔴 {count}`
- Only created PRs: `📤 {count}`
- Both types: `🔴 {review_count} | 📤 {created_count}`

### Menu Structure

```
┌─────────────────────────────────┐
│ 🔴 2 | 📤 1                      │ <- Menu bar icon
└─────────────────────────────────┘
  ├─ Reviews for You:
  │   ├─ owner/repo1:
  │   │   └─ #123 Fix bug (alice, 2h ago)
  │   └─ owner/repo2:
  │       └─ #456 Add feature (bob, 1d ago)
  │
  ├─ Your PRs:
  │   └─ owner/repo2:
  │       └─ #789 New feature (waiting, 3h ago)
  │
  ├─ ─────────────
  ├─ Check Now
  ├─ ─────────────
  └─ Quit
```

### PR Formatting

- Review requests: `#{number} {title} ({author}, {age})`
- Created PRs: `#{number} {title} ({status}, {age})`

### Edge Cases

- If `created_pr_repos` is empty/not configured: don't show "Your PRs" section, don't show `📤` in icon
- If one list is empty but the other has items: only show the non-empty section

## Notification Strategy

### What Triggers Notifications

1. **New review requests** (existing behavior, unchanged):
   - When a PR appears in review requests that wasn't there before
   - Notification: "New review request: #{number} {title}"

2. **Created PR status changes** (new):
   - Status changes from "waiting" → "approved"
   - Status changes from "waiting" → "changes_requested"
   - NOT triggered by: comments alone, or transitions between approved/changes_requested

### Tracking State Changes

- Cache will store both PR IDs (existing) and a new `pr_statuses: dict[int, str]` map
- On each poll, compare current status to cached status
- If status changed and meets notification criteria, send notification

### Notification Format

- New review request: "New review request: #{number} {title}" (existing)
- Created PR approved: "PR #123 approved"
- Created PR needs changes: "PR #123 needs changes"

### Cache Structure Update

```python
@dataclass
class Cache:
    seen_prs: set[int]  # existing
    pr_statuses: dict[int, str]  # NEW: pr_id -> last_known_status
    last_checked: datetime | None
```

## Testing Strategy

### New Tests to Add

1. **PullRequest model tests:**
   - Test PR with type="review_request" and review_status=None
   - Test PR with type="created" and various review_status values
   - Test format_menu_item() for both types

2. **GitHubClient tests:**
   - Test `_fetch_review_requests()` returns PRs with type="review_request"
   - Test `_fetch_created_prs()` returns PRs with type="created" and correct statuses
   - Test `_get_review_status()` maps GitHub review states correctly
   - Test `fetch_prs()` combines both lists and filters by configured repos
   - Test filtering by `created_pr_filter` ("all", "waiting", "needs_attention")

3. **App tests:**
   - Test menu rendering with only review requests (existing, should still pass)
   - Test menu rendering with only created PRs
   - Test menu rendering with both types
   - Test title shows `🔴 {count}` for only reviews
   - Test title shows `📤 {count}` for only created PRs
   - Test title shows `🔴 {x} | 📤 {y}` for both
   - Test title shows `✅` when both lists empty

4. **Notification tests:**
   - Test notification sent when created PR status changes to "approved"
   - Test notification sent when created PR status changes to "changes_requested"
   - Test no notification for comment-only status
   - Test cache stores and retrieves pr_statuses

5. **Config tests:**
   - Test loading config with new `created_pr_repos` field
   - Test loading config with `created_pr_filter` field
   - Test backward compatibility (config without new fields still works)

## Implementation Notes

### GitHub API Queries

**Review requests search:**
```
is:pr is:open review-requested:{username}
```

**Created PRs search:**
```
is:pr is:open author:{username}
```

**Review status determination:**
Use GitHub's Reviews API to check PR review state:
- No reviews → "waiting"
- Latest review state is "APPROVED" → "approved"
- Latest review state is "CHANGES_REQUESTED" → "changes_requested"
- Latest review state is "COMMENTED" → "commented"

### Config Validation

- `created_pr_filter` must be one of: "all", "waiting", "needs_attention"
- `created_pr_repos` is optional, defaults to `[]`
- `review_request_repos` or deprecated `repos` must be provided

### Migration Path

1. Phase 1: Refactor PullRequest model and GitHubClient (keep existing behavior working)
2. Phase 2: Add config support for created_pr_repos
3. Phase 3: Add menu rendering for both sections
4. Phase 4: Add notifications for status changes

Can be implemented incrementally with tests passing at each phase.

## Decision

**Selected approach:** Unified PR Model (Approach 2)

**Rationale:**
- Cleaner data model with single source of truth
- Less code duplication between review requests and created PRs
- Easier to extend with more PR types in the future
- Single fetch method simplifies app logic
- Worth the refactoring effort for long-term maintainability
