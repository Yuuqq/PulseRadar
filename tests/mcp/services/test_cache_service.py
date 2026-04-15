"""Unit tests for mcp_server.services.cache_service.

Covers make_cache_key (pure function) and CacheService (set/get/delete/clear,
expiry semantics, cleanup_expired, get_stats).
"""

from __future__ import annotations

import time

from mcp_server.services.cache_service import CacheService, make_cache_key


class TestMakeCacheKey:
    def test_no_params_returns_namespace(self):
        assert make_cache_key("latest_news") == "latest_news"

    def test_params_produce_prefixed_hash(self):
        key = make_cache_key("latest_news", platforms=["zhihu"], limit=50)
        assert key.startswith("latest_news:")
        suffix = key.split(":", 1)[1]
        assert len(suffix) == 12  # sha256 hex truncated to 12 chars

    def test_same_params_produce_stable_key(self):
        k1 = make_cache_key("search", query="AI", mode="keyword")
        k2 = make_cache_key("search", query="AI", mode="keyword")
        assert k1 == k2

    def test_different_param_order_produces_same_key(self):
        k1 = make_cache_key("search", mode="keyword", query="AI")
        k2 = make_cache_key("search", query="AI", mode="keyword")
        assert k1 == k2

    def test_list_order_is_normalized(self):
        k1 = make_cache_key("n", platforms=["a", "b"])
        k2 = make_cache_key("n", platforms=["b", "a"])
        assert k1 == k2

    def test_none_values_are_ignored(self):
        k1 = make_cache_key("n", x="y")
        k2 = make_cache_key("n", x="y", z=None)
        assert k1 == k2


class TestCacheService:
    def test_set_and_get(self):
        cache = CacheService()
        cache.set("k1", {"v": 1})
        assert cache.get("k1") == {"v": 1}

    def test_miss_returns_none(self):
        cache = CacheService()
        assert cache.get("nonexistent") is None

    def test_expired_entry_returns_none_and_is_removed(self):
        cache = CacheService()
        cache.set("k1", "v")
        # Simulate expiry by backdating the timestamp.
        cache._timestamps["k1"] = time.time() - 1000
        assert cache.get("k1", ttl=900) is None
        # Auto-removed
        assert "k1" not in cache._cache

    def test_delete_existing_returns_true(self):
        cache = CacheService()
        cache.set("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None

    def test_delete_missing_returns_false(self):
        cache = CacheService()
        assert cache.delete("k") is False

    def test_clear_removes_all(self):
        cache = CacheService()
        cache.set("k1", 1)
        cache.set("k2", 2)
        cache.clear()
        assert cache.get("k1") is None
        assert cache.get("k2") is None

    def test_cleanup_expired_removes_stale_entries(self):
        cache = CacheService()
        cache.set("fresh", "ok")
        cache.set("stale", "old")
        cache._timestamps["stale"] = time.time() - 2000
        removed = cache.cleanup_expired(ttl=900)
        assert removed == 1
        assert cache.get("fresh") == "ok"
        assert "stale" not in cache._cache

    def test_get_stats_shape(self):
        cache = CacheService()
        cache.set("k", "v")
        stats = cache.get_stats()
        assert stats["total_entries"] == 1
        assert stats["oldest_entry_age"] >= 0
        assert stats["newest_entry_age"] >= 0
