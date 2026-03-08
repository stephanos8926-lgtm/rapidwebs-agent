"""Caching and optimization modules for token efficiency and security.

This package provides:
- Hash-based change detection for files
- Content-addressable storage for deduplication
- Response caching with file invalidation
- Token budget enforcement
- Lazy directory loading
- Integration utilities for agent components

Example:
    >>> from agent.caching import create_caching
    >>> caching = create_caching('/workspace', daily_token_limit=100000)
    >>> 
    >>> # Check budget and cache before API call
    >>> cached = caching.check_and_get_cached(prompt, model, files)
    >>> if cached:
    ...     return cached
    >>> 
    >>> # Make API call and cache result
    >>> response = call_llm_api(prompt)
    >>> caching.cache_response_and_record_usage(prompt, model, files, response, tokens)
"""

from .change_detector import HashBasedChangeDetector, FileState
from .content_addressable import ContentAddressableCache
from .response_cache import ResponseCache, CacheEntry
from .token_budget import TokenBudgetEnforcer, TokenBudgetConfig, ActionOnExceed
from .lazy_loader import LazyDirectoryLoader, LazyFile, LazyContentProvider
from .integration import CachingIntegration, create_caching, preload_workspace

__all__ = [
    # Core caching components
    'HashBasedChangeDetector',
    'FileState',
    'ContentAddressableCache',
    'ResponseCache',
    'CacheEntry',
    'TokenBudgetEnforcer',
    'TokenBudgetConfig',
    'ActionOnExceed',
    'LazyDirectoryLoader',
    'LazyFile',
    'LazyContentProvider',
    # Integration
    'CachingIntegration',
    'create_caching',
    'preload_workspace',
]
