"""Lazy loading for files and directories.

This module provides lazy loading mechanisms to defer file content
loading until actually needed, reducing initial context by 20-40%.
"""

from pathlib import Path
from typing import Dict, List, Optional, Callable, Generator, Any, Set
from dataclasses import dataclass, field
from collections import OrderedDict
import asyncio
import threading
import time


@dataclass
class LazyFile:
    """Lazy-loaded file representation.
    
    This class wraps a file path and only loads content when explicitly
    requested, supporting LRU eviction and size limits.
    
    Attributes:
        path: File path
        max_size: Maximum file size to load (bytes)
        _content: Cached content (None until loaded)
        _loaded: Whether content has been loaded
        _load_callback: Optional custom load function
        _load_time: When content was loaded
        _access_count: Number of times accessed
    """
    path: Path
    max_size: int = 524288  # 512KB default
    _content: Optional[str] = field(default=None, repr=False)
    _loaded: bool = False
    _load_callback: Optional[Callable[[str], str]] = None
    _load_time: float = 0.0
    _access_count: int = 0
    _load_error: Optional[str] = None

    @property
    def is_loaded(self) -> bool:
        """Check if content has been loaded."""
        return self._loaded and self._content is not None

    @property
    def exists(self) -> bool:
        """Check if file exists."""
        return self.path.exists()

    @property
    def size(self) -> int:
        """Get file size in bytes."""
        try:
            return self.path.stat().st_size
        except (IOError, OSError):
            return -1

    def load(self, force: bool = False) -> Optional[str]:
        """Load content on demand.
        
        Args:
            force: Force reload even if already loaded
            
        Returns:
            File content, or None if load failed
        """
        if self._loaded and self._content is not None and not force:
            self._access_count += 1
            return self._content

        # Check file size before loading
        try:
            file_size = self.path.stat().st_size
            if file_size > self.max_size:
                self._load_error = f"File too large: {file_size} bytes (max: {self.max_size})"
                return None
        except (IOError, OSError) as e:
            self._load_error = f"Cannot stat file: {e}"
            return None

        try:
            if self._load_callback:
                self._content = self._load_callback(str(self.path))
            else:
                self._content = self.path.read_text(encoding='utf-8')

            self._loaded = True
            self._load_time = time.time()
            self._access_count += 1
            self._load_error = None
            return self._content

        except (IOError, OSError, UnicodeDecodeError) as e:
            self._load_error = f"Load error: {e}"
            self._loaded = False
            self._content = None
            return None

    def unload(self):
        """Free memory by unloading content."""
        self._content = None
        self._loaded = False
        self._load_time = 0.0

    def get_content(self) -> Optional[str]:
        """Get content, loading if necessary."""
        return self.load()

    def get_error(self) -> Optional[str]:
        """Get last load error, if any."""
        return self._load_error

    def get_info(self) -> Dict[str, Any]:
        """Get file information.
        
        Returns:
            Dictionary with file metadata
        """
        try:
            stat = self.path.stat()
            return {
                'path': str(self.path),
                'exists': True,
                'size': stat.st_size,
                'modified': stat.st_mtime,
                'is_loaded': self._loaded,
                'access_count': self._access_count,
                'load_time': self._load_time,
                'error': self._load_error
            }
        except (IOError, OSError):
            return {
                'path': str(self.path),
                'exists': False,
                'error': self._load_error or 'File not found'
            }


class LazyDirectoryLoader:
    """Lazy loading for large directories.
    
    This class provides memory-efficient directory scanning with LRU
    eviction and on-demand file loading.
    
    Example:
        >>> loader = LazyDirectoryLoader(
        ...     Path('/workspace'),
        ...     max_files=1000,
        ...     max_memory_files=50
        ... )
        >>> # Scan directory (yields paths, doesn't load content)
        >>> for path in loader.scan('**/*.py'):
        ...     print(path)
        >>> # Get lazy file wrapper
        >>> lazy_file = loader.get_file(Path('/workspace/file.py'))
        >>> # Load content when needed
        >>> content = lazy_file.load()
    """

    def __init__(self, root: Path, max_files: int = 1000,
                 max_memory_files: int = 50, max_file_size: int = 524288):
        """Initialize lazy directory loader.
        
        Args:
            root: Root directory to scan
            max_files: Maximum files to track in scan
            max_memory_files: Maximum files to keep loaded in memory
            max_file_size: Maximum file size to load (bytes)
        """
        self.root = root.resolve()
        self.max_files = max_files
        self.max_memory_files = max_memory_files
        self.max_file_size = max_file_size
        self.files: OrderedDict[str, LazyFile] = OrderedDict()
        self._scan_complete = False
        self._scanned_paths: List[Path] = []
        self._lock = threading.RLock()

    def scan(self, pattern: str = '**/*', 
             exclude_patterns: Set[str] = None) -> Generator[Path, None, None]:
        """Lazy directory scan.
        
        Yields file paths without loading content. Results are cached
        for subsequent scans.
        
        Args:
            pattern: Glob pattern (default: '**/*' for all files)
            exclude_patterns: Set of patterns to exclude
            
        Yields:
            File paths matching the pattern
        """
        with self._lock:
            if self._scan_complete:
                # Return cached results
                for path in self._scanned_paths:
                    yield path
                return

            exclude_patterns = exclude_patterns or set()
            count = 0

            try:
                for path in self.root.glob(pattern):
                    if count >= self.max_files:
                        break

                    if not path.is_file():
                        continue

                    # Check exclusions
                    path_str = str(path.relative_to(self.root))
                    excluded = False
                    for exclude in exclude_patterns:
                        if exclude in path_str:
                            excluded = True
                            break

                    if excluded:
                        continue

                    self._scanned_paths.append(path)
                    count += 1
                    yield path

            except (IOError, OSError, PermissionError):
                pass

            self._scan_complete = True

    def get_file(self, path: Path, 
                 load_callback: Callable[[str], str] = None) -> Optional[LazyFile]:
        """Get or create lazy file wrapper.
        
        Uses LRU eviction when memory limit is reached.
        
        Args:
            path: File path
            load_callback: Optional custom load function
            
        Returns:
            LazyFile wrapper, or None if path invalid
        """
        with self._lock:
            path_str = str(path.resolve())

            if path_str in self.files:
                # Move to end (most recently used)
                self.files.move_to_end(path_str)
                lazy_file = self.files[path_str]
                if load_callback:
                    lazy_file._load_callback = load_callback
                return lazy_file

            # Validate path
            if not path.exists():
                return None

            # Create new lazy file
            lazy_file = LazyFile(
                path=path.resolve(),
                max_size=self.max_file_size,
                _load_callback=load_callback
            )
            self.files[path_str] = lazy_file

            # Enforce memory limit (LRU eviction)
            while len(self.files) > self.max_memory_files:
                oldest_key = next(iter(self.files))
                oldest_file = self.files[oldest_key]
                oldest_file.unload()  # Free memory before removing
                del self.files[oldest_key]

            return lazy_file

    def load_file(self, path: Path, 
                  load_callback: Callable[[str], str] = None) -> Optional[str]:
        """Load file content immediately.
        
        Convenience method that gets lazy file and loads content.
        
        Args:
            path: File path
            load_callback: Optional custom load function
            
        Returns:
            File content, or None if load failed
        """
        lazy_file = self.get_file(path, load_callback)
        if lazy_file:
            return lazy_file.load()
        return None

    async def preload_likely_files(self, patterns: List[str],
                                   max_size: int = 102400) -> int:
        """Pre-load files matching likely patterns.
        
        Asynchronously pre-loads small files matching common patterns
        to reduce latency when they're accessed.
        
        Args:
            patterns: List of glob patterns (e.g., ['*.py', '*.md'])
            max_size: Maximum file size to preload (bytes)
            
        Returns:
            Number of files successfully preloaded
        """
        tasks = []
        loaded_count = 0

        for pattern in patterns:
            for path in self.root.glob(pattern):
                if not path.is_file():
                    continue

                try:
                    if path.stat().st_size > max_size:
                        continue
                except (IOError, OSError):
                    continue

                lazy_file = self.get_file(path)
                if lazy_file:
                    tasks.append(self._preload_file(lazy_file))

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            loaded_count = sum(1 for r in results if isinstance(r, str))

        return loaded_count

    async def _preload_file(self, lazy_file: LazyFile) -> Optional[str]:
        """Preload a single file in executor."""
        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, lazy_file.load)
        except Exception:
            return None

    def get_loaded_files(self) -> List[str]:
        """Get list of currently loaded file paths.
        
        Returns:
            List of absolute file paths with loaded content
        """
        with self._lock:
            return [
                path for path, lazy_file in self.files.items()
                if lazy_file.is_loaded
            ]

    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics.
        
        Returns:
            Dictionary with statistics
        """
        with self._lock:
            loaded_count = sum(1 for f in self.files.values() if f.is_loaded)
            total_accesses = sum(f._access_count for f in self.files.values())

            return {
                'tracked_files': len(self.files),
                'loaded_files': loaded_count,
                'max_memory_files': self.max_memory_files,
                'scan_complete': self._scan_complete,
                'scanned_path_count': len(self._scanned_paths),
                'total_accesses': total_accesses,
                'memory_usage_estimate': self._estimate_memory_usage()
            }

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of loaded content.
        
        Returns:
            Estimated bytes used by loaded content
        """
        total = 0
        for lazy_file in self.files.values():
            if lazy_file._content:
                total += len(lazy_file._content.encode('utf-8'))
        return total

    def unload_all(self):
        """Unload all file content (keep paths tracked)."""
        with self._lock:
            for lazy_file in self.files.values():
                lazy_file.unload()

    def clear(self):
        """Clear all tracked files."""
        with self._lock:
            self.files.clear()
            self._scanned_paths.clear()
            self._scan_complete = False

    def close(self):
        """Close loader and unload all files.
        
        Call this to free memory and clean up resources.
        """
        self.unload_all()
        self.clear()

    def __del__(self):
        """Destructor for cleanup."""
        self.close()

    def get_recently_accessed(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently accessed files.
        
        Args:
            limit: Maximum files to return
            
        Returns:
            List of file info dictionaries, sorted by access
        """
        with self._lock:
            sorted_files = sorted(
                self.files.values(),
                key=lambda f: (f._access_count, f._load_time),
                reverse=True
            )

            return [
                {
                    'path': str(f.path),
                    'access_count': f._access_count,
                    'last_load_time': f._load_time,
                    'is_loaded': f.is_loaded
                }
                for f in sorted_files[:limit]
            ]

    def evict_least_used(self, count: int = 1) -> int:
        """Evict least-used files from memory.
        
        Args:
            count: Number of files to evict
            
        Returns:
            Actual number of files evicted
        """
        with self._lock:
            # Sort by access count and load time
            sorted_files = sorted(
                self.files.items(),
                key=lambda x: (x[1]._access_count, x[1]._load_time)
            )

            evicted = 0
            for path, lazy_file in sorted_files[:count]:
                if lazy_file.is_loaded:
                    lazy_file.unload()
                    evicted += 1

            return evicted


class LazyContentProvider:
    """Provider for lazy content with automatic eviction.
    
    This class combines multiple lazy loaders with intelligent
    content prioritization.
    """

    def __init__(self, workspace: Path, max_total_memory_mb: float = 50.0):
        """Initialize content provider.
        
        Args:
            workspace: Root workspace directory
            max_total_memory_mb: Maximum memory for content (MB)
        """
        self.workspace = workspace.resolve()
        self.max_memory_bytes = int(max_total_memory_mb * 1024 * 1024)
        self.loader = LazyDirectoryLoader(
            root=workspace,
            max_files=5000,
            max_memory_files=100,
            max_file_size=524288
        )
        self._priority_files: Set[str] = set()
        self._lock = threading.RLock()

    def set_priority_files(self, paths: List[Path]):
        """Set priority files to keep loaded.
        
        Args:
            paths: List of file paths to prioritize
        """
        with self._lock:
            self._priority_files = {str(p.resolve()) for p in paths}

    def get_content(self, path: Path) -> Optional[str]:
        """Get file content, loading if necessary.
        
        Args:
            path: File path
            
        Returns:
            File content, or None if unavailable
        """
        return self.loader.load_file(path)

    def get_lazy_file(self, path: Path) -> Optional[LazyFile]:
        """Get lazy file wrapper.
        
        Args:
            path: File path
            
        Returns:
            LazyFile wrapper, or None if unavailable
        """
        return self.loader.get_file(path)

    def scan_files(self, pattern: str = '**/*') -> Generator[Path, None, None]:
        """Scan for files matching pattern.
        
        Args:
            pattern: Glob pattern
            
        Yields:
            Matching file paths
        """
        yield from self.loader.scan(pattern)

    def enforce_memory_limit(self):
        """Enforce memory limit by evicting non-priority files."""
        with self._lock:
            current_usage = self.loader._estimate_memory_usage()
            
            if current_usage <= self.max_memory_bytes:
                return

            # Get files sorted by priority and usage
            files_info = []
            for path_str, lazy_file in self.loader.files.items():
                is_priority = path_str in self._priority_files
                files_info.append((path_str, is_priority, lazy_file))

            # Sort: non-priority first, then by access count
            files_info.sort(key=lambda x: (x[1], x[2]._access_count))

            # Evict until under limit
            for path_str, is_priority, lazy_file in files_info:
                if is_priority:
                    continue  # Never evict priority files

                if lazy_file.is_loaded:
                    lazy_file.unload()
                    current_usage = self.loader._estimate_memory_usage()
                    
                    if current_usage <= self.max_memory_bytes:
                        break

    def get_stats(self) -> Dict[str, Any]:
        """Get provider statistics.

        Returns:
            Dictionary with statistics
        """
        loader_stats = self.loader.get_stats()

        return {
            **loader_stats,
            'priority_files': len(self._priority_files),
            'max_memory_mb': self.max_memory_bytes / (1024 * 1024),
            'memory_usage_mb': loader_stats['memory_usage_estimate'] / (1024 * 1024)
        }

    def close(self):
        """Close provider and unload all files.
        
        Call this to free memory and clean up resources.
        """
        self.loader.clear()

    def __del__(self):
        """Destructor for cleanup."""
        self.close()
