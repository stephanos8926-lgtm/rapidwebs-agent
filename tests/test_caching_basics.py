#!/usr/bin/env python
"""Test caching functionality."""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from agent.caching import create_caching


def test_caching_basics():
    """Test basic caching operations."""
    
    print("=" * 60)
    print("Testing Caching System")
    print("=" * 60)
    
    # Create temp workspace
    with tempfile.TemporaryDirectory() as temp_dir:
        workspace = Path(temp_dir)
        
        # Create caching integration
        caching = create_caching(workspace, daily_token_limit=100000)
        
        print(f"\n✓ Caching initialized")
        print(f"  Workspace: {workspace}")
        print(f"  Cache dir: {caching.cache_dir}")
        
        # Test 1: Check cache (should be empty)
        print("\nTest 1: Check empty cache")
        cached = caching.check_and_get_cached(
            prompt="Test prompt",
            model="test-model",
            files=[]
        )
        assert cached is None, "Cache should be empty"
        print("  ✓ Empty cache returns None")
        
        # Test 2: Cache a response
        print("\nTest 2: Cache a response")
        caching.cache_response_and_record_usage(
            prompt="Test prompt",
            model="test-model",
            files=[],
            response="Test response",
            tokens=100
        )
        print("  ✓ Response cached")
        
        # Test 3: Retrieve cached response
        print("\nTest 3: Retrieve cached response")
        cached_response = caching.check_and_get_cached(
            prompt="Test prompt",
            model="test-model",
            files=[]
        )
        assert cached_response is not None, "Cache should have response"
        assert cached_response == "Test response", "Response should match"
        print(f"  ✓ Retrieved: {cached_response}")
        
        # Test 4: Different prompt should not be cached
        print("\nTest 4: Different prompt not cached")
        cached2 = caching.check_and_get_cached(
            prompt="Different prompt",
            model="test-model",
            files=[]
        )
        assert cached2 is None, "Different prompt should not be cached"
        print("  ✓ Different prompt returns None")
        
        # Test 5: Get stats
        print("\nTest 5: Get caching stats")
        stats = caching.get_all_stats()
        print(f"  ✓ Stats retrieved:")
        print(f"    - Budget: {stats.get('budget', {})}")
        print(f"    - Response cache: {stats.get('response_cache', {})}")
        print(f"    - Content cache: {stats.get('content_cache', {})}")
        
        # Test 6: Budget check
        print("\nTest 6: Budget check")
        budget_ok = caching.budget.check_budget(1000)
        print(f"  ✓ Budget check (1000 tokens): {budget_ok}")
        
        # Test 7: Clear cache
        print("\nTest 7: Clear cache")
        caching.clear_all()
        cached3 = caching.check_and_get_cached(
            prompt="Test prompt",
            model="test-model",
            files=[]
        )
        assert cached3 is None, "Cache should be cleared"
        print("  ✓ Cache cleared successfully")
        
    print("\n" + "=" * 60)
    print("ALL CACHING TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    test_caching_basics()
