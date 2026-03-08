"""Optional external tools and integrations.

This package provides MCP servers and tool integrations for the RapidWebs Agent.
"""

from .mcp_server_caching import (
    initialize_caching,
    check_cache,
    cache_response,
    invalidate_files,
    get_stats,
    check_budget,
    get_lazy_content,
    is_file_changed,
    cleanup_cache,
    clear_all_cache,
)

__all__ = [
    'initialize_caching',
    'check_cache',
    'cache_response',
    'invalidate_files',
    'get_stats',
    'check_budget',
    'get_lazy_content',
    'is_file_changed',
    'cleanup_cache',
    'clear_all_cache',
]