"""Unit tests for output management system."""

import pytest
import asyncio
import tempfile
from pathlib import Path

from agent.temp_manager import TempManager
from agent.output_manager import OutputManager, OutputResult


@pytest.fixture
def temp_manager():
    """Create a TempManager instance."""
    with tempfile.TemporaryDirectory() as tmpdir:
        manager = TempManager(
            session_id='test_output',
            base_temp_dir=Path(tmpdir)
        )
        yield manager


@pytest.fixture
def output_manager(temp_manager):
    """Create an OutputManager instance."""
    return OutputManager(
        temp_manager=temp_manager,
        inline_max_bytes=1024,  # 1KB for testing
        summary_max_bytes=10240,  # 10KB for testing
        max_inline_lines=20,
        context_lines=10
    )


class TestOutputResult:
    """Tests for OutputResult dataclass."""
    
    def test_output_result_creation(self):
        """Test creating an OutputResult."""
        result = OutputResult(
            original_size=1000,
            display_text="Preview text",
            summary="Summary text",
            routing_decision='summarized'
        )
        
        assert result.original_size == 1000
        assert result.display_text == "Preview text"
        assert result.summary == "Summary text"
        assert result.routing_decision == 'summarized'
    
    def test_output_result_to_dict(self):
        """Test converting OutputResult to dictionary."""
        result = OutputResult(
            original_size=500,
            display_text="Test",
            file_path=Path('/tmp/test.txt')
        )
        
        result_dict = result.to_dict()
        
        assert result_dict['original_size'] == 500
        assert result_dict['display_text'] == "Test"
        assert 'test.txt' in result_dict['file_path']


class TestOutputRouting:
    """Tests for output routing logic."""
    
    @pytest.mark.asyncio
    async def test_route_inline_small_output(self, output_manager):
        """Test that small output is routed inline."""
        small_output = "Small output content"
        
        result = await output_manager.process_output(
            tool_name='terminal',
            output=small_output,
            success=True
        )
        
        assert result.routing_decision == 'inline'
        assert result.file_path is None
        assert result.display_text == small_output
    
    @pytest.mark.asyncio
    async def test_route_summarized_medium_output(self, output_manager):
        """Test that medium output is summarized and stored."""
        # Create output larger than inline threshold but smaller than summary threshold
        medium_output = "Line\n" * 200  # ~1KB
        
        result = await output_manager.process_output(
            tool_name='terminal',
            output=medium_output,
            success=True
        )
        
        assert result.routing_decision == 'summarized'
        assert result.file_path is not None
        assert result.file_path.exists()
        assert result.summary is not None
    
    @pytest.mark.asyncio
    async def test_route_file_only_large_output(self, output_manager):
        """Test that large output is file-only."""
        # Create very large output
        large_output = "X" * 15000  # 15KB, exceeds summary threshold
        
        result = await output_manager.process_output(
            tool_name='terminal',
            output=large_output,
            success=True
        )
        
        assert result.routing_decision == 'file_only'
        assert result.file_path is not None
        assert result.file_path.exists()
        assert 'Large output stored to file' in result.summary


class TestOutputSummarization:
    """Tests for output summarization logic."""
    
    @pytest.mark.asyncio
    async def test_summarize_terminal_output_success(self, output_manager):
        """Test summarizing successful terminal output."""
        output = "\n".join([
            "Compiling project...",
            "Build successful",
            "Tests passed: 50",
            "Tests failed: 0"
        ])
        
        summary = await output_manager._generate_summary(
            output=output,
            tool_name='terminal',
            success=True
        )
        
        assert 'Terminal Output Summary' in summary
        assert 'Success' in summary
    
    @pytest.mark.asyncio
    async def test_summarize_terminal_output_error(self, output_manager):
        """Test summarizing terminal output with errors."""
        output = "\n".join([
            "Compiling project...",
            "Error: Compilation failed",
            "fatal: Unable to resolve reference"
        ])
        
        summary = await output_manager._generate_summary(
            output=output,
            tool_name='terminal',
            success=False
        )
        
        assert 'Terminal Output Summary' in summary
        assert 'Failed' in summary
        assert 'Errors Found' in summary
    
    @pytest.mark.asyncio
    async def test_summarize_search_output(self, output_manager):
        """Test summarizing search results."""
        output = "\n".join([
            "main.py:10: def hello():",
            "main.py:25: hello()",
            "utils.py:5: def helper():",
            "utils.py:15: helper()"
        ])
        
        summary = await output_manager._generate_summary(
            output=output,
            tool_name='search',
            success=True
        )
        
        assert 'Search Results Summary' in summary
        assert 'Matches' in summary
        assert 'Files' in summary
    
    @pytest.mark.asyncio
    async def test_summarize_generic_output(self, output_manager):
        """Test summarizing generic output."""
        output = "\n".join([f"Line {i}" for i in range(100)])
        
        summary = await output_manager._generate_summary(
            output=output,
            tool_name='unknown',
            success=True
        )
        
        assert 'Output Summary' in summary
        assert 'Total Lines' in summary
        assert 'Content Density' in summary


class TestContextPreview:
    """Tests for context preview generation."""
    
    def test_create_context_preview_small(self, output_manager):
        """Test preview with content smaller than context."""
        output = "\n".join([f"Line {i}" for i in range(10)])
        
        preview = output_manager._create_context_preview(output, context_lines=20)
        
        # Should return full content when smaller than context
        assert preview == output
    
    def test_create_context_preview_large(self, output_manager):
        """Test preview with content larger than context."""
        output = "\n".join([f"Line {i}" for i in range(100)])
        
        preview = output_manager._create_context_preview(output, context_lines=10)
        
        lines = preview.splitlines()
        assert len(lines) < 100  # Should be truncated
        assert 'omitted' in preview.lower()
        assert 'Line 0' in preview  # First line
        assert 'Line 99' in preview  # Last line


class TestTokenEstimation:
    """Tests for token count estimation."""
    
    def test_estimate_tokens_english(self, output_manager):
        """Test token estimation for English text."""
        text = "Hello, this is a test of token estimation."
        
        tokens = output_manager._estimate_tokens(text)
        
        # Rough estimate: 1 token ≈ 4 characters
        assert tokens > 0
        assert tokens < len(text)  # Should be less than character count
    
    def test_estimate_tokens_code(self, output_manager):
        """Test token estimation for code."""
        code = """
def hello():
    print("Hello, World!")
    return True
"""
        tokens = output_manager._estimate_tokens(code)
        assert tokens > 0


class TestOutputCleaning:
    """Tests for output cleaning."""
    
    def test_clean_output_ansi_codes(self, output_manager):
        """Test removing ANSI escape codes."""
        output = "\x1b[32mGreen text\x1b[0m\nNormal text"
        
        cleaned = output_manager._clean_output(output, 'terminal')
        
        assert '\x1b[' not in cleaned
        assert 'Green text' in cleaned
        assert 'Normal text' in cleaned
    
    def test_clean_output_excessive_whitespace(self, output_manager):
        """Test removing excessive whitespace."""
        output = "Line 1\n\n\n\nLine 2"
        
        cleaned = output_manager._clean_output(output, 'terminal')
        
        assert '\n\n\n' not in cleaned
        assert 'Line 1' in cleaned
        assert 'Line 2' in cleaned
    
    def test_clean_output_null_bytes(self, output_manager):
        """Test removing null bytes."""
        output = "Text\x00with\x00nulls"
        
        cleaned = output_manager._clean_output(output, 'terminal')
        
        assert '\x00' not in cleaned
        assert 'Textwithnulls' in cleaned


class TestSearchStoredOutput:
    """Tests for searching stored output files."""
    
    @pytest.mark.asyncio
    async def test_search_stored_output(self, output_manager):
        """Test searching within a stored output file."""
        # Create output large enough to be stored
        large_output = "\n".join([
            f"Line {i}: Error: Connection failed" if i % 10 == 0 else f"Line {i}: Info: OK"
            for i in range(200)
        ])
        
        result = await output_manager.process_output(
            tool_name='terminal',
            output=large_output,
            success=True
        )
        
        # Ensure file was created
        assert result.file_path is not None
        
        # Search within stored file
        matches = await output_manager.search_stored_output(
            file_path=result.file_path,
            query='Error'
        )
        
        assert len(matches) > 0
        assert 'Error' in matches[0]['content']


class TestOutputManagerStats:
    """Tests for output manager statistics."""
    
    def test_get_stats(self, output_manager):
        """Test getting output manager statistics."""
        stats = output_manager.get_stats()
        
        assert 'inline_max_bytes' in stats
        assert 'summary_max_bytes' in stats
        assert 'max_inline_lines' in stats
        assert 'temp_manager_stats' in stats


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
