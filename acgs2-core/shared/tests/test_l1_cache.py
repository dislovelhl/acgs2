"""
ACGS-2 L1 In-Process Cache Module Tests
Constitutional Hash: cdd01ef066bc6cf2

Tests for shared/l1_cache.py with focus on thread safety and TTL expiration.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import MagicMock

import pytest

from shared.l1_cache import (
    CONSTITUTIONAL_HASH,
    L1Cache,
    L1CacheConfig,
    L1CacheStats,
    get_l1_cache,
    reset_l1_cache,
)

# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def cache():
    """Create a fresh L1Cache instance for each test."""
    return L1Cache(maxsize=100, ttl=60)


@pytest.fixture
def short_ttl_cache():
    """Create a cache with short TTL for expiration testing."""
    return L1Cache(maxsize=100, ttl=1)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton before and after each test."""
    reset_l1_cache()
    yield
    reset_l1_cache()


# ============================================================================
# L1CacheConfig Tests
# ============================================================================


class TestL1CacheConfig:
    """Test L1CacheConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = L1CacheConfig()
        assert config.maxsize == 1024
        assert config.ttl == 600
        assert config.serialize is False

    def test_custom_values(self):
        """Test custom configuration values."""
        config = L1CacheConfig(maxsize=500, ttl=300, serialize=True)
        assert config.maxsize == 500
        assert config.ttl == 300
        assert config.serialize is True


# ============================================================================
# L1CacheStats Tests
# ============================================================================


class TestL1CacheStats:
    """Test L1CacheStats dataclass."""

    def test_default_values(self):
        """Test default statistics values."""
        stats = L1CacheStats()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
        assert stats.deletes == 0
        assert stats.evictions == 0

    def test_hit_ratio_zero_accesses(self):
        """Test hit ratio with no accesses."""
        stats = L1CacheStats()
        assert stats.hit_ratio == 0.0

    def test_hit_ratio_all_hits(self):
        """Test hit ratio with all hits."""
        stats = L1CacheStats(hits=10, misses=0)
        assert stats.hit_ratio == 1.0

    def test_hit_ratio_mixed(self):
        """Test hit ratio with mixed hits and misses."""
        stats = L1CacheStats(hits=7, misses=3)
        assert stats.hit_ratio == 0.7


# ============================================================================
# L1Cache Basic Operations Tests
# ============================================================================


class TestL1CacheBasicOperations:
    """Test basic L1Cache operations."""

    def test_cache_initialization(self, cache):
        """Test cache is initialized correctly."""
        assert cache.maxsize == 100
        assert cache.ttl == 60
        assert cache.size == 0

    def test_set_and_get(self, cache):
        """Test basic set and get operations."""
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_nonexistent_key(self, cache):
        """Test getting a key that doesn't exist."""
        assert cache.get("nonexistent") is None

    def test_get_with_default(self, cache):
        """Test getting with default value."""
        default_value = "default"
        assert cache.get("nonexistent", default_value) == default_value

    def test_delete_existing_key(self, cache):
        """Test deleting an existing key."""
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_nonexistent_key(self, cache):
        """Test deleting a key that doesn't exist."""
        assert cache.delete("nonexistent") is False

    def test_exists(self, cache):
        """Test exists method."""
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        assert cache.exists("nonexistent") is False

    def test_contains_operator(self, cache):
        """Test 'in' operator support."""
        cache.set("key1", "value1")
        assert "key1" in cache
        assert "nonexistent" not in cache

    def test_len_operator(self, cache):
        """Test len() function support."""
        assert len(cache) == 0
        cache.set("key1", "value1")
        assert len(cache) == 1
        cache.set("key2", "value2")
        assert len(cache) == 2

    def test_clear(self, cache):
        """Test clear method."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size == 2
        cache.clear()
        assert cache.size == 0
        assert cache.get("key1") is None

    def test_repr(self, cache):
        """Test string representation."""
        cache.set("key1", "value1")
        repr_str = repr(cache)
        assert "L1Cache" in repr_str
        assert "maxsize=100" in repr_str
        assert "ttl=60" in repr_str


# ============================================================================
# L1Cache Batch Operations Tests
# ============================================================================


class TestL1CacheBatchOperations:
    """Test batch operations."""

    def test_get_many(self, cache):
        """Test getting multiple values."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")

        result = cache.get_many(["key1", "key2", "key4"])
        assert result == {"key1": "value1", "key2": "value2"}
        assert "key4" not in result

    def test_set_many(self, cache):
        """Test setting multiple values."""
        items = {"key1": "value1", "key2": "value2", "key3": "value3"}
        cache.set_many(items)

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.size == 3


# ============================================================================
# L1Cache Serialization Tests
# ============================================================================


class TestL1CacheSerialization:
    """Test serialization functionality."""

    def test_serialize_dict(self):
        """Test serialization of dictionary values."""
        cache = L1Cache(maxsize=100, ttl=60, serialize=True)
        data = {"name": "Alice", "age": 30}
        cache.set("user", data)
        assert cache.get("user") == data

    def test_serialize_list(self):
        """Test serialization of list values."""
        cache = L1Cache(maxsize=100, ttl=60, serialize=True)
        data = [1, 2, 3, 4, 5]
        cache.set("numbers", data)
        assert cache.get("numbers") == data

    def test_serialize_nested(self):
        """Test serialization of nested structures."""
        cache = L1Cache(maxsize=100, ttl=60, serialize=True)
        data = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        cache.set("nested", data)
        assert cache.get("nested") == data


# ============================================================================
# L1Cache TTL Expiration Tests
# ============================================================================


class TestL1CacheTTLExpiration:
    """Test TTL expiration behavior."""

    def test_item_expires_after_ttl(self, short_ttl_cache):
        """Test that items expire after TTL."""
        short_ttl_cache.set("key1", "value1")
        assert short_ttl_cache.get("key1") == "value1"

        # Wait for TTL to expire
        time.sleep(1.5)

        # Item should be expired
        assert short_ttl_cache.get("key1") is None

    def test_item_accessible_before_ttl(self, short_ttl_cache):
        """Test that items are accessible before TTL expires."""
        short_ttl_cache.set("key1", "value1")

        # Check immediately
        assert short_ttl_cache.get("key1") == "value1"

        # Check after partial TTL
        time.sleep(0.5)
        assert short_ttl_cache.get("key1") == "value1"

    def test_exists_returns_false_after_expiry(self, short_ttl_cache):
        """Test that exists returns False after TTL expiry."""
        short_ttl_cache.set("key1", "value1")
        assert short_ttl_cache.exists("key1") is True

        time.sleep(1.5)
        assert short_ttl_cache.exists("key1") is False

    def test_size_decreases_after_expiry(self, short_ttl_cache):
        """Test that size reflects expiration."""
        short_ttl_cache.set("key1", "value1")
        short_ttl_cache.set("key2", "value2")
        assert short_ttl_cache.size == 2

        time.sleep(1.5)

        # Accessing the cache triggers cleanup
        short_ttl_cache.get("nonexistent")
        assert short_ttl_cache.size == 0

    def test_multiple_items_different_times(self, short_ttl_cache):
        """Test items added at different times expire at different times."""
        short_ttl_cache.set("key1", "value1")
        time.sleep(0.6)
        short_ttl_cache.set("key2", "value2")

        # Wait until first key expires but second doesn't
        time.sleep(0.6)

        # First key should be expired, second should still be valid
        assert short_ttl_cache.get("key1") is None
        assert short_ttl_cache.get("key2") == "value2"


# ============================================================================
# L1Cache Thread Safety Tests
# ============================================================================


class TestL1CacheThreadSafety:
    """Test thread safety of cache operations."""

    def test_concurrent_sets(self, cache):
        """Test concurrent set operations don't cause data corruption."""
        num_threads = 10
        items_per_thread = 100

        def set_items(thread_id):
            for i in range(items_per_thread):
                key = f"thread_{thread_id}_key_{i}"
                cache.set(key, f"value_{thread_id}_{i}")

        threads = []
        for i in range(num_threads):
            t = threading.Thread(target=set_items, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify some items are correctly stored
        assert cache.size > 0
        # Check a sample of keys
        for i in range(num_threads):
            sample_key = f"thread_{i}_key_0"
            if cache.exists(sample_key):
                assert cache.get(sample_key) == f"value_{i}_0"

    def test_concurrent_gets_and_sets(self, cache):
        """Test concurrent get and set operations."""
        cache.set("shared_key", "initial_value")
        results = []
        errors = []

        def reader():
            for _ in range(100):
                try:
                    value = cache.get("shared_key")
                    if value is not None:
                        results.append(value)
                except Exception as e:
                    errors.append(e)

        def writer():
            for i in range(100):
                try:
                    cache.set("shared_key", f"value_{i}")
                except Exception as e:
                    errors.append(e)

        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=reader))
            threads.append(threading.Thread(target=writer))

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"
        assert len(results) > 0

    def test_concurrent_deletes(self, cache):
        """Test concurrent delete operations."""
        # Pre-populate cache
        for i in range(100):
            cache.set(f"key_{i}", f"value_{i}")

        errors = []

        def delete_items(start):
            for i in range(start, 100, 4):
                try:
                    cache.delete(f"key_{i}")
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=delete_items, args=(i,)) for i in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"

    def test_thread_pool_executor(self, cache):
        """Test with ThreadPoolExecutor for realistic concurrent access."""

        def operation(i):
            key = f"key_{i % 10}"
            if i % 3 == 0:
                cache.set(key, f"value_{i}")
            elif i % 3 == 1:
                cache.get(key)
            else:
                cache.exists(key)
            return i

        with ThreadPoolExecutor(max_workers=20) as executor:
            results = list(executor.map(operation, range(1000)))

        assert len(results) == 1000

    def test_no_race_conditions_in_stats(self, cache):
        """Test that statistics tracking is thread-safe."""

        def access_cache(thread_id):
            for i in range(100):
                key = f"key_{thread_id}_{i % 10}"
                cache.set(key, f"value_{i}")
                cache.get(key)
                cache.get(f"nonexistent_{i}")

        threads = [threading.Thread(target=access_cache, args=(i,)) for i in range(10)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = cache.stats
        # Total accesses should be consistent
        total_gets = stats.hits + stats.misses
        assert total_gets == 2000  # 10 threads * 100 iterations * 2 gets

    def test_concurrent_clear(self, cache):
        """Test concurrent clear and set operations."""
        errors = []

        def set_continuously():
            for i in range(100):
                try:
                    cache.set(f"key_{i}", f"value_{i}")
                except Exception as e:
                    errors.append(e)

        def clear_periodically():
            for _ in range(10):
                try:
                    cache.clear()
                    time.sleep(0.01)
                except Exception as e:
                    errors.append(e)

        threads = [
            threading.Thread(target=set_continuously),
            threading.Thread(target=clear_periodically),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors occurred: {errors}"


# ============================================================================
# L1Cache Statistics Tests
# ============================================================================


class TestL1CacheStatistics:
    """Test statistics tracking."""

    def test_hits_increment(self, cache):
        """Test hit counter increments on cache hit."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("key1")
        assert cache.stats.hits == 2

    def test_misses_increment(self, cache):
        """Test miss counter increments on cache miss."""
        cache.get("nonexistent1")
        cache.get("nonexistent2")
        assert cache.stats.misses == 2

    def test_sets_increment(self, cache):
        """Test set counter increments."""
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.stats.sets == 2

    def test_deletes_increment(self, cache):
        """Test delete counter increments on successful delete."""
        cache.set("key1", "value1")
        cache.delete("key1")
        assert cache.stats.deletes == 1

    def test_delete_miss_no_increment(self, cache):
        """Test delete counter doesn't increment on failed delete."""
        cache.delete("nonexistent")
        assert cache.stats.deletes == 0

    def test_get_stats_comprehensive(self, cache):
        """Test get_stats returns comprehensive statistics."""
        cache.set("key1", "value1")
        cache.get("key1")
        cache.get("nonexistent")

        stats_dict = cache.get_stats()

        assert stats_dict["tier"] == "L1"
        assert stats_dict["constitutional_hash"] == CONSTITUTIONAL_HASH
        assert stats_dict["maxsize"] == 100
        assert stats_dict["ttl"] == 60
        assert stats_dict["current_size"] == 1
        assert stats_dict["hits"] == 1
        assert stats_dict["misses"] == 1
        assert stats_dict["sets"] == 1
        assert stats_dict["hit_ratio"] == 0.5


# ============================================================================
# L1Cache Access Frequency Tests
# ============================================================================


class TestL1CacheAccessFrequency:
    """Test access frequency tracking for tier promotion."""

    def test_access_frequency_tracking(self, cache):
        """Test access frequency is tracked."""
        cache.set("key1", "value1")
        for _ in range(5):
            cache.get("key1")

        # 1 set + 5 gets = 6 accesses
        assert cache.get_access_frequency("key1") == 6

    def test_hot_keys_detection(self, cache):
        """Test hot keys are detected correctly."""
        # Create a hot key
        cache.set("hot_key", "value")
        for _ in range(15):
            cache.get("hot_key")

        # Create a cold key
        cache.set("cold_key", "value")
        cache.get("cold_key")

        hot_keys = cache.get_hot_keys(threshold=10)
        assert "hot_key" in hot_keys
        assert "cold_key" not in hot_keys

    def test_access_window_reset(self, cache):
        """Test access window resets after timeout."""
        # Override window for testing
        cache._access_window_seconds = 1

        cache.set("key1", "value1")
        for _ in range(5):
            cache.get("key1")

        assert cache.get_access_frequency("key1") == 6

        # Wait for window to reset
        time.sleep(1.5)

        assert cache.get_access_frequency("key1") == 0


# ============================================================================
# L1Cache Eviction Tests
# ============================================================================


class TestL1CacheEviction:
    """Test cache eviction behavior."""

    def test_maxsize_enforcement(self):
        """Test cache doesn't exceed maxsize."""
        cache = L1Cache(maxsize=10, ttl=60)

        for i in range(20):
            cache.set(f"key_{i}", f"value_{i}")

        assert cache.size <= 10

    def test_eviction_callback(self):
        """Test eviction callback is called on delete."""
        callback = MagicMock()
        cache = L1Cache(maxsize=10, ttl=60, on_evict=callback)

        cache.set("key1", "value1")
        cache.delete("key1")

        callback.assert_called_once_with("key1", "value1")

    def test_currsize_property(self):
        """Test currsize property for cachetools compatibility."""
        cache = L1Cache(maxsize=100, ttl=60)
        cache.set("key1", "value1")
        cache.set("key2", "value2")

        assert cache.currsize == 2
        assert cache.currsize == cache.size


# ============================================================================
# Singleton Pattern Tests
# ============================================================================


class TestL1CacheSingleton:
    """Test singleton pattern for L1Cache."""

    def test_get_l1_cache_returns_same_instance(self):
        """Test get_l1_cache returns singleton."""
        cache1 = get_l1_cache()
        cache2 = get_l1_cache()
        assert cache1 is cache2

    def test_singleton_thread_safe(self):
        """Test singleton creation is thread-safe."""
        caches = []

        def get_cache():
            caches.append(get_l1_cache())

        threads = [threading.Thread(target=get_cache) for _ in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All caches should be the same instance
        assert all(c is caches[0] for c in caches)

    def test_reset_l1_cache(self):
        """Test reset_l1_cache clears singleton."""
        cache1 = get_l1_cache()
        cache1.set("key1", "value1")

        reset_l1_cache()

        cache2 = get_l1_cache()
        assert cache2.get("key1") is None
        assert cache1 is not cache2

    def test_singleton_parameters_on_first_call(self):
        """Test singleton uses parameters from first call."""
        cache1 = get_l1_cache(maxsize=50, ttl=120)
        assert cache1.maxsize == 50
        assert cache1.ttl == 120

        # Second call with different params should return same instance
        cache2 = get_l1_cache(maxsize=100, ttl=60)
        assert cache2.maxsize == 50  # Original values
        assert cache2.ttl == 120


# ============================================================================
# Constitutional Hash Tests
# ============================================================================


class TestConstitutionalHash:
    """Test constitutional hash validation."""

    def test_constitutional_hash_defined(self):
        """Test CONSTITUTIONAL_HASH is defined."""
        assert CONSTITUTIONAL_HASH is not None
        assert len(CONSTITUTIONAL_HASH) > 0

    def test_constitutional_hash_in_stats(self, cache):
        """Test constitutional hash appears in stats."""
        stats = cache.get_stats()
        assert stats["constitutional_hash"] == CONSTITUTIONAL_HASH


# ============================================================================
# Edge Cases Tests
# ============================================================================


class TestL1CacheEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_key(self, cache):
        """Test handling of empty string key."""
        cache.set("", "empty_key_value")
        assert cache.get("") == "empty_key_value"

    def test_none_value(self, cache):
        """Test storing None as value."""
        cache.set("key_none", None)
        # get returns None for both missing and None values
        # but exists should return True
        assert cache.exists("key_none") is True

    def test_complex_values(self, cache):
        """Test storing complex Python objects."""
        data = {"nested": {"list": [1, 2, 3], "tuple": (4, 5, 6)}}
        cache.set("complex", data)
        result = cache.get("complex")
        assert result == data

    def test_unicode_key(self, cache):
        """Test Unicode characters in keys."""
        cache.set("key_", "unicode_value")
        assert cache.get("key_") == "unicode_value"

    def test_large_value(self, cache):
        """Test storing large values."""
        large_value = "x" * 100000
        cache.set("large", large_value)
        assert cache.get("large") == large_value

    def test_get_many_empty_list(self, cache):
        """Test get_many with empty list."""
        result = cache.get_many([])
        assert result == {}

    def test_set_many_empty_dict(self, cache):
        """Test set_many with empty dict."""
        initial_size = cache.size
        cache.set_many({})
        assert cache.size == initial_size


# ============================================================================
# Integration Tests
# ============================================================================


class TestL1CacheIntegration:
    """Integration tests for L1Cache."""

    def test_full_lifecycle(self, cache):
        """Test complete cache lifecycle."""
        # Set values
        cache.set("user:1", {"name": "Alice", "age": 30})
        cache.set("user:2", {"name": "Bob", "age": 25})

        # Get values
        assert cache.get("user:1") == {"name": "Alice", "age": 30}
        assert cache.get("user:2") == {"name": "Bob", "age": 25}

        # Check stats
        assert cache.stats.sets == 2
        assert cache.stats.hits == 2

        # Delete
        cache.delete("user:1")
        assert cache.get("user:1") is None
        assert cache.stats.deletes == 1
        assert cache.stats.misses == 1

        # Clear
        cache.clear()
        assert cache.size == 0

    def test_concurrent_lifecycle_stress(self, cache):
        """Stress test with concurrent operations."""
        errors = []

        def stress_test(thread_id):
            try:
                for i in range(200):
                    key = f"stress_{thread_id}_{i % 20}"
                    cache.set(key, f"value_{i}")
                    cache.get(key)
                    cache.get(f"nonexistent_{i}")
                    if i % 10 == 0:
                        cache.delete(key)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=stress_test, args=(i,)) for i in range(20)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Errors during stress test: {errors}"
        # Verify cache is still functional
        cache.set("final_key", "final_value")
        assert cache.get("final_key") == "final_value"
