"""Integration tests for rw-agent Tier 4 caching system.

This module tests the caching integration components:
1. Cache hit/miss functionality
2. File invalidation triggers cache miss
3. Token budget enforcement
4. Statistics tracking
5. Lazy loading
6. Content-addressable storage

Usage:
    pytest tests/test_caching_integration.py -v
"""

import pytest
import tempfile
import time
from pathlib import Path
from typing import List

# Import caching components
from agent.caching import (
    create_caching,
    CachingIntegration,
    HashBasedChangeDetector,
    ContentAddressableCache,
    ResponseCache,
    TokenBudgetEnforcer,
    TokenBudgetConfig,
    ActionOnExceed,
    LazyDirectoryLoader,
    LazyContentProvider,
)


class TestCachingIntegration:
    """Test the CachingIntegration class."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def caching(self, temp_workspace):
        """Create a caching integration instance."""
        return create_caching(temp_workspace, daily_token_limit=100000)

    @pytest.fixture
    def test_file(self, temp_workspace):
        """Create a test file in the workspace."""
        test_file = temp_workspace / "test.py"
        test_file.write_text("def hello():\n    return 'world'\n")
        return test_file

    def test_initialization(self, caching, temp_workspace):
        """Test caching system initialization."""
        assert caching is not None
        assert caching.workspace == temp_workspace.resolve()
        assert caching.cache_dir.exists()
        assert caching.change_detector is not None
        assert caching.content_cache is not None
        assert caching.responses is not None
        assert caching.budget is not None
        assert caching.lazy_loader is not None
        assert caching.content_provider is not None

    def test_check_and_get_cached_miss(self, caching):
        """Test cache miss on first check."""
        result = caching.check_and_get_cached(
            prompt="test prompt",
            model="test-model",
            files=["test.py"]
        )
        assert result is None

    def test_check_and_get_cached_hit(self, caching):
        """Test cache hit after caching response."""
        prompt = "test prompt for hit"
        model = "test-model"
        files = ["test.py"]
        response = "test response content"
        tokens = 500

        # First check should miss
        result = caching.check_and_get_cached(prompt, model, files)
        assert result is None

        # Cache the response
        caching.cache_response_and_record_usage(
            prompt, model, files, response, tokens
        )

        # Second check should hit
        result = caching.check_and_get_cached(prompt, model, files)
        assert result == response

    def test_cache_response_and_record_usage(self, caching):
        """Test caching response and recording token usage."""
        prompt = "test prompt"
        model = "test-model"
        files = ["test.py"]
        response = "test response"
        tokens = 1000

        caching.cache_response_and_record_usage(
            prompt, model, files, response, tokens
        )

        # Verify response is cached
        cached = caching.responses.get(prompt, model, files)
        assert cached == response

        # Verify token usage is recorded
        stats = caching.budget.get_usage_report()
        assert stats['daily_usage'] >= tokens

    def test_invalidate_files(self, caching, test_file):
        """Test file invalidation triggers cache miss."""
        prompt = "test prompt"
        model = "test-model"
        files = [str(test_file)]
        response = "test response"
        tokens = 500

        # Cache the response
        caching.cache_response_and_record_usage(
            prompt, model, files, response, tokens
        )

        # Verify cached
        assert caching.check_and_get_cached(prompt, model, files) == response

        # Modify the file
        test_file.write_text("def hello():\n    return 'modified'\n")

        # Invalidate the file
        caching.invalidate_files([str(test_file)])

        # Should now miss
        result = caching.check_and_get_cached(prompt, model, files)
        assert result is None

    def test_get_lazy_content(self, caching, test_file):
        """Test lazy content loading."""
        content = caching.get_lazy_content(str(test_file))
        assert content is not None
        assert "def hello():" in content
        assert "return 'world'" in content

    def test_is_file_changed(self, caching, test_file):
        """Test file change detection."""
        # Track the file initially
        caching.change_detector.track(test_file)

        # Should not be changed immediately
        assert not caching.is_file_changed(str(test_file))

        # Modify the file
        time.sleep(0.1)  # Ensure mtime changes
        test_file.write_text("modified content")

        # Should be changed now
        assert caching.is_file_changed(str(test_file))

    def test_get_all_stats(self, caching):
        """Test getting comprehensive statistics."""
        stats = caching.get_all_stats()

        assert 'change_detector' in stats
        assert 'content_cache' in stats
        assert 'response_cache' in stats
        assert 'token_budget' in stats
        assert 'lazy_loader' in stats
        assert 'content_provider' in stats

        # Check response cache stats structure
        response_stats = stats['response_cache']
        assert 'hits' in response_stats
        assert 'misses' in response_stats
        assert 'hit_rate' in response_stats

        # Check token budget stats structure
        budget_stats = stats['token_budget']
        assert 'daily_usage' in budget_stats
        assert 'daily_limit' in budget_stats
        assert 'remaining' in budget_stats

    def test_cleanup(self, caching):
        """Test cache cleanup."""
        # Add some data
        caching.cache_response_and_record_usage(
            "test", "model", ["test.py"], "response", 100
        )

        # Cleanup
        result = caching.cleanup(max_age_days=30)
        assert 'content_cache_deleted' in result

    def test_clear_all(self, caching):
        """Test clearing all caches."""
        # Add some data
        caching.cache_response_and_record_usage(
            "test", "model", ["test.py"], "response", 100
        )

        # Clear all
        caching.clear_all()

        # Verify cleared
        stats = caching.get_all_stats()
        assert stats['response_cache']['cache_size'] == 0
        assert stats['token_budget']['daily_usage'] == 0


class TestResponseCache:
    """Test the ResponseCache class."""

    @pytest.fixture
    def cache(self):
        """Create a response cache instance."""
        return ResponseCache(ttl_seconds=1800, max_entries=100)

    def test_cache_miss(self, cache):
        """Test cache miss."""
        result = cache.get("prompt", "model", ["file.py"])
        assert result is None

    def test_cache_hit(self, cache):
        """Test cache hit."""
        cache.set("prompt", "model", ["file.py"], "response", 100)
        result = cache.get("prompt", "model", ["file.py"])
        assert result == "response"

    def test_cache_ttl_expiration(self):
        """Test TTL-based expiration."""
        cache = ResponseCache(ttl_seconds=1, max_entries=100)
        cache.set("prompt", "model", ["file.py"], "response", 100)

        # Should hit immediately
        assert cache.get("prompt", "model", ["file.py"]) == "response"

        # Wait for expiration
        time.sleep(1.1)

        # Should miss after TTL
        result = cache.get("prompt", "model", ["file.py"])
        assert result is None

    def test_cache_invalidate_file(self, cache, tmp_path):
        """Test file invalidation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("original")

        cache.set("prompt", "model", [str(test_file)], "response", 100)

        # Modify file
        test_file.write_text("modified")

        # Invalidate
        cache.invalidate_file(str(test_file))

        # Should miss
        result = cache.get("prompt", "model", [str(test_file)])
        assert result is None

    def test_cache_stats(self, cache):
        """Test cache statistics."""
        cache.set("prompt1", "model", ["file.py"], "response1", 100)
        cache.get("prompt1", "model", ["file.py"])  # Hit
        cache.get("prompt2", "model", ["file.py"])  # Miss

        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1
        assert stats['cache_size'] == 1


class TestTokenBudget:
    """Test the TokenBudgetEnforcer class."""

    @pytest.fixture
    def budget(self):
        """Create a token budget enforcer."""
        config = TokenBudgetConfig(
            enabled=True,
            daily_limit=10000,
            per_request_limit=1000,
            warning_threshold=0.8
        )
        return TokenBudgetEnforcer(config)

    def test_check_budget_allowed(self, budget):
        """Test budget check for allowed request."""
        assert budget.check_budget(500) is True

    def test_check_budget_exceeds_per_request(self, budget):
        """Test budget check exceeds per-request limit."""
        # Should still return True with WARN action
        assert budget.check_budget(1500) is True

    def test_check_budget_exceeds_daily(self, budget):
        """Test budget check exceeds daily limit."""
        # Use up most of the budget
        budget.record_usage(9000, "completion", "model")

        # Should still return True with WARN action
        assert budget.check_budget(2000) is True

    def test_record_usage(self, budget):
        """Test recording token usage."""
        budget.record_usage(500, "completion", "model")
        budget.record_usage(300, "prompt", "model")

        report = budget.get_usage_report()
        assert report['daily_usage'] == 800
        assert report['request_count'] == 2

    def test_usage_report(self, budget):
        """Test usage report."""
        budget.record_usage(5000, "completion", "model")

        report = budget.get_usage_report()
        assert report['daily_usage'] == 5000
        assert report['daily_limit'] == 10000
        assert report['remaining'] == 5000
        assert report['usage_percentage'] == 50.0

    def test_reset_daily(self, budget):
        """Test daily reset."""
        budget.record_usage(5000, "completion", "model")
        budget.reset_daily()

        report = budget.get_usage_report()
        assert report['daily_usage'] == 0


class TestHashBasedChangeDetector:
    """Test the HashBasedChangeDetector class."""

    @pytest.fixture
    def detector(self, tmp_path):
        """Create a change detector."""
        return HashBasedChangeDetector(tmp_path)

    def test_track_file(self, detector, tmp_path):
        """Test tracking a file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        state = detector.track(test_file)
        assert state.path == str(test_file.resolve())
        assert state.size > 0
        assert state.content_hash != '0' * 16

    def test_has_changed_no_change(self, detector, tmp_path):
        """Test no change detected."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        detector.track(test_file)
        assert not detector.has_changed(test_file)

    def test_has_changed_with_change(self, detector, tmp_path):
        """Test change detected."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        detector.track(test_file)

        # Modify file
        time.sleep(0.1)
        test_file.write_text("modified")

        assert detector.has_changed(test_file)

    def test_get_stats(self, detector, tmp_path):
        """Test statistics."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        detector.track(test_file)

        stats = detector.get_stats()
        assert stats['tracked_files'] == 1
        assert stats['total_size'] > 0


class TestContentAddressableCache:
    """Test the ContentAddressableCache class."""

    @pytest.fixture
    def cache(self, tmp_path):
        """Create a content-addressable cache."""
        db_path = tmp_path / "cache.db"
        return ContentAddressableCache(db_path=db_path)

    def test_store_and_retrieve(self, cache):
        """Test storing and retrieving content."""
        content = b"Hello, World!"
        content_hash = cache.store(content, "text")

        retrieved = cache.retrieve(content_hash)
        assert retrieved == content

    def test_deduplication(self, cache):
        """Test content deduplication."""
        content = b"Duplicate content"

        # Store twice
        hash1 = cache.store(content, "text")
        hash2 = cache.store(content, "text")

        # Should be same hash
        assert hash1 == hash2

        # Check stats
        stats = cache.get_stats()
        assert stats['total_entries'] == 1

    def test_path_mapping(self, cache, tmp_path):
        """Test path-to-hash mapping."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        content = test_file.read_bytes()
        content_hash = cache.store(content, "text")

        cache.update_path_mapping(test_file, content_hash, test_file.stat().st_mtime)

        retrieved_hash = cache.get_path_hash(test_file)
        assert retrieved_hash == content_hash

    def test_invalidate_path(self, cache, tmp_path):
        """Test path invalidation."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        content = test_file.read_bytes()
        content_hash = cache.store(content, "text")
        cache.update_path_mapping(test_file, content_hash, test_file.stat().st_mtime)

        # Invalidate
        cache.invalidate_path(test_file)

        # Should be removed
        assert cache.get_path_hash(test_file) is None


class TestLazyDirectoryLoader:
    """Test the LazyDirectoryLoader class."""

    @pytest.fixture
    def loader(self, tmp_path):
        """Create a lazy directory loader."""
        return LazyDirectoryLoader(root=tmp_path, max_files=100, max_memory_files=10)

    def test_scan_files(self, loader, tmp_path):
        """Test scanning files."""
        # Create test files
        (tmp_path / "file1.py").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")

        files = list(loader.scan("**/*.py"))
        assert len(files) == 2

    def test_get_file(self, loader, tmp_path):
        """Test getting lazy file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        lazy_file = loader.get_file(test_file)
        assert lazy_file is not None
        assert not lazy_file.is_loaded

    def test_load_file(self, loader, tmp_path):
        """Test loading file content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("test content")

        content = loader.load_file(test_file)
        assert content == "test content"

    def test_get_stats(self, loader, tmp_path):
        """Test statistics."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        loader.load_file(test_file)

        stats = loader.get_stats()
        assert stats['tracked_files'] >= 1
        assert stats['loaded_files'] >= 1


class TestLazyContentProvider:
    """Test the LazyContentProvider class."""

    @pytest.fixture
    def provider(self, tmp_path):
        """Create a lazy content provider."""
        return LazyContentProvider(tmp_path, max_total_memory_mb=10.0)

    def test_get_content(self, provider, tmp_path):
        """Test getting content."""
        test_file = tmp_path / "test.py"
        test_file.write_text("test content")

        content = provider.get_content(test_file)
        assert content == "test content"

    def test_get_lazy_file(self, provider, tmp_path):
        """Test getting lazy file."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        lazy_file = provider.get_lazy_file(test_file)
        assert lazy_file is not None

    def test_get_stats(self, provider, tmp_path):
        """Test statistics."""
        test_file = tmp_path / "test.py"
        test_file.write_text("content")

        provider.get_content(test_file)

        stats = provider.get_stats()
        assert 'tracked_files' in stats
        assert 'loaded_files' in stats
        assert 'memory_usage_mb' in stats


class TestMCPServerTools:
    """Test MCP server tool functions."""

    @pytest.fixture
    def temp_workspace(self):
        """Create a temporary workspace."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_cwd = Path.cwd()
            import os
            os.chdir(tmpdir)
            yield Path(tmpdir)
            os.chdir(old_cwd)

    def test_initialize_caching(self, temp_workspace):
        """Test initialize_caching function."""
        from tools.mcp_server_caching import initialize_caching, caching

        # Reset global
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        result = initialize_caching(100000)
        assert result['status'] == 'initialized'
        assert result['daily_token_limit'] == 100000

    def test_check_cache(self, temp_workspace):
        """Test check_cache function."""
        from tools.mcp_server_caching import initialize_caching, check_cache
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        initialize_caching(100000)

        result = check_cache("test", "model", ["test.py"])
        assert result['cached'] is False

    def test_cache_response(self, temp_workspace):
        """Test cache_response function."""
        from tools.mcp_server_caching import (
            initialize_caching,
            cache_response,
            check_cache,
        )
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        initialize_caching(100000)

        # Cache a response
        result = cache_response("test", "model", ["test.py"], "response", 100)
        assert result['status'] == 'cached'

        # Check it's cached
        result = check_cache("test", "model", ["test.py"])
        assert result['cached'] is True
        assert result['response'] == "response"

    def test_invalidate_files(self, temp_workspace):
        """Test invalidate_files function."""
        from tools.mcp_server_caching import (
            initialize_caching,
            cache_response,
            invalidate_files,
            check_cache,
        )
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        initialize_caching(100000)

        # Cache a response
        cache_response("test", "model", ["test.py"], "response", 100)

        # Invalidate
        result = invalidate_files(["test.py"])
        assert 'invalidated' in result

    def test_get_stats(self, temp_workspace):
        """Test get_stats function."""
        from tools.mcp_server_caching import initialize_caching, get_stats
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        initialize_caching(100000)

        stats = get_stats()
        assert 'response_cache' in stats
        assert 'token_budget' in stats

    def test_check_budget(self, temp_workspace):
        """Test check_budget function."""
        from tools.mcp_server_caching import initialize_caching, check_budget
        import tools.mcp_server_caching as server_module
        server_module.caching = None

        initialize_caching(100000)

        result = check_budget(5000)
        assert 'allowed' in result
        assert 'remaining' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
