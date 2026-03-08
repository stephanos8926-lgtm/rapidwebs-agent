"""Tests for EnhancedCodeParser.

Run with: python -m pytest tests/test_code_parser.py -v
"""

import pytest
from agent.code_parser import (
    EnhancedCodeParser, CodeBlock, MergeStrategy, ParseResult,
    parse_and_merge_code
)


class TestCodeBlockExtraction:
    """Test code block extraction from LLM output."""

    def test_extract_markdown_block(self):
        """Test extraction of standard markdown code blocks."""
        parser = EnhancedCodeParser()
        llm_output = """Here's the fixed code:

```python
def hello():
    print("Hello, World!")
```

Hope this helps!"""

        blocks = parser.extract_code_blocks(llm_output, "test.py")
        assert len(blocks) == 1
        assert blocks[0].language == "python"
        assert "def hello():" in blocks[0].content

    def test_extract_full_file_marker(self):
        """Test extraction of full file replacement marker."""
        parser = EnhancedCodeParser()
        llm_output = """<!-- FULL_FILE -->
```python
import os

def main():
    print("Complete file")
```
"""
        blocks = parser.extract_code_blocks(llm_output, "test.py")
        assert len(blocks) == 1
        assert blocks[0].is_full_file
        assert "import os" in blocks[0].content

    def test_extract_range_marker(self):
        """Test extraction of @@ line-range markers."""
        parser = EnhancedCodeParser()
        llm_output = """Replace lines 10-15:

@@ -10,5 @@
```python
def new_function():
    return True
```
"""
        blocks = parser.extract_code_blocks(llm_output, "test.py")
        assert len(blocks) == 1
        assert blocks[0].start_line == 10
        assert blocks[0].end_line == 15
        assert blocks[0].marker_type == "range"

    def test_extract_search_replace_blocks(self):
        """Test extraction of SEARCH/REPLACE blocks."""
        parser = EnhancedCodeParser()
        llm_output = """Here's the change:

```SEARCH
def old_func():
    pass
```

```REPLACE
def new_func():
    return True
```
"""
        blocks = parser.extract_code_blocks(llm_output, "test.py")
        assert len(blocks) == 1
        assert blocks[0].marker_type == "search_replace"
        assert "def old_func" in blocks[0].search_pattern
        assert "def new_func" in blocks[0].replace_pattern


class TestMergeStrategy:
    """Test merge strategy determination."""

    def test_full_file_strategy(self):
        """Test full file replacement strategy."""
        parser = EnhancedCodeParser()
        block = CodeBlock(
            content="complete code",
            is_full_file=True
        )
        strategy = parser.determine_merge_strategy(block, "")
        assert strategy == MergeStrategy.REPLACE_ALL

    def test_range_strategy(self):
        """Test range replacement strategy."""
        parser = EnhancedCodeParser()
        block = CodeBlock(
            content="new code",
            start_line=10,
            end_line=15,
            marker_type="range"
        )
        strategy = parser.determine_merge_strategy(block, "existing code")
        assert strategy == MergeStrategy.REPLACE_RANGE

    def test_symbol_strategy(self):
        """Test symbol replacement strategy."""
        parser = EnhancedCodeParser()
        existing = """
def hello():
    print("hi")
"""
        block = CodeBlock(
            content="def hello():\n    print('Hello!')",
            symbol_name="hello"
        )
        strategy = parser.determine_merge_strategy(block, existing)
        assert strategy == MergeStrategy.REPLACE_SYMBOL

    def test_append_strategy(self):
        """Test append strategy."""
        parser = EnhancedCodeParser()
        block = CodeBlock(
            content="new function",
            is_append=True
        )
        strategy = parser.determine_merge_strategy(block, "existing")
        assert strategy == MergeStrategy.APPEND


class TestMergeOperations:
    """Test code merge operations."""

    def test_merge_append(self):
        """Test appending code to file."""
        parser = EnhancedCodeParser()
        existing = "def existing():\n    pass\n"
        block = CodeBlock(content="def new():\n    pass\n")
        
        result = parser.apply_merge(existing, block, MergeStrategy.APPEND)
        assert "def existing():" in result
        assert "def new():" in result

    def test_merge_replace_all(self):
        """Test full file replacement."""
        parser = EnhancedCodeParser()
        existing = "old code"
        block = CodeBlock(content="new code")
        
        result = parser.apply_merge(existing, block, MergeStrategy.REPLACE_ALL)
        assert result == "new code"

    def test_merge_replace_range(self):
        """Test range replacement."""
        parser = EnhancedCodeParser()
        existing = "line1\nline2\nline3\nline4\nline5"
        block = CodeBlock(
            content="NEW LINE",
            start_line=2,
            end_line=4
        )
        
        result = parser.apply_merge(existing, block, MergeStrategy.REPLACE_RANGE)
        lines = result.split('\n')
        assert lines[0] == "line1"
        assert "NEW" in lines[1]
        assert lines[-1] == "line5"


class TestSyntaxValidation:
    """Test Python syntax validation."""

    def test_valid_syntax(self):
        """Test validation of valid Python code."""
        parser = EnhancedCodeParser()
        code = """
def hello():
    print("Hello")
    return True
"""
        is_valid, errors = parser.validate_python_syntax(code)
        assert is_valid
        assert len(errors) == 0

    def test_invalid_syntax(self):
        """Test detection of syntax errors."""
        parser = EnhancedCodeParser()
        code = """
def broken(:
    print("Missing parameter")
"""
        is_valid, errors = parser.validate_python_syntax(code)
        assert not is_valid
        assert len(errors) > 0
        assert "Syntax error" in errors[0]

    def test_auto_rollback(self):
        """Test automatic rollback on syntax error."""
        parser = EnhancedCodeParser(validate_syntax=True, auto_rollback=True)
        existing = "def existing():\n    pass\n"
        llm_output = "```python\ndef broken(:\n```"
        
        result = parser.parse_and_merge(llm_output, existing, "test.py")
        assert not result.success
        assert result.merged_code == existing  # Rolled back
        assert result.rollback_available


class TestParseAndMerge:
    """Test complete parse and merge workflow."""

    def test_successful_merge(self):
        """Test successful code merge."""
        parser = EnhancedCodeParser()
        existing = """
def hello():
    print("Hello")
"""
        llm_output = """Here's the improved version:

```python
def hello():
    print("Hello, World!")
    return True
```
"""
        result = parser.parse_and_merge(llm_output, existing, "test.py")
        assert result.success
        assert result.blocks_merged >= 1
        assert "Hello, World!" in result.merged_code

    def test_no_code_blocks(self):
        """Test handling of output with no code blocks."""
        parser = EnhancedCodeParser()
        existing = "existing code"
        llm_output = "I don't have any code to share."
        
        result = parser.parse_and_merge(llm_output, existing, "test.py")
        assert not result.success
        assert "No code blocks" in result.error

    def test_convenience_function(self):
        """Test the parse_and_merge_code convenience function."""
        existing = "def old():\n    pass\n"
        llm_output = "```python\ndef new():\n    pass\n```"
        
        result = parse_and_merge_code(llm_output, existing, "test.py")
        # Should succeed (append strategy)
        assert result.success or "new" in result.merged_code


class TestSymbolDetection:
    """Test symbol name detection."""

    def test_detect_function_name(self):
        """Test function name extraction."""
        parser = EnhancedCodeParser()
        code = "def my_function(arg):\n    pass"
        name = parser._extract_symbol_name(code)
        assert name == "my_function"

    def test_detect_class_name(self):
        """Test class name extraction."""
        parser = EnhancedCodeParser()
        code = "class MyClass:\n    pass"
        name = parser._extract_symbol_name(code)
        assert name == "MyClass"

    def test_find_symbol_in_code(self):
        """Test finding symbol in existing code."""
        parser = EnhancedCodeParser()
        code = """
def existing_func():
    pass

class ExistingClass:
    pass
"""
        assert parser._find_symbol_in_code(code, "existing_func")
        assert parser._find_symbol_in_code(code, "ExistingClass")
        assert not parser._find_symbol_in_code(code, "nonexistent")


class TestLanguageDetection:
    """Test language detection from file extension."""

    def test_detect_python(self):
        parser = EnhancedCodeParser()
        assert parser._detect_language("test.py") == "python"

    def test_detect_javascript(self):
        parser = EnhancedCodeParser()
        assert parser._detect_language("test.js") == "javascript"

    def test_detect_typescript(self):
        parser = EnhancedCodeParser()
        assert parser._detect_language("test.ts") == "typescript"

    def test_default_language(self):
        parser = EnhancedCodeParser()
        assert parser._detect_language("") == "python"
        assert parser._detect_language("test.unknown") == "python"
