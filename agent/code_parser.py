"""Enhanced code parser with AST-based merging and syntax validation.

This module provides safe code block merging for LLM-generated edits with:
- AST-based symbol matching for safe function/class replacement
- Multiple merge strategies (full file, range, symbol, append)
- Syntax validation before writing (ruff check)
- Rollback on parse errors
- Support for markdown blocks, SEARCH/REPLACE, @@ line-range markers
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

from .logging_config import get_logger

logger = get_logger('code_parser')


class MergeStrategy(Enum):
    """Strategy for merging code blocks."""
    REPLACE_ALL = "replace_all"  # Full file replacement
    REPLACE_RANGE = "replace_range"  # Replace specific line range
    REPLACE_SYMBOL = "replace_symbol"  # Replace function/class by signature
    APPEND = "append"  # Append to end of file
    PREPEND = "prepend"  # Prepend to beginning of file
    REJECT = "reject"  # Reject the change (unclear intent)


@dataclass
class CodeBlock:
    """Represents a code block extracted from LLM output."""
    content: str
    language: str = ""
    start_line: Optional[int] = None  # For @@ range markers
    end_line: Optional[int] = None
    symbol_name: Optional[str] = None  # Function/class name
    symbol_type: Optional[str] = None  # 'function', 'class', etc.
    marker_type: str = "markdown"  # markdown, search_replace, range
    search_pattern: Optional[str] = None  # For SEARCH/REPLACE blocks
    replace_pattern: Optional[str] = None
    is_append: bool = False
    is_full_file: bool = False


@dataclass
class ParseResult:
    """Result of parsing and merging operation."""
    success: bool
    merged_code: str = ""
    error: str = ""
    strategy: MergeStrategy = MergeStrategy.REJECT
    blocks_merged: int = 0
    syntax_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)
    rollback_available: bool = False
    original_code: str = ""


class EnhancedCodeParser:
    """Parse and merge LLM-generated code blocks with AST-based validation.

    Example:
        >>> parser = EnhancedCodeParser()
        >>> result = parser.parse_and_merge(llm_output, existing_code, "example.py")
        >>> if result.success:
        ...     print(f"Merged {result.blocks_merged} blocks")
        ...     print(result.merged_code)
        >>> else:
        ...     print(f"Error: {result.error}")
    """

    def __init__(self, validate_syntax: bool = True, auto_rollback: bool = True):
        """Initialize code parser.

        Args:
            validate_syntax: Run syntax validation after merging
            auto_rollback: Automatically rollback on syntax errors
        """
        self.validate_syntax = validate_syntax
        self.auto_rollback = auto_rollback

    def parse_and_merge(self, llm_output: str, existing_code: str,
                       file_path: str = "") -> ParseResult:
        """Parse LLM output and merge code blocks into existing file.

        Args:
            llm_output: Raw LLM response containing code blocks
            existing_code: Current file content
            file_path: Path to file (for language detection)

        Returns:
            ParseResult with merged code or error information
        """
        result = ParseResult(
            success=False,
            original_code=existing_code,
            rollback_available=self.auto_rollback
        )

        try:
            # Extract code blocks from LLM output
            blocks = self.extract_code_blocks(llm_output, file_path)

            if not blocks:
                result.error = "No code blocks found in LLM output"
                return result

            logger.debug(f"Extracted {len(blocks)} code blocks from LLM output")

            # Start with existing code
            merged_code = existing_code

            # Apply each block with appropriate strategy
            for i, block in enumerate(blocks):
                strategy = self.determine_merge_strategy(block, merged_code)
                logger.debug(f"Block {i+1}: strategy = {strategy.value}")

                if strategy == MergeStrategy.REJECT:
                    result.error = f"Block {i+1}: Unclear merge intent"
                    result.strategy = strategy
                    return result

                merged_code = self.apply_merge(merged_code, block, strategy)

                if merged_code is None:
                    result.error = f"Block {i+1}: Merge failed for strategy {strategy.value}"
                    result.strategy = strategy
                    return result

                result.blocks_merged += 1

            # Validate syntax if enabled
            if self.validate_syntax:
                is_valid, errors = self.validate_python_syntax(merged_code)
                result.syntax_valid = is_valid
                result.validation_errors = errors

                if not is_valid:
                    if self.auto_rollback:
                        result.error = f"Syntax validation failed: {errors[0]}. Rolled back to original."
                        result.merged_code = existing_code
                        result.strategy = strategy
                        return result
                    else:
                        result.error = f"Syntax validation failed: {errors[0]}"
                        result.merged_code = merged_code
                        result.strategy = strategy
                        return result

            result.success = True
            result.merged_code = merged_code
            result.strategy = strategy

            logger.info(f"Successfully merged {result.blocks_merged} code blocks")

        except Exception as e:
            logger.error(f"Parse and merge failed: {e}")
            result.error = str(e)
            if self.auto_rollback:
                result.merged_code = existing_code

        return result

    def extract_code_blocks(self, text: str, file_path: str = "") -> List[CodeBlock]:
        """Extract code blocks from LLM output.

        Supports multiple formats:
        1. Markdown fenced blocks: ```python ... ```
        2. SEARCH/REPLACE blocks
        3. @@ line-range markers: @@ -10,+5 @@
        4. Full file markers: <!-- FULL_FILE -->

        Args:
            text: LLM output text
            file_path: Source file path (for language detection)

        Returns:
            List of extracted CodeBlock objects
        """
        blocks = []

        # Check for full file replacement marker
        if '<!-- FULL_FILE -->' in text or '```FULL_FILE' in text:
            block = self._extract_full_file(text, file_path)
            if block:
                blocks.append(block)
                return blocks

        # Extract SEARCH/REPLACE blocks
        search_replace_blocks = self._extract_search_replace_blocks(text)
        blocks.extend(search_replace_blocks)

        # Extract @@ range marker blocks
        range_blocks = self._extract_range_blocks(text, file_path)
        blocks.extend(range_blocks)

        # Extract standard markdown code blocks (if no other blocks found)
        if not blocks:
            markdown_blocks = self._extract_markdown_blocks(text, file_path)
            blocks.extend(markdown_blocks)

        return blocks

    def _extract_markdown_blocks(self, text: str, file_path: str) -> List[CodeBlock]:
        """Extract standard markdown fenced code blocks."""
        blocks = []
        language = self._detect_language(file_path)

        # Pattern for fenced code blocks
        pattern = r'```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        for lang, content in matches:
            block = CodeBlock(
                content=content.strip(),
                language=lang or language,
                marker_type="markdown"
            )
            blocks.append(block)

        return blocks

    def _extract_search_replace_blocks(self, text: str) -> List[CodeBlock]:
        """Extract SEARCH/REPLACE style blocks.

        Format:
        ```SEARCH
        def old_function():
            pass
        ```

        ```REPLACE
        def new_function():
            return True
        ```
        """
        blocks = []

        # Find SEARCH/REPLACE pairs
        search_pattern = r'```SEARCH\n(.*?)```'
        replace_pattern = r'```REPLACE\n(.*?)```'

        searches = re.findall(search_pattern, text, re.DOTALL)
        replaces = re.findall(replace_pattern, text, re.DOTALL)

        # Pair them up
        for i, search in enumerate(searches):
            replace = replaces[i] if i < len(replaces) else ""
            block = CodeBlock(
                content=replace.strip(),
                search_pattern=search.strip(),
                replace_pattern=replace.strip(),
                marker_type="search_replace",
                symbol_name=self._extract_symbol_name(search.strip())
            )
            blocks.append(block)

        return blocks

    def _extract_range_blocks(self, text: str, file_path: str) -> List[CodeBlock]:
        """Extract @@ line-range marker blocks.

        Format:
        @@ -10,5 @@
        ```python
        new code here
        ```
        """
        blocks = []
        language = self._detect_language(file_path)

        # Pattern for @@ markers followed by code block
        pattern = r'@@\s*-(\d+)(?:,(\d+))?\s*@@\s*```(\w+)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)

        for start, count, lang, content in matches:
            start_line = int(start)
            end_line = start_line + (int(count) if count else 1)

            block = CodeBlock(
                content=content.strip(),
                language=lang or language,
                start_line=start_line,
                end_line=end_line,
                marker_type="range"
            )
            blocks.append(block)

        return blocks

    def _extract_full_file(self, text: str, file_path: str) -> Optional[CodeBlock]:
        """Extract full file replacement block."""
        language = self._detect_language(file_path)

        # Try different full file markers
        patterns = [
            r'<!-- FULL_FILE -->\s*```(\w+)?\n(.*?)```',
            r'```FULL_FILE\s*(\w+)?\n(.*?)```',
            r'```(\w+)?\n(.*?)```\s*<!-- END_FILE -->',
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL)
            if match:
                lang, content = match.groups()
                return CodeBlock(
                    content=content.strip(),
                    language=lang or language,
                    marker_type="markdown",
                    is_full_file=True
                )

        return None

    def _extract_symbol_name(self, code: str) -> Optional[str]:
        """Extract function or class name from code snippet."""
        # Try to parse as Python AST
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    return node.name
        except SyntaxError:
            pass

        # Fallback: regex for common patterns
        patterns = [
            r'def\s+(\w+)\s*\(',  # Function
            r'class\s+(\w+)',  # Class
        ]

        for pattern in patterns:
            match = re.search(pattern, code)
            if match:
                return match.group(1)

        return None

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension."""
        if not file_path:
            return "python"

        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
        }

        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'python')

    def determine_merge_strategy(self, block: CodeBlock,
                                existing_code: str) -> MergeStrategy:
        """Determine the appropriate merge strategy for a code block.

        Args:
            block: Code block to merge
            existing_code: Current file content

        Returns:
            Appropriate MergeStrategy
        """
        # Check for explicit markers first
        if block.is_full_file:
            return MergeStrategy.REPLACE_ALL

        if block.marker_type == "range" and block.start_line is not None:
            return MergeStrategy.REPLACE_RANGE

        if block.marker_type == "search_replace":
            return MergeStrategy.REPLACE_SYMBOL

        # Check for append marker
        if block.is_append or 'APPEND' in block.content.upper():
            return MergeStrategy.APPEND

        # Try to match symbol in existing code
        if block.symbol_name:
            if self._find_symbol_in_code(existing_code, block.symbol_name):
                return MergeStrategy.REPLACE_SYMBOL

        # Check if block looks like complete file
        if self._looks_like_complete_file(block.content):
            return MergeStrategy.REPLACE_ALL

        # Default to append for unclear cases
        return MergeStrategy.APPEND

    def _find_symbol_in_code(self, code: str, symbol_name: str) -> bool:
        """Check if a symbol (function/class) exists in code."""
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == symbol_name:
                        return True
        except SyntaxError:
            # Fallback to regex
            pattern = rf'(def|class)\s+{re.escape(symbol_name)}\s*[\(:]'
            return bool(re.search(pattern, code))

        return False

    def _looks_like_complete_file(self, content: str) -> bool:
        """Check if content looks like a complete file."""
        # Check for common file-level patterns
        indicators = [
            r'^import\s+\w+',  # Import at start
            r'^from\s+\w+\s+import',  # From import
            r'^class\s+\w+',  # Class definition
            r'^def\s+\w+',  # Function at module level
            r'^if\s+__name__',  # Main guard
            r'#!/usr/bin/env',  # Shebang
            r'^"""',  # Module docstring
            r"^'''",  # Module docstring
        ]

        matches = sum(1 for pattern in indicators if re.search(pattern, content, re.MULTILINE))
        return matches >= 2  # At least 2 indicators suggest complete file

    def apply_merge(self, existing_code: str, block: CodeBlock,
                   strategy: MergeStrategy) -> Optional[str]:
        """Apply a merge strategy to integrate a code block.

        Args:
            existing_code: Current file content
            block: Code block to merge
            strategy: Merge strategy to use

        Returns:
            Merged code, or None if merge failed
        """
        if strategy == MergeStrategy.REPLACE_ALL:
            return block.content

        elif strategy == MergeStrategy.REPLACE_RANGE:
            return self._merge_range(existing_code, block)

        elif strategy == MergeStrategy.REPLACE_SYMBOL:
            return self._merge_symbol(existing_code, block)

        elif strategy == MergeStrategy.APPEND:
            return self._merge_append(existing_code, block)

        elif strategy == MergeStrategy.PREPEND:
            return self._merge_prepend(existing_code, block)

        return None

    def _merge_range(self, code: str, block: CodeBlock) -> Optional[str]:
        """Replace code at specific line range."""
        if block.start_line is None:
            return None

        lines = code.split('\n')
        start_idx = block.start_line - 1  # Convert to 0-indexed
        end_idx = block.end_line if block.end_line else start_idx + 1

        # Ensure indices are valid
        start_idx = max(0, min(start_idx, len(lines)))
        end_idx = max(start_idx, min(end_idx, len(lines)))

        # Replace the range
        new_lines = lines[:start_idx] + block.content.split('\n') + lines[end_idx:]
        return '\n'.join(new_lines)

    def _merge_symbol(self, code: str, block: CodeBlock) -> str:
        """Replace a function or class by symbol name."""
        try:
            existing_tree = ast.parse(code)
            symbol_name = block.symbol_name or self._extract_symbol_name(block.content)

            if not symbol_name:
                # No symbol found, fall back to append
                return self._merge_append(code, block)

            # Find the symbol in existing code
            symbol_node = None
            for node in ast.walk(existing_tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    if node.name == symbol_name:
                        symbol_node = node
                        break

            if symbol_node is None:
                # Symbol not found, append new code
                return self._merge_append(code, block)

            # Get line numbers of existing symbol
            start_line = symbol_node.lineno - 1  # 0-indexed
            end_line = getattr(symbol_node, 'end_lineno', start_line + 1)

            # Replace the symbol
            lines = code.split('\n')
            new_lines = lines[:start_line] + block.content.split('\n') + lines[end_line:]
            return '\n'.join(new_lines)

        except SyntaxError:
            # Can't parse existing code, fall back to append
            return self._merge_append(code, block)

    def _merge_append(self, code: str, block: CodeBlock) -> str:
        """Append code block to end of file."""
        # Ensure there's a newline between existing and new code
        if code and not code.endswith('\n'):
            code += '\n\n'
        elif code and code.endswith('\n') and not code.endswith('\n\n'):
            code += '\n'

        return code + block.content

    def _merge_prepend(self, code: str, block: CodeBlock) -> str:
        """Prepend code block to beginning of file."""
        # Ensure there's a newline between new and existing code
        new_content = block.content
        if not new_content.endswith('\n'):
            new_content += '\n\n'
        elif not new_content.endswith('\n\n'):
            new_content += '\n'

        return new_content + code

    def validate_python_syntax(self, code: str) -> Tuple[bool, List[str]]:
        """Validate Python syntax using AST parsing and ruff.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # First, check basic Python syntax with AST
        try:
            ast.parse(code)
        except SyntaxError as e:
            errors.append(f"Syntax error: {e.msg} at line {e.lineno}")
            return False, errors

        # Then, check with ruff if available
        try:
            from .code_analysis_tools import RuffLinter
            linter = RuffLinter()
            result = linter.lint_code(code)

            if result.get('errors'):
                for error in result['errors']:
                    errors.append(f"Ruff: {error.get('message', error)}")

            # Consider syntax-only errors as fatal
            syntax_errors = [e for e in result.get('errors', [])
                           if e.get('code') == 'E999']
            if syntax_errors:
                return False, [f"Ruff syntax error: {syntax_errors[0]}"]

        except ImportError:
            logger.debug("Ruff not available, skipping advanced linting")
        except Exception as e:
            logger.debug(f"Ruff check failed: {e}")

        return len(errors) == 0, errors


def parse_and_merge_code(llm_output: str, existing_code: str,
                        file_path: str = "", **kwargs) -> ParseResult:
    """Convenience function for parsing and merging code.

    Args:
        llm_output: LLM response containing code blocks
        existing_code: Current file content
        file_path: Source file path
        **kwargs: Additional arguments for EnhancedCodeParser

    Returns:
        ParseResult with merged code or error
    """
    parser = EnhancedCodeParser(**kwargs)
    return parser.parse_and_merge(llm_output, existing_code, file_path)
