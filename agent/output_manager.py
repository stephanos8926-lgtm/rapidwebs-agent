"""Output management for RapidWebs Agent.

This module provides intelligent output handling with:
- Threshold-based routing (inline vs. summarized vs. file-only)
- Smart summarization for large outputs
- Token-efficient context injection
- Transparent file-based storage for large tool outputs

Example:
    output_mgr = OutputManager(temp_manager)
    
    # Process tool output
    result = await output_mgr.process_output(
        tool_name='terminal',
        output=large_command_output,
        success=True
    )
    
    # result contains:
    # - display_text: Short preview for UI
    # - summary: Intelligent summary if output was large
    # - file_path: Path to full output if stored
    # - token_count: Estimated token usage
"""

import asyncio
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime, timezone
import re

from .logging_config import get_logger
from .temp_manager import TempManager

logger = get_logger('output_manager')


@dataclass
class OutputResult:
    """Result of output processing.
    
    Attributes:
        original_size: Original output size in bytes
        display_text: Text suitable for inline display
        summary: Intelligent summary (if output was large)
        file_path: Path to full output file (if stored)
        token_count: Estimated token count for context
        routing_decision: How the output was handled
        metadata: Additional metadata
    """
    original_size: int
    display_text: str
    summary: Optional[str] = None
    file_path: Optional[Path] = None
    token_count: int = 0
    routing_decision: str = 'inline'
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'original_size': self.original_size,
            'display_text': self.display_text,
            'summary': self.summary,
            'file_path': str(self.file_path) if self.file_path else None,
            'token_count': self.token_count,
            'routing_decision': self.routing_decision,
            'metadata': self.metadata
        }


class OutputManager:
    """Manage tool output routing and summarization.
    
    Attributes:
        temp_manager: Temporary file manager instance
        inline_max_bytes: Maximum bytes for inline display
        summary_max_bytes: Maximum bytes before file-only storage
        max_inline_lines: Maximum lines for inline display
        context_lines: Lines to keep from start/end when summarizing
        enable_summarization: Whether to enable smart summarization
    """
    
    def __init__(
        self,
        temp_manager: TempManager,
        inline_max_bytes: int = 10 * 1024,  # 10KB
        summary_max_bytes: int = 1024 * 1024,  # 1MB
        max_inline_lines: int = 50,
        context_lines: int = 50,
        enable_summarization: bool = True
    ):
        """Initialize output manager.
        
        Args:
            temp_manager: Temporary file manager instance
            inline_max_bytes: Maximum bytes for inline display
            summary_max_bytes: Maximum bytes before file-only storage
            max_inline_lines: Maximum lines for inline display
            context_lines: Lines to keep from start/end when summarizing
            enable_summarization: Whether to enable smart summarization
        """
        self.temp_manager = temp_manager
        self.inline_max_bytes = inline_max_bytes
        self.summary_max_bytes = summary_max_bytes
        self.max_inline_lines = max_inline_lines
        self.context_lines = context_lines
        self.enable_summarization = enable_summarization
        
        logger.info(
            f'OutputManager initialized: inline={inline_max_bytes}B, '
            f'summary={summary_max_bytes}B, max_lines={max_inline_lines}'
        )
    
    async def process_output(
        self,
        tool_name: str,
        output: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> OutputResult:
        """Process tool output with intelligent routing.
        
        Args:
            tool_name: Name of the tool that produced the output
            output: Raw output content
            success: Whether the tool execution was successful
            metadata: Optional additional metadata
            
        Returns:
            OutputResult with routing decision and processed content
        """
        output_bytes = len(output.encode('utf-8'))
        output_lines = output.count('\n') + 1
        
        logger.debug(
            f'Processing output from {tool_name}: {output_bytes}B, {output_lines} lines'
        )
        
        # Determine routing strategy
        if output_bytes <= self.inline_max_bytes and output_lines <= self.max_inline_lines:
            # Small output: display inline
            return await self._route_inline(tool_name, output, success, metadata)
        
        elif output_bytes <= self.summary_max_bytes:
            # Medium output: summarize and store
            return await self._route_summarized(tool_name, output, success, metadata)
        
        else:
            # Large output: file-only with minimal summary
            return await self._route_file_only(tool_name, output, success, metadata)
    
    async def _route_inline(
        self,
        tool_name: str,
        output: str,
        success: bool,
        metadata: Optional[Dict[str, Any]]
    ) -> OutputResult:
        """Route small output for inline display.
        
        Args:
            tool_name: Tool name
            output: Raw output
            success: Execution success status
            metadata: Additional metadata
            
        Returns:
            OutputResult with inline display text
        """
        # Clean up output for display
        display_text = self._clean_output(output, tool_name)
        token_count = self._estimate_tokens(display_text)
        
        result = OutputResult(
            original_size=len(output.encode('utf-8')),
            display_text=display_text,
            token_count=token_count,
            routing_decision='inline',
            metadata={
                'tool': tool_name,
                'success': success,
                'lines': output.count('\n') + 1,
                **(metadata or {})
            }
        )
        
        logger.debug(f'Output routed inline: {result.original_size}B')
        return result
    
    async def _route_summarized(
        self,
        tool_name: str,
        output: str,
        success: bool,
        metadata: Optional[Dict[str, Any]]
    ) -> OutputResult:
        """Route medium output with summarization and file storage.
        
        Args:
            tool_name: Tool name
            output: Raw output
            success: Execution success status
            metadata: Additional metadata
            
        Returns:
            OutputResult with summary and file reference
        """
        # Store full output
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{tool_name}_output_{timestamp}.txt'
        
        try:
            file_path = await self.temp_manager.create_temp_file(
                filename=filename,
                content=output,
                category='output',
                metadata={
                    'tool': tool_name,
                    'success': success,
                    'timestamp': timestamp,
                    **(metadata or {})
                }
            )
        except Exception as e:
            logger.error(f'Failed to store output file: {e}')
            # Fallback to inline with truncation
            return await self._route_inline(tool_name, output[:self.inline_max_bytes], success, metadata)
        
        # Generate summary
        summary = await self._generate_summary(output, tool_name, success)
        
        # Create display text (first + last context lines)
        display_text = self._create_context_preview(output, self.context_lines)
        
        token_count = self._estimate_tokens(summary + display_text)
        
        result = OutputResult(
            original_size=len(output.encode('utf-8')),
            display_text=display_text,
            summary=summary,
            file_path=file_path,
            token_count=token_count,
            routing_decision='summarized',
            metadata={
                'tool': tool_name,
                'success': success,
                'lines': output.count('\n') + 1,
                'file_stored': True,
                **(metadata or {})
            }
        )
        
        logger.info(
            f'Output routed summarized: {result.original_size}B -> '
            f'{len(summary)}B summary + {file_path}'
        )
        return result
    
    async def _route_file_only(
        self,
        tool_name: str,
        output: str,
        success: bool,
        metadata: Optional[Dict[str, Any]]
    ) -> OutputResult:
        """Route large output to file-only storage.
        
        Args:
            tool_name: Tool name
            output: Raw output
            success: Execution success status
            metadata: Additional metadata
            
        Returns:
            OutputResult with file reference only
        """
        # Store full output
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{tool_name}_output_{timestamp}.txt'
        
        try:
            file_path = await self.temp_manager.create_temp_file(
                filename=filename,
                content=output,
                category='output',
                metadata={
                    'tool': tool_name,
                    'success': success,
                    'timestamp': timestamp,
                    'large_output': True,
                    **(metadata or {})
                }
            )
        except Exception as e:
            logger.error(f'Failed to store large output file: {e}')
            # Fallback to truncated inline
            truncated = output[:self.inline_max_bytes] + '\n\n[... output truncated due to error ...]'
            return await self._route_inline(tool_name, truncated, success, metadata)
        
        # Minimal summary
        lines = output.splitlines()
        summary = (
            f"📄 Large output stored to file\n\n"
            f"**Tool:** {tool_name}\n"
            f"**Size:** {len(output.encode('utf-8')):,} bytes\n"
            f"**Lines:** {len(lines):,}\n"
            f"**Status:** {'Success' if success else 'Failed'}\n\n"
            f"Use `grep` or `search` to find specific content in the output file."
        )
        
        # Very brief preview
        display_text = f"[Large output: {len(lines)} lines, {len(output.encode('utf-8')):,} bytes]"
        
        token_count = self._estimate_tokens(summary)
        
        result = OutputResult(
            original_size=len(output.encode('utf-8')),
            display_text=display_text,
            summary=summary,
            file_path=file_path,
            token_count=token_count,
            routing_decision='file_only',
            metadata={
                'tool': tool_name,
                'success': success,
                'lines': len(lines),
                'file_stored': True,
                'large_output': True,
                **(metadata or {})
            }
        )
        
        logger.info(
            f'Output routed file-only: {result.original_size}B -> {file_path}'
        )
        return result
    
    def _clean_output(self, output: str, tool_name: str) -> str:
        """Clean output for display.
        
        Args:
            output: Raw output
            tool_name: Tool that produced output
            
        Returns:
            Cleaned output string
        """
        # Remove excessive whitespace
        output = re.sub(r'\n{3,}', '\n\n', output)
        output = output.rstrip()
        
        # Remove ANSI escape codes (terminal colors)
        output = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', output)
        
        # Remove null bytes
        output = output.replace('\x00', '')
        
        # Truncate if still too long for display
        lines = output.splitlines()
        if len(lines) > self.max_inline_lines:
            half = self.max_inline_lines // 2
            lines = lines[:half] + [f'\n[... {len(lines) - self.max_inline_lines} lines omitted ...]\n'] + lines[-half:]
            output = '\n'.join(lines)
        
        return output
    
    async def _generate_summary(
        self,
        output: str,
        tool_name: str,
        success: bool
    ) -> str:
        """Generate intelligent summary of output.
        
        Args:
            output: Raw output
            tool_name: Tool that produced output
            success: Execution success status
            
        Returns:
            Summary string
        """
        if not self.enable_summarization:
            return output[:500] + '...' if len(output) > 500 else output
        
        lines = output.splitlines()
        total_lines = len(lines)
        
        # Tool-specific summarization
        if tool_name == 'terminal':
            return self._summarize_terminal_output(lines, success)
        elif tool_name == 'fs':
            return self._summarize_filesystem_output(lines, success)
        elif tool_name == 'search':
            return self._summarize_search_output(lines, success)
        elif tool_name == 'subagents':
            return self._summarize_subagents_output(lines, success)
        else:
            return self._summarize_generic_output(lines, success)
    
    def _summarize_terminal_output(
        self,
        lines: List[str],
        success: bool
    ) -> str:
        """Summarize terminal command output.
        
        Args:
            lines: Output lines
            success: Command success status
            
        Returns:
            Summary string
        """
        total_lines = len(lines)
        
        # Extract key information
        status = '✅ Success' if success else '❌ Failed'
        
        # Look for error patterns
        error_patterns = [
            r'error:', r'Error:', r'ERROR', r'failed:', r'Failed:',
            r'exception:', r'Exception:', r'Traceback', r'fatal:'
        ]
        
        errors_found = []
        for line in lines:
            for pattern in error_patterns:
                if re.search(pattern, line):
                    errors_found.append(line.strip()[:100])
                    break
        
        # Look for output patterns
        output_indicators = [
            r'^(\d+)',  # Lines starting with numbers
            r'^[A-Z]',  # Lines starting with capital letters
            r'[:=]',    # Lines with colons or equals (key-value)
        ]
        
        content_lines = sum(1 for line in lines if any(re.search(p, line) for p in output_indicators))
        
        summary_parts = [
            f"📟 Terminal Output Summary",
            f"",
            f"**Status:** {status}",
            f"**Total Lines:** {total_lines}",
            f"**Content Lines:** {content_lines}",
        ]
        
        if errors_found:
            summary_parts.append(f"**Errors Found:** {len(errors_found)}")
            summary_parts.append("")
            summary_parts.append("Key errors:")
            for error in errors_found[:3]:
                summary_parts.append(f"- {error}")
        
        summary_parts.append("")
        summary_parts.append("Use `grep` to search the full output file for specific content.")
        
        return '\n'.join(summary_parts)
    
    def _summarize_filesystem_output(
        self,
        lines: List[str],
        success: bool
    ) -> str:
        """Summarize filesystem operation output.
        
        Args:
            lines: Output lines
            success: Operation success status
            
        Returns:
            Summary string
        """
        status = '✅ Success' if success else '❌ Failed'
        
        # Look for file/directory counts
        file_count = sum(1 for line in lines if 'file' in line.lower())
        dir_count = sum(1 for line in lines if 'director' in line.lower())
        
        summary = (
            f"📁 Filesystem Operation Summary\n\n"
            f"**Status:** {status}\n"
            f"**Lines:** {len(lines)}\n"
        )
        
        if file_count or dir_count:
            summary += f"**Files mentioned:** {file_count}\n"
            summary += f"**Directories mentioned:** {dir_count}\n"
        
        return summary
    
    def _summarize_search_output(
        self,
        lines: List[str],
        success: bool
    ) -> str:
        """Summarize search operation output.
        
        Args:
            lines: Output lines
            success: Operation success status
            
        Returns:
            Summary string
        """
        status = '✅ Success' if success else '❌ Failed'
        
        # Count matches (lines that look like file:line patterns)
        match_pattern = r'^[^:]+:\d+:'
        matches = sum(1 for line in lines if re.match(match_pattern, line))
        
        # Count unique files
        files = set()
        for line in lines:
            match = re.match(r'^([^:]+):\d+:', line)
            if match:
                files.add(match.group(1))
        
        summary = (
            f"🔍 Search Results Summary\n\n"
            f"**Status:** {status}\n"
            f"**Total Matches:** {matches}\n"
            f"**Unique Files:** {len(files)}\n"
        )
        
        if files:
            summary += "\n**Files with matches:**\n"
            for file in list(files)[:10]:
                summary += f"- {file}\n"
            if len(files) > 10:
                summary += f"- ... and {len(files) - 10} more\n"
        
        return summary
    
    def _summarize_subagents_output(
        self,
        lines: List[str],
        success: bool
    ) -> str:
        """Summarize subagents operation output.
        
        Args:
            lines: Output lines
            success: Operation success status
            
        Returns:
            Summary string
        """
        status = '✅ Success' if success else '❌ Failed'
        
        # Look for task completion markers
        task_pattern = r'(task|agent|subagent).*?(complete|finish|done|success)'
        tasks_completed = sum(1 for line in lines if re.search(task_pattern, line, re.IGNORECASE))
        
        # Look for error markers
        error_pattern = r'(error|fail|exception)'
        errors = sum(1 for line in lines if re.search(error_pattern, line, re.IGNORECASE))
        
        summary = (
            f"🤖 SubAgents Execution Summary\n\n"
            f"**Status:** {status}\n"
            f"**Output Lines:** {len(lines)}\n"
            f"**Task Completions:** {tasks_completed}\n"
            f"**Error Mentions:** {errors}\n"
        )
        
        return summary
    
    def _summarize_generic_output(
        self,
        lines: List[str],
        success: bool
    ) -> str:
        """Summarize generic output.
        
        Args:
            lines: Output lines
            success: Operation success status
            
        Returns:
            Summary string
        """
        status = '✅ Success' if success else '❌ Failed'
        total_lines = len(lines)
        
        # Estimate content density
        non_empty = sum(1 for line in lines if line.strip())
        density = (non_empty / total_lines * 100) if total_lines > 0 else 0
        
        summary = (
            f"📄 Output Summary\n\n"
            f"**Status:** {status}\n"
            f"**Total Lines:** {total_lines}\n"
            f"**Non-empty Lines:** {non_empty}\n"
            f"**Content Density:** {density:.0f}%\n"
        )
        
        return summary
    
    def _create_context_preview(
        self,
        output: str,
        context_lines: int
    ) -> str:
        """Create preview with first and last context lines.
        
        Args:
            output: Raw output
            context_lines: Number of lines to keep from start/end
            
        Returns:
            Preview string
        """
        lines = output.splitlines()
        total_lines = len(lines)
        
        if total_lines <= context_lines * 2:
            return output
        
        first_lines = lines[:context_lines]
        last_lines = lines[-context_lines:]
        omitted = total_lines - (context_lines * 2)
        
        preview = (
            '\n'.join(first_lines) +
            f'\n\n[... {omitted} lines omitted ...]\n\n' +
            '\n'.join(last_lines)
        )
        
        return preview
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text.
        
        Uses simple heuristic: ~4 characters per token for English text.
        
        Args:
            text: Text to estimate
            
        Returns:
            Estimated token count
        """
        # Rough estimation: 1 token ≈ 4 characters for English
        # More accurate would be to use tiktoken, but this is fast
        char_count = len(text)
        return char_count // 4
    
    async def search_stored_output(
        self,
        file_path: Path,
        query: str,
        case_sensitive: bool = False,
        max_results: int = 50
    ) -> List[Dict[str, Any]]:
        """Search within stored output file.
        
        Args:
            file_path: Path to stored output file
            query: Search query
            case_sensitive: Whether search is case-sensitive
            max_results: Maximum results to return
            
        Returns:
            List of matching lines with metadata
        """
        return await self.temp_manager.grep_file(
            file_path=file_path,
            query=query,
            case_sensitive=case_sensitive,
            max_results=max_results
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get output manager statistics.
        
        Returns:
            Statistics dictionary
        """
        return {
            'inline_max_bytes': self.inline_max_bytes,
            'summary_max_bytes': self.summary_max_bytes,
            'max_inline_lines': self.max_inline_lines,
            'context_lines': self.context_lines,
            'enable_summarization': self.enable_summarization,
            'temp_manager_stats': self.temp_manager.get_stats()
        }
