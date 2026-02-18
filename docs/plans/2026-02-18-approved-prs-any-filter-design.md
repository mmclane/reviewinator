# Design: Show Approved PRs / Rename `either` to `any`

**Date:** 2026-02-18

## Summary

Extend the `created_pr_filter` config option to show approved PRs alongside waiting and needs-attention PRs. Rename the `either` filter value to `any` to better reflect that it now covers three actionable states.

## Problem

The default `either` filter hides approved PRs from the menu. When a PR is approved, it still needs to be merged — it's actionable — but the user has no visibility into it from the menu bar.

## Design

### Config changes (`config.py`)

- Replace `"either"` with `"any"` in the valid filters list: `["all", "waiting", "needs_attention", "any"]`
- Update the default from `"either"` to `"any"`
- No backward compatibility for `"either"` — it becomes an invalid value

### Filter logic changes (`github_client.py`)

In `_fetch_created_prs`, update the filter branch:

```python
# Before
elif filter_type == "either" and review_status not in ("waiting", "changes_requested"):
    continue

# After
elif filter_type == "any" and review_status not in ("waiting", "changes_requested", "approved"):
    continue
```

### Live config update (`~/.config/reviewinator/config.yaml`)

Change `created_pr_filter: either` → `created_pr_filter: any`

### Documentation updates

- `CLAUDE.md`: Replace `either` with `any` in the config reference, update description
- `config.example.yaml`: Same

### Test changes (`test_config.py`, `test_github_client.py`)

- Replace all `"either"` references with `"any"`
- Add test: approved PRs are included with `any` filter
- Add test: approved PRs are excluded with `waiting` filter
- Add test: approved PRs are excluded with `needs_attention` filter
- Add test: `"either"` is now rejected as an invalid filter value

## Affected Files

1. `src/reviewinator/config.py`
2. `src/reviewinator/github_client.py`
3. `~/.config/reviewinator/config.yaml`
4. `CLAUDE.md`
5. `config.example.yaml`
6. `tests/test_config.py`
7. `tests/test_github_client.py`
