"""Temporary file management for RapidWebs Agent.

This module provides a centralized temporary file system with:
- Cross-platform temp directory management
- Content-addressable storage for deduplication
- Automatic cleanup on session end
- Configurable retention policies
- Safe file operations with proper error handling

Example:
    temp_mgr = TempManager()
    
    # Create temp file with content
    temp_path = await temp_mgr.create_temp_file("output.txt", large_content)
    
    # Read temp file
    content = await temp_mgr.read_temp_file(temp_path)
    
    # Search within temp file
    matches = await temp_mgr.search_file(temp_path, "pattern")
    
    # Cleanup old files
    await temp_mgr.cleanup_old_files(hours=24)
"""

import os
import hashlib
import asyncio
from pathlib import Path
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone, timedelta
import re
import shutil

from .logging_config import get_logger

logger = get_logger('temp_manager')


class TempManager:
    """Manage temporary files for agent operations.
    
    Attributes:
        temp_dir: Base temporary directory path
        session_id: Current session identifier
        file_registry: Registry of created temp files with metadata
        max_file_size: Maximum allowed file size in bytes
        retention_hours: Default retention period in hours
    """
    
    def __init__(
        self,
        session_id: Optional[str] = None,
        base_temp_dir: Optional[Path] = None,
        max_file_size: int = 100 * 1024 * 1024,  # 100MB
        retention_hours: int = 24
    ):
        """Initialize temporary file manager.
        
        Args:
            session_id: Session identifier (auto-generated if not provided)
            base_temp_dir: Custom base temp directory (uses system temp if not provided)
            max_file_size: Maximum allowed file size in bytes
            retention_hours: Default retention period for cleanup
        """
        self.session_id = session_id or datetime.now().strftime('%Y%m%d_%H%M%S')
        self.max_file_size = max_file_size
        self.retention_hours = retention_hours
        self.file_registry: Dict[str, Dict[str, Any]] = {}
        
        # Determine base temp directory
        if base_temp_dir:
            self.base_temp_dir = base_temp_dir
        else:
            self.base_temp_dir = self._get_system_temp_dir()
        
        # Create session-specific subdirectory
        self.temp_dir = self.base_temp_dir / 'rapidwebs-agent' / f'session_{self.session_id}'
        self.content_dir = self.temp_dir / 'content'
        self.output_dir = self.temp_dir / 'output'
        self.cache_dir = self.temp_dir / 'cache'
        
        # Initialize directories
        self._init_directories()
        
        logger.info(f'TempManager initialized: {self.temp_dir}')
    
    def _get_system_temp_dir(self) -> Path:
        """Get system-appropriate temporary directory.
        
        Returns:
            Path to system temp directory
        """
        if os.name == 'nt':  # Windows
            temp_dir = os.environ.get('TEMP', os.environ.get('TMP', r'C:\Temp'))
        elif os.name == 'posix':  # Unix/Linux/macOS
            temp_dir = os.environ.get('TMPDIR', '/tmp')
        else:
            temp_dir = '.'
        
        return Path(temp_dir)
    
    def _init_directories(self):
        """Create necessary directory structure."""
        try:
            self.temp_dir.mkdir(parents=True, exist_ok=True)
            self.content_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            logger.debug(f'Created temp directories: {self.temp_dir}')
        except OSError as e:
            logger.error(f'Failed to create temp directories: {e}')
            raise
    
    def _compute_content_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for deduplication.
        
        Args:
            content: Content to hash
            
        Returns:
            Hexadecimal hash string (first 16 chars)
        """
        return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]
    
    def _generate_filename(self, prefix: str, extension: str, content_hash: Optional[str] = None) -> str:
        """Generate unique filename.
        
        Args:
            prefix: Filename prefix
            extension: File extension
            content_hash: Optional content hash for deduplication
            
        Returns:
            Generated filename
        """
        timestamp = datetime.now().strftime('%H%M%S_%f')
        if content_hash:
            return f'{prefix}_{content_hash}.{extension}'
        else:
            return f'{prefix}_{timestamp}.{extension}'
    
    async def create_temp_file(
        self,
        filename: str,
        content: str,
        category: str = 'output',
        metadata: Optional[Dict[str, Any]] = None
    ) -> Path:
        """Create temporary file with content.
        
        Args:
            filename: Base filename (extension will be preserved)
            content: File content
            category: Category directory ('output', 'content', 'cache')
            metadata: Optional metadata to store with file
            
        Returns:
            Path to created file
            
        Raises:
            ValueError: If content exceeds max_file_size
            OSError: If file creation fails
        """
        # Validate file size
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self.max_file_size:
            raise ValueError(f'Content exceeds max file size: {len(content_bytes)} > {self.max_file_size}')
        
        # Determine target directory
        if category not in ['output', 'content', 'cache']:
            category = 'output'
        target_dir = getattr(self, f'{category}_dir', self.output_dir)
        
        # Compute content hash for deduplication
        content_hash = self._compute_content_hash(content)
        
        # Parse filename
        path_obj = Path(filename)
        prefix = path_obj.stem or 'temp'
        extension = path_obj.suffix.lstrip('.') or 'txt'
        
        # Generate unique filename with content hash
        unique_filename = self._generate_filename(prefix, extension, content_hash)
        file_path = target_dir / unique_filename
        
        # Check if identical content already exists (deduplication)
        if content_hash in self.file_registry:
            existing_path = Path(self.file_registry[content_hash]['path'])
            if existing_path.exists():
                logger.debug(f'Using existing file with hash {content_hash}: {existing_path}')
                return existing_path
        
        # Write file asynchronously
        await asyncio.to_thread(self._write_file_sync, file_path, content)
        
        # Register file
        file_metadata = {
            'path': str(file_path),
            'filename': unique_filename,
            'category': category,
            'size': len(content_bytes),
            'hash': content_hash,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'metadata': metadata or {}
        }
        self.file_registry[content_hash] = file_metadata
        
        logger.debug(f'Created temp file: {file_path} ({len(content_bytes)} bytes)')
        return file_path
    
    def _write_file_sync(self, path: Path, content: str):
        """Synchronous file write helper.
        
        Args:
            path: File path
            content: File content
        """
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    async def read_temp_file(
        self,
        file_path: Path,
        start_line: Optional[int] = None,
        end_line: Optional[int] = None,
        encoding: str = 'utf-8'
    ) -> str:
        """Read temporary file content.
        
        Args:
            file_path: Path to file
            start_line: Optional start line (1-indexed)
            end_line: Optional end line (1-indexed, inclusive)
            encoding: File encoding
            
        Returns:
            File content (optionally subset by lines)
            
        Raises:
            FileNotFoundError: If file doesn't exist
        """
        if not file_path.exists():
            raise FileNotFoundError(f'Temp file not found: {file_path}')
        
        # Read asynchronously
        content = await asyncio.to_thread(self._read_file_sync, file_path, encoding)
        
        # Subset by lines if requested
        if start_line is not None or end_line is not None:
            lines = content.splitlines()
            start_idx = (start_line - 1) if start_line else 0
            end_idx = end_line if end_line else len(lines)
            lines = lines[start_idx:end_idx]
            content = '\n'.join(lines)
        
        return content
    
    def _read_file_sync(self, path: Path, encoding: str) -> str:
        """Synchronous file read helper.
        
        Args:
            path: File path
            encoding: File encoding
            
        Returns:
            File content
        """
        with open(path, 'r', encoding=encoding) as f:
            return f.read()
    
    async def search_file(
        self,
        file_path: Path,
        pattern: str,
        context_lines: int = 2,
        max_matches: int = 100
    ) -> List[Dict[str, Any]]:
        """Search for pattern in file content.
        
        Args:
            file_path: Path to file
            pattern: Regular expression pattern
            context_lines: Number of context lines before/after match
            max_matches: Maximum matches to return
            
        Returns:
            List of match dictionaries with line number, content, and context
        """
        if not file_path.exists():
            logger.warning(f'File not found for search: {file_path}')
            return []
        
        try:
            regex = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        except re.error as e:
            logger.error(f'Invalid regex pattern: {e}')
            return []
        
        content = await self.read_temp_file(file_path)
        lines = content.splitlines()
        
        matches = []
        for i, line in enumerate(lines):
            if regex.search(line):
                # Get context
                start_idx = max(0, i - context_lines)
                end_idx = min(len(lines), i + context_lines + 1)
                context = lines[start_idx:end_idx]
                
                matches.append({
                    'line_number': i + 1,
                    'content': line,
                    'context': context,
                    'file': str(file_path)
                })
                
                if len(matches) >= max_matches:
                    break
        
        logger.debug(f'Search found {len(matches)} matches for pattern: {pattern}')
        return matches
    
    async def grep_file(
        self,
        file_path: Path,
        query: str,
        case_sensitive: bool = False,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Simple grep-like search in file.
        
        Args:
            file_path: Path to file
            query: Search query (substring match)
            case_sensitive: Whether search is case-sensitive
            max_results: Maximum results to return
            
        Returns:
            List of matching lines with line numbers
        """
        if not file_path.exists():
            return []
        
        content = await self.read_temp_file(file_path)
        lines = content.splitlines()
        
        results = []
        for i, line in enumerate(lines):
            if case_sensitive:
                if query in line:
                    results.append({'line': i + 1, 'content': line})
            else:
                if query.lower() in line.lower():
                    results.append({'line': i + 1, 'content': line})
            
            if len(results) >= max_results:
                break
        
        return results
    
    async def cleanup_old_files(self, hours: Optional[int] = None) -> Dict[str, Any]:
        """Clean up temporary files older than specified hours.
        
        Args:
            hours: Retention period in hours (uses default if not provided)
            
        Returns:
            Dictionary with cleanup statistics
        """
        retention_hours = hours or self.retention_hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=retention_hours)
        
        stats = {
            'files_checked': 0,
            'files_deleted': 0,
            'bytes_freed': 0,
            'errors': 0
        }
        
        # Check all category directories
        for category_dir in [self.output_dir, self.content_dir, self.cache_dir]:
            if not category_dir.exists():
                continue
            
            try:
                for file_path in category_dir.iterdir():
                    if not file_path.is_file():
                        continue
                    
                    stats['files_checked'] += 1
                    
                    try:
                        # Check file modification time
                        mtime = datetime.fromtimestamp(
                            file_path.stat().st_mtime,
                            tz=timezone.utc
                        )
                        
                        if mtime < cutoff:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            stats['files_deleted'] += 1
                            stats['bytes_freed'] += file_size
                            
                            # Remove from registry
                            for file_hash, file_info in list(self.file_registry.items()):
                                if file_info['path'] == str(file_path):
                                    del self.file_registry[file_hash]
                                    break
                    except OSError as e:
                        logger.error(f'Error deleting file {file_path}: {e}')
                        stats['errors'] += 1
            except OSError as e:
                logger.error(f'Error scanning directory {category_dir}: {e}')
                stats['errors'] += 1
        
        logger.info(
            f'Cleanup complete: {stats["files_deleted"]}/{stats["files_checked"]} files, '
            f'{stats["bytes_freed"]} bytes freed'
        )
        return stats
    
    async def cleanup_session(self) -> Dict[str, Any]:
        """Clean up entire session directory.
        
        Returns:
            Dictionary with cleanup statistics
        """
        stats = {
            'session_id': self.session_id,
            'temp_dir': str(self.temp_dir),
            'deleted': False,
            'error': None
        }
        
        if self.temp_dir.exists():
            try:
                # Count files before deletion
                file_count = sum(1 for _ in self.temp_dir.rglob('*') if _.is_file())
                total_size = sum(f.stat().st_size for f in self.temp_dir.rglob('*') if f.is_file())
                
                # Remove entire session directory
                shutil.rmtree(self.temp_dir)
                
                stats['deleted'] = True
                stats['files_deleted'] = file_count
                stats['bytes_freed'] = total_size
                
                logger.info(f'Session cleanup: removed {file_count} files ({total_size} bytes)')
            except OSError as e:
                stats['error'] = str(e)
                logger.error(f'Failed to cleanup session {self.session_id}: {e}')
        
        # Clear registry
        self.file_registry.clear()
        
        return stats
    
    def get_file_info(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get information about a temp file.
        
        Args:
            file_path: Path to file
            
        Returns:
            File metadata dictionary or None if not found
        """
        # Check registry by path
        for file_info in self.file_registry.values():
            if file_info['path'] == str(file_path):
                return file_info
        
        # File not in registry, try to get basic info
        if file_path.exists():
            stat = file_path.stat()
            return {
                'path': str(file_path),
                'filename': file_path.name,
                'size': stat.st_size,
                'created_at': datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat(),
                'modified_at': datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                'category': self._guess_category(file_path)
            }
        
        return None
    
    def _guess_category(self, file_path: Path) -> str:
        """Guess file category based on path.
        
        Args:
            file_path: Path to file
            
        Returns:
            Category string
        """
        path_str = str(file_path)
        if '/output/' in path_str or '\\output\\' in path_str:
            return 'output'
        elif '/content/' in path_str or '\\content\\' in path_str:
            return 'content'
        elif '/cache/' in path_str or '\\cache\\' in path_str:
            return 'cache'
        else:
            return 'unknown'
    
    def get_stats(self) -> Dict[str, Any]:
        """Get temporary file manager statistics.
        
        Returns:
            Statistics dictionary
        """
        total_size = 0
        file_count = len(self.file_registry)
        
        for file_info in self.file_registry.values():
            try:
                path = Path(file_info['path'])
                if path.exists():
                    total_size += path.stat().st_size
            except (OSError, KeyError):
                pass
        
        return {
            'session_id': self.session_id,
            'temp_dir': str(self.temp_dir),
            'file_count': file_count,
            'total_size': total_size,
            'max_file_size': self.max_file_size,
            'retention_hours': self.retention_hours
        }


# Global instance for convenience
_temp_manager: Optional[TempManager] = None


def get_temp_manager(session_id: Optional[str] = None) -> TempManager:
    """Get or create global TempManager instance.
    
    Args:
        session_id: Session identifier
        
    Returns:
        TempManager instance
    """
    global _temp_manager
    if _temp_manager is None or (session_id and _temp_manager.session_id != session_id):
        _temp_manager = TempManager(session_id=session_id)
    return _temp_manager


def cleanup_all_temp_files():
    """Cleanup all temporary files for all sessions.
    
    This is a convenience function for manual cleanup.
    """
    base_dir = TempManager()._get_system_temp_dir() / 'rapidwebs-agent'
    
    if base_dir.exists():
        try:
            shutil.rmtree(base_dir)
            logger.info(f'Cleaned up all temp files: {base_dir}')
        except OSError as e:
            logger.error(f'Failed to cleanup temp files: {e}')
