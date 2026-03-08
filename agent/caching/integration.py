"""Integration module for caching system.

This module provides integration between the caching system and the existing
agent components (ContextManager, ModelManager, etc.).
"""

from pathlib import Path
from typing import Dict, Any, Optional, List

from .change_detector import HashBasedChangeDetector
from .content_addressable import ContentAddressableCache
from .response_cache import ResponseCache
from .token_budget import TokenBudgetEnforcer, TokenBudgetConfig, ActionOnExceed
from .lazy_loader import LazyDirectoryLoader, LazyContentProvider


class CachingIntegration:
    """Integrates all caching components for the agent.
    
    This class provides a unified interface to all caching functionality,
    making it easy to integrate with existing agent components.
    
    Example:
        >>> caching = CachingIntegration(workspace=Path('/workspace'))
        >>> # Check budget before API call
        >>> if caching.budget.check_budget(5000):
        ...     # Check response cache
        ...     cached = caching.responses.get(prompt, model, files)
        ...     if cached:
        ...         return cached
        ...     # Make API call and cache result
        ...     response = call_api(prompt)
        ...     caching.responses.set(prompt, model, files, response, tokens)
        ...     caching.budget.record_usage(tokens, 'completion', model)
    """

    def __init__(self, workspace: Path, cache_dir: Path = None,
                 token_budget_config: TokenBudgetConfig = None):
        """Initialize caching integration.
        
        Args:
            workspace: Root workspace directory
            cache_dir: Directory for cache files (default: ~/.cache/rapidwebs-agent)
            token_budget_config: Token budget configuration
        """
        self.workspace = workspace.resolve()
        self.cache_dir = cache_dir or (
            Path.home() / '.cache' / 'rapidwebs-agent'
        )
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Initialize all caching components
        self.change_detector = HashBasedChangeDetector(self.workspace)
        self.content_cache = ContentAddressableCache(
            db_path=self.cache_dir / 'content_cache.db'
        )
        self.responses = ResponseCache(
            ttl_seconds=1800,
            max_entries=500
        )
        self.budget = TokenBudgetEnforcer(
            token_budget_config or TokenBudgetConfig(
                enabled=True,
                daily_limit=100000,
                per_request_limit=8000,
                warning_threshold=0.8,
                action_on_exceed=ActionOnExceed.WARN
            )
        )
        self.lazy_loader = LazyDirectoryLoader(
            root=self.workspace,
            max_files=5000,
            max_memory_files=100
        )
        self.content_provider = LazyContentProvider(
            workspace=self.workspace,
            max_total_memory_mb=50.0
        )

        # State file paths
        self._change_state_file = self.cache_dir / 'change_detector_state.json'
        self._budget_state_file = self.cache_dir / 'token_budget_state.json'

        # Load persisted state
        self._load_state()

    def _load_state(self):
        """Load persisted state from disk."""
        self.change_detector.load_state(self._change_state_file)
        self.budget.load_state(self._budget_state_file)

    def save_state(self):
        """Persist state to disk."""
        self.change_detector.save_state(self._change_state_file)
        self.budget.save_state(self._budget_state_file)

    def check_and_get_cached(self, prompt: str, model: str,
                              files: List[str]) -> Optional[str]:
        """Check budget and get cached response.
        
        Args:
            prompt: Prompt text
            model: Model name
            files: List of file paths
            
        Returns:
            Cached response, or None if not available/budget exceeded
        """
        # Check budget
        estimated_tokens = 5000  # Default estimate
        if not self.budget.check_budget(estimated_tokens):
            return None

        # Check cache
        return self.responses.get(prompt, model, files)

    def cache_response_and_record_usage(self, prompt: str, model: str,
                                         files: List[str], response: str,
                                         tokens: int, request_type: str = 'completion'):
        """Cache response and record token usage.
        
        Args:
            prompt: Prompt text
            model: Model name
            files: List of file paths
            response: LLM response
            tokens: Token count
            request_type: Type of request
        """
        # Cache response
        self.responses.set(prompt, model, files, response, tokens)
        
        # Record usage
        self.budget.record_usage(tokens, request_type, model)

    def invalidate_files(self, file_paths: List[str]):
        """Invalidate caches for changed files.
        
        Args:
            file_paths: List of file paths that changed
        """
        for path_str in file_paths:
            path = Path(path_str)
            
            # Invalidate response cache
            self.responses.invalidate_file(path)
            
            # Invalidate content cache
            self.content_cache.invalidate_path(path)
            
            # Update change detector
            self.change_detector.track(path)

    def get_lazy_content(self, path: str) -> Optional[str]:
        """Get file content with lazy loading.
        
        Args:
            path: File path
            
        Returns:
            File content, or None if unavailable
        """
        return self.content_provider.get_content(Path(path))

    def is_file_changed(self, path: str) -> bool:
        """Check if file has changed.
        
        Args:
            path: File path
            
        Returns:
            True if changed, False if unchanged
        """
        return self.change_detector.has_changed(Path(path))

    def get_all_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics.
        
        Returns:
            Dictionary with all caching statistics
        """
        return {
            'change_detector': self.change_detector.get_stats(),
            'content_cache': self.content_cache.get_stats(),
            'response_cache': self.responses.get_stats(),
            'token_budget': self.budget.get_usage_report(),
            'lazy_loader': self.lazy_loader.get_stats(),
            'content_provider': self.content_provider.get_stats()
        }

    def get_detailed_stats(self) -> Dict[str, Any]:
        """Get detailed statistics with history.
        
        Returns:
            Dictionary with detailed statistics
        """
        return {
            'change_detector': self.change_detector.get_stats(),
            'content_cache': self.content_cache.get_stats(),
            'response_cache': self.responses.get_stats(),
            'token_budget': self.budget.get_detailed_report(),
            'lazy_loader': self.lazy_loader.get_stats(),
            'content_provider': self.content_provider.get_stats()
        }

    def cleanup(self, max_age_days: int = 30):
        """Clean up old cache entries.
        
        Args:
            max_age_days: Maximum age of entries to keep
        """
        # Clean content cache
        deleted = self.content_cache.cleanup(max_age_days=max_age_days)
        
        # Clean response cache (remove old entries)
        self.responses.remove_oldest(count=100)
        
        # Clean change detector state
        self.change_detector.validate_stale_entries(
            max_age_seconds=max_age_days * 86400
        )
        
        # Save state
        self.save_state()
        
        return {'content_cache_deleted': deleted}

    def clear_all(self):
        """Clear all caches and reset statistics."""
        self.change_detector.clear()
        self.content_cache.clear()
        self.responses.clear()
        self.budget.reset_daily()
        self.lazy_loader.clear()
        self.content_provider.loader.clear()
        self.save_state()


# Convenience functions for direct integration

def create_caching(workspace: str | Path,
                   daily_token_limit: int = 100000) -> CachingIntegration:
    """Create caching integration with common defaults.
    
    Args:
        workspace: Workspace directory path
        daily_token_limit: Daily token budget
        
    Returns:
        Configured CachingIntegration instance
    """
    if isinstance(workspace, str):
        workspace = Path(workspace)
    
    config = TokenBudgetConfig(
        enabled=True,
        daily_limit=daily_token_limit,
        per_request_limit=8000,
        warning_threshold=0.8,
        action_on_exceed=ActionOnExceed.WARN
    )
    
    return CachingIntegration(
        workspace=workspace,
        token_budget_config=config
    )


async def preload_workspace(caching: CachingIntegration,
                            patterns: List[str] = None) -> int:
    """Pre-load workspace files for faster access.
    
    Args:
        caching: CachingIntegration instance
        patterns: File patterns to preload
        
    Returns:
        Number of files preloaded
    """
    if patterns is None:
        patterns = ['*.py', '*.md', '*.txt', '*.json', '*.yaml', '*.yml']
    
    return await caching.lazy_loader.preload_likely_files(patterns)
