# Green Check Mark Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Change the menu bar icon from `✓` to `✅` when there are no pending PRs for clearer visual feedback.

**Architecture:** Single-line change in the `_do_update_menu()` method that sets the menu bar title. The change updates the emoji from a plain check mark to a green check mark emoji.

**Tech Stack:** Python, rumps (macOS menu bar framework), pytest

---

## Task 1: Add Test for Green Check Mark Display

**Files:**
- Test: `tests/test_app.py`

**Step 1: Write the failing test**

Add a test that verifies the menu bar shows ✅ when there are no PRs:

```python
def test_menu_shows_green_check_when_no_prs(app):
    """Test that menu bar shows green check mark when no PRs."""
    app.prs = []
    app._do_update_menu()
    assert app.title == "✅"
```

**Step 2: Run test to verify it fails**

Run: `make test`

Expected: FAIL with assertion error showing `"✓" != "✅"`

**Step 3: Implement the change**

Modify: `src/reviewinator/app.py:85`

Change from:
```python
self.title = "✓"  # Green check for no reviews
```

To:
```python
self.title = "✅"  # Green check for no reviews
```

**Step 4: Run test to verify it passes**

Run: `make test`

Expected: All tests PASS

**Step 5: Verify existing tests still pass**

Run: `make test-cov`

Expected: All tests PASS with coverage report

**Step 6: Manual testing**

Run: `make run`

Verify:
- Menu bar shows `✅` when there are no pending PRs
- Menu bar shows `🔴 {count}` when PRs are present
- Emoji renders correctly in both light and dark menu bar modes
- Transitions between states work correctly

**Step 7: Run linting**

Run: `make lint`

Expected: No linting errors

**Step 8: Commit**

```bash
git add src/reviewinator/app.py tests/test_app.py
git commit -m "feat: Change check mark to green emoji when no PRs

Updated menu bar icon from ✓ to ✅ when there are no pending PRs
to provide clearer visual feedback (green = good, red = action needed).

Co-Authored-By: Claude Sonnet 4.5 <noreply@anthropic.com>"
```

---

## Testing Checklist

Before considering this complete, verify:
- [ ] Unit test passes for green check mark display
- [ ] All existing tests still pass
- [ ] No linting errors
- [ ] Manual verification: ✅ appears when no PRs
- [ ] Manual verification: 🔴 count appears when PRs present
- [ ] Manual verification: Works in both light and dark menu bar modes
- [ ] Code committed with proper message

## Reference Skills

- **TDD:** @superpowers:test-driven-development - Use TDD workflow throughout
- **Verification:** @superpowers:verification-before-completion - Verify all tests pass before claiming completion
