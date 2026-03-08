"""Unit tests for temporary file management system."""

import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta

from agent.temp_manager import TempManager, get_temp_manager, cleanup_all_temp_files


@pytest.fixture
def temp_manager():
    """Create a TempManager instance with temporary directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TempManager(
            session_id='test_session',
            base_temp_dir=Path(tmpdir)
        )
        yield manager


@pytest.fixture
def sample_content():
    """Sample content for testing."""
    return "Hello, World!\n" * 100


class TestTempManagerInit:
    """Tests for TempManager initialization."""
    
    def test_init_creates_directories(self, temp_manager):
        """Test that initialization creates required directories."""
        assert temp_manager.temp_dir.exists()
        assert temp_manager.content_dir.exists()
        assert temp_manager.output_dir.exists()
        assert temp_manager.cache_dir.exists()
    
    def test_init_generates_session_id(self):
        """Test that session ID is generated if not provided."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = TempManager(base_temp_dir=Path(tmpdir))
            assert manager.session_id is not None
            assert len(manager.session_id) > 0
    
    def test_init_custom_session_id(self, temp_manager):
        """Test that custom session ID is used."""
        assert temp_manager.session_id == 'test_session'


class TestTempFileCreation:
    """Tests for temporary file creation."""
    
    @pytest.mark.asyncio
    async def test_create_temp_file(self, temp_manager, sample_content):
        """Test creating a temporary file."""
        file_path = await temp_manager.create_temp_file(
            filename='test.txt',
            content=sample_content,
            category='output'
        )
        
        assert file_path.exists()
        assert file_path.is_file()
        
        # Verify content
        content = await temp_manager.read_temp_file(file_path)
        assert content == sample_content
    
    @pytest.mark.asyncio
    async def test_create_temp_file_deduplication(self, temp_manager, sample_content):
        """Test that identical content is deduplicated."""
        file_path1 = await temp_manager.create_temp_file(
            filename='test1.txt',
            content=sample_content,
            category='output'
        )
        
        file_path2 = await temp_manager.create_temp_file(
            filename='test2.txt',
            content=sample_content,
            category='output'
        )
        
        # Should return the same file for identical content
        assert file_path1 == file_path2
    
    @pytest.mark.asyncio
    async def test_create_temp_file_exceeds_max_size(self, temp_manager):
        """Test that large content raises ValueError."""
        large_content = "X" * (temp_manager.max_file_size + 1)
        
        with pytest.raises(ValueError, match="exceeds max file size"):
            await temp_manager.create_temp_file(
                filename='large.txt',
                content=large_content
            )
    
    @pytest.mark.asyncio
    async def test_create_temp_file_different_categories(self, temp_manager):
        """Test creating files in different categories."""
        output_file = await temp_manager.create_temp_file(
            filename='output.txt',
            content='output content',
            category='output'
        )
        
        content_file = await temp_manager.create_temp_file(
            filename='content.txt',
            content='content content',
            category='content'
        )
        
        cache_file = await temp_manager.create_temp_file(
            filename='cache.txt',
            content='cache content',
            category='cache'
        )
        
        assert 'output' in str(output_file)
        assert 'content' in str(content_file)
        assert 'cache' in str(cache_file)


class TestTempFileRead:
    """Tests for temporary file reading."""
    
    @pytest.mark.asyncio
    async def test_read_temp_file(self, temp_manager, sample_content):
        """Test reading a temporary file."""
        file_path = await temp_manager.create_temp_file(
            filename='test.txt',
            content=sample_content,
            category='output'
        )
        
        content = await temp_manager.read_temp_file(file_path)
        assert content == sample_content
    
    @pytest.mark.asyncio
    async def test_read_temp_file_line_range(self, temp_manager):
        """Test reading a file with line range."""
        content = "\n".join([f"Line {i}" for i in range(1, 101)])
        file_path = await temp_manager.create_temp_file(
            filename='lines.txt',
            content=content,
            category='output'
        )
        
        # Read lines 10-20
        subset = await temp_manager.read_temp_file(
            file_path,
            start_line=10,
            end_line=20
        )
        
        lines = subset.splitlines()
        assert len(lines) == 11  # 10-20 inclusive
        assert lines[0] == "Line 10"
        assert lines[-1] == "Line 20"
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_manager):
        """Test reading a non-existent file raises FileNotFoundError."""
        fake_path = Path('/fake/path/file.txt')
        
        with pytest.raises(FileNotFoundError):
            await temp_manager.read_temp_file(fake_path)


class TestFileSearch:
    """Tests for file search functionality."""
    
    @pytest.mark.asyncio
    async def test_search_file_pattern(self, temp_manager):
        """Test searching for a pattern in a file."""
        content = """
        def hello():
            print("Hello, World!")
        
        def goodbye():
            print("Goodbye, World!")
        """
        file_path = await temp_manager.create_temp_file(
            filename='code.py',
            content=content,
            category='output'
        )
        
        matches = await temp_manager.search_file(
            file_path,
            pattern=r'def \w+\(\):'
        )
        
        assert len(matches) == 2
        assert 'hello' in matches[0]['content']
        assert 'goodbye' in matches[1]['content']
    
    @pytest.mark.asyncio
    async def test_grep_file_simple(self, temp_manager):
        """Test simple grep search."""
        content = "\n".join([
            "Error: Something failed",
            "Info: All good",
            "Error: Another failure",
            "Success: Done"
        ])
        file_path = await temp_manager.create_temp_file(
            filename='log.txt',
            content=content,
            category='output'
        )
        
        results = await temp_manager.grep_file(
            file_path,
            query='Error'
        )
        
        assert len(results) == 2
        assert 'Error' in results[0]['content']
    
    @pytest.mark.asyncio
    async def test_grep_file_case_sensitive(self, temp_manager):
        """Test case-sensitive grep."""
        content = "error\nError\nERROR"
        file_path = await temp_manager.create_temp_file(
            filename='case.txt',
            content=content,
            category='output'
        )
        
        # Case sensitive
        results = await temp_manager.grep_file(
            file_path,
            query='Error',
            case_sensitive=True
        )
        assert len(results) == 1
        assert results[0]['content'] == 'Error'
        
        # Case insensitive
        results = await temp_manager.grep_file(
            file_path,
            query='Error',
            case_sensitive=False
        )
        assert len(results) == 3


class TestCleanup:
    """Tests for cleanup functionality."""
    
    @pytest.mark.asyncio
    async def test_cleanup_old_files(self, temp_manager):
        """Test cleaning up old files."""
        # Create a file
        file_path = await temp_manager.create_temp_file(
            filename='test.txt',
            content='test content',
            category='output'
        )
        
        # Manually set old modification time
        old_time = (datetime.now(timezone.utc) - timedelta(hours=25)).timestamp()
        Path(file_path).touch()
        import os
        os.utime(file_path, (old_time, old_time))
        
        # Cleanup files older than 24 hours
        stats = await temp_manager.cleanup_old_files(hours=24)
        
        assert stats['files_deleted'] >= 1
        assert not file_path.exists()
    
    @pytest.mark.asyncio
    async def test_cleanup_session(self, temp_manager):
        """Test cleaning up entire session."""
        # Create some files
        await temp_manager.create_temp_file(
            filename='test1.txt',
            content='content1',
            category='output'
        )
        await temp_manager.create_temp_file(
            filename='test2.txt',
            content='content2',
            category='content'
        )
        
        # Cleanup session
        stats = await temp_manager.cleanup_session()
        
        assert stats['deleted'] is True
        assert not temp_manager.temp_dir.exists()
        assert len(temp_manager.file_registry) == 0
    
    @pytest.mark.asyncio
    async def test_get_stats(self, temp_manager, sample_content):
        """Test getting statistics."""
        await temp_manager.create_temp_file(
            filename='test.txt',
            content=sample_content,
            category='output'
        )
        
        stats = temp_manager.get_stats()
        
        assert stats['session_id'] == 'test_session'
        assert stats['file_count'] == 1
        assert stats['total_size'] > 0


class TestGlobalManager:
    """Tests for global TempManager instance."""
    
    def test_get_temp_manager_singleton(self):
        """Test that get_temp_manager returns singleton."""
        manager1 = get_temp_manager('test1')
        manager2 = get_temp_manager('test1')
        
        assert manager1 is manager2
    
    def test_get_temp_manager_different_session(self):
        """Test that different session IDs create different managers."""
        manager1 = get_temp_manager('session1')
        manager2 = get_temp_manager('session2')
        
        assert manager1.session_id != manager2.session_id


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
