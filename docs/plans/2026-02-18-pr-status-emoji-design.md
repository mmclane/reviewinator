# Design: PR Status Emoji

**Date:** 2026-02-18

## Summary

Prepend a status emoji to each PR menu item so users can see at a glance what action (if any) is needed.

## Emoji Map

| Type / Status | Emoji | Meaning |
|---|---|---|
| `review_request` | 👀 | Someone wants your review |
| `created` + `waiting` | 🕐 | No reviews yet |
| `created` + `approved` | ✅ | Ready to merge |
| `created` + `changes_requested` | 🔴 | Action needed |
| `created` + `commented` | 💬 | Has feedback |
| `created` + unknown | 🕐 | Fallback |

## Before / After

```
# Before
#142 Fix login bug (alice, 2h ago)
#91 Update deps (approved, 1h ago)

# After
👀 #142 Fix login bug (alice, 2h ago)
✅ #91 Update deps (approved, 1h ago)
```

## Implementation

**One file changed:** `src/reviewinator/github_client.py`

Add a module-level `STATUS_EMOJI` dict and update `PullRequest.format_menu_item()`:

```python
STATUS_EMOJI = {
    "review_request": "👀",
    "waiting": "🕐",
    "approved": "✅",
    "changes_requested": "🔴",
    "commented": "💬",
}
```

In `format_menu_item`:
- If `type == "review_request"`: use `STATUS_EMOJI["review_request"]`
- If `type == "created"`: use `STATUS_EMOJI.get(review_status, "🕐")`

**Tests:** Update existing `format_menu_item` tests in `tests/test_github_client.py` to assert the emoji prefix. Add tests for each status variant.

## Affected Files

1. `src/reviewinator/github_client.py`
2. `tests/test_github_client.py`
