# Green Check Mark for No Pending PRs

**Date:** 2026-02-13
**Status:** Approved

## Overview

Currently, when there are no pending PRs, the menu bar shows a simple check mark `✓`. We'll change this to a green check mark emoji `✅` to provide clearer visual feedback that everything is good (no action needed).

The visual states will be:
- **No PRs:** `✅` (green check - all clear)
- **Has PRs:** `🔴 {count}` (red dot with count - action needed)

This creates a clear color-coded system: green = good, red = needs attention.

## Implementation

This is a single-line change in `src/reviewinator/app.py`:

**Current code (line 85):**
```python
self.title = "✓"  # Green check for no reviews
```

**New code:**
```python
self.title = "✅"  # Green check for no reviews
```

The change happens in the `_do_update_menu()` method, which rebuilds the menu and updates the title based on the current PR count. The emoji will render consistently across macOS versions since it's a standard Unicode emoji.

## Testing

To verify this change works correctly:

1. **Manual testing:**
   - Run the app with `make run`
   - Verify the menu bar shows `✅` when there are no pending PRs
   - Verify it still shows `🔴 {count}` when PRs are present
   - Check that the emoji renders correctly in both light and dark menu bar modes

2. **Unit testing:**
   - The existing tests in the codebase should continue to pass
   - No new tests needed since this is just a visual change to a string constant

3. **Edge cases:**
   - Confirm the check mark appears correctly on app startup (before first poll completes)
   - Verify transitions between states (0 PRs → has PRs → 0 PRs) update correctly

## Decision

**Selected approach:** Simple emoji replacement (Option A)

**Rationale:**
- Minimal change with clear visual impact
- No dependencies or complex code needed
- The green checkmark is self-explanatory
- Menu already provides "No pending reviews" context when clicked
- Rumps does not support tooltips, so more complex approaches would require custom PyObjC code
