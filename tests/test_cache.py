"""Tests for cache module."""

import json
from datetime import datetime, timezone
from pathlib import Path

from reviewinator.cache import Cache, load_cache, save_cache


class TestCache:
    """Tests for Cache dataclass."""

    def test_cache_defaults(self) -> None:
        """Should have empty defaults."""
        cache = Cache()
        assert cache.seen_prs == set()
        assert cache.last_checked is None

    def test_cache_with_values(self) -> None:
        """Should store provided values."""
        now = datetime.now(timezone.utc)
        cache = Cache(seen_prs={1, 2, 3}, last_checked=now)
        assert cache.seen_prs == {1, 2, 3}
        assert cache.last_checked == now


class TestLoadCache:
    """Tests for load_cache function."""

    def test_load_existing_cache(self, tmp_path: Path) -> None:
        """Should load cache from existing file."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text(
            json.dumps({"last_checked": "2026-02-13T10:30:00+00:00", "seen_prs": [142, 138, 89]})
        )

        cache = load_cache(cache_file)

        assert cache.seen_prs == {142, 138, 89}
        assert cache.last_checked == datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)

    def test_load_nonexistent_cache_returns_empty(self, tmp_path: Path) -> None:
        """Should return empty cache when file doesn't exist."""
        cache_file = tmp_path / "nonexistent.json"

        cache = load_cache(cache_file)

        assert cache.seen_prs == set()
        assert cache.last_checked is None

    def test_load_corrupted_cache_returns_empty(self, tmp_path: Path) -> None:
        """Should return empty cache when file is corrupted."""
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("not valid json {{{")

        cache = load_cache(cache_file)

        assert cache.seen_prs == set()
        assert cache.last_checked is None


class TestSaveCache:
    """Tests for save_cache function."""

    def test_save_cache(self, tmp_path: Path) -> None:
        """Should save cache to file."""
        cache_file = tmp_path / "cache.json"
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        cache = Cache(seen_prs={1, 2, 3}, last_checked=now)

        save_cache(cache, cache_file)

        data = json.loads(cache_file.read_text())
        assert set(data["seen_prs"]) == {1, 2, 3}
        assert data["last_checked"] == "2026-02-13T10:30:00+00:00"

    def test_save_cache_creates_parent_dirs(self, tmp_path: Path) -> None:
        """Should create parent directories if they don't exist."""
        cache_file = tmp_path / "subdir" / "cache.json"
        cache = Cache(seen_prs={1}, last_checked=None)

        save_cache(cache, cache_file)

        assert cache_file.exists()

    def test_save_and_load_roundtrip(self, tmp_path: Path) -> None:
        """Should preserve data through save/load cycle."""
        cache_file = tmp_path / "cache.json"
        now = datetime(2026, 2, 13, 10, 30, 0, tzinfo=timezone.utc)
        original = Cache(seen_prs={10, 20, 30}, last_checked=now)

        save_cache(original, cache_file)
        loaded = load_cache(cache_file)

        assert loaded.seen_prs == original.seen_prs
        assert loaded.last_checked == original.last_checked


class TestCacheHelpers:
    """Tests for cache helper functions."""

    def test_get_cache_path(self) -> None:
        """Should return ~/.config/reviewinator/cache.json."""
        from reviewinator.cache import get_cache_path

        cache_path = get_cache_path()
        assert cache_path == Path.home() / ".config" / "reviewinator" / "cache.json"
