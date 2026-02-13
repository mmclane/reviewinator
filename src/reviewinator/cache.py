"""Cache for tracking seen PRs."""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class Cache:
    """Stores state about PRs we've already seen."""

    seen_prs: set[int] = field(default_factory=set)
    pr_statuses: dict[int, str] = field(default_factory=dict)
    last_checked: datetime | None = None


def get_cache_path() -> Path:
    """Return the default cache file path."""
    return Path.home() / ".config" / "reviewinator" / "cache.json"


def load_cache(cache_path: Path) -> Cache:
    """Load cache from file.

    Args:
        cache_path: Path to the cache.json file.

    Returns:
        Cache object. Returns empty cache if file doesn't exist or is corrupted.
    """
    if not cache_path.exists():
        return Cache()

    try:
        with open(cache_path) as f:
            data = json.load(f)

        last_checked = None
        if data.get("last_checked"):
            last_checked = datetime.fromisoformat(data["last_checked"])

        return Cache(
            seen_prs=set(data.get("seen_prs", [])),
            pr_statuses=data.get("pr_statuses", {}),
            last_checked=last_checked,
        )
    except (json.JSONDecodeError, KeyError, ValueError):
        return Cache()


def save_cache(cache: Cache, cache_path: Path) -> None:
    """Save cache to file.

    Args:
        cache: Cache object to save.
        cache_path: Path to save to.
    """
    cache_path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "seen_prs": list(cache.seen_prs),
        "pr_statuses": cache.pr_statuses,
        "last_checked": cache.last_checked.isoformat() if cache.last_checked else None,
    }

    with open(cache_path, "w") as f:
        json.dump(data, f, indent=2)
