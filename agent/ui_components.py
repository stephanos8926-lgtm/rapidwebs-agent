"""Reusable TUI components for RapidWebs Agent.

This module provides industry-standard terminal UI components using Rich:
- CollapsiblePanel: Expandable/collapsible sections
- ToolCallCard: Structured tool execution display
- ResultSummary: Auto-generated result summaries
- DiffViewer: Side-by-side code comparison
- OutputViewer: Paginated large text with search
- TabbedDisplay: Tabbed interface for multi-part results

All components follow accessibility best practices with:
- Clear visual hierarchy
- Color-coded status indicators
- Consistent spacing and padding
- Screen-reader friendly text alternatives
"""

from typing import Optional, Dict, Any, List, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum
import asyncio

from rich.console import Console, Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.rule import Rule
from rich.box import ROUNDED, DOUBLE, SIMPLE
from rich.style import Style
from rich.live import Live
from rich.layout import Layout
from rich.align import Align

from .logging_config import get_logger

logger = get_logger('ui_components')

# Create shared console instance
console = Console(legacy_windows=False)


class StatusColor(Enum):
    """Status color mapping for consistent UI."""
    SUCCESS = "green"
    INFO = "cyan"
    WARNING = "yellow"
    ERROR = "red"
    PENDING = "dim"
    RUNNING = "blue"


@dataclass
class ToolCallInfo:
    """Information about a tool call for display.
    
    Attributes:
        tool_name: Name of the tool
        operation: Operation being performed
        params: Tool parameters
        status: Execution status
        duration_ms: Execution duration in milliseconds
        risk_level: Risk level of the operation
    """
    tool_name: str
    operation: str
    params: Dict[str, Any]
    status: str = "pending"
    duration_ms: Optional[float] = None
    risk_level: str = "read"


class CollapsiblePanel:
    """Collapsible panel component for expandable content.
    
    Industry pattern: Use for long outputs that users may want to hide/show.
    Simulates collapse/expand through state management (actual interactivity
    requires full TUI framework like Textual).
    
    Example:
        panel = CollapsiblePanel(
            title="Tool Output",
            content=long_output,
            collapsed=False,
            border_style="green"
        )
        panel.render(console)
    """
    
    def __init__(
        self,
        title: str,
        content: str,
        collapsed: bool = False,
        border_style: str = "white",
        subtitle: Optional[str] = None,
        padding: tuple = (1, 2)
    ):
        """Initialize collapsible panel.
        
        Args:
            title: Panel title
            content: Panel content (can be long)
            collapsed: Whether panel starts collapsed
            border_style: Border color/style
            subtitle: Optional subtitle
            padding: Content padding (top/bottom, left/right)
        """
        self.title = title
        self.content = content
        self.collapsed = collapsed
        self.border_style = border_style
        self.subtitle = subtitle
        self.padding = padding
        self.expanded = not collapsed
    
    def toggle(self):
        """Toggle expanded/collapsed state."""
        self.expanded = not self.expanded
        logger.debug(f'Panel "{self.title}" toggled: {"expanded" if self.expanded else "collapsed"}')
    
    def render(self, console: Optional[Console] = None) -> None:
        """Render the panel.
        
        Args:
            console: Rich console instance (uses global if not provided)
        """
        console = console or Console()
        
        if self.expanded:
            # Show full content
            panel = Panel(
                self.content,
                title=f"[bold]{self.title}[/bold]",
                subtitle=self.subtitle,
                border_style=self.border_style,
                padding=self.padding,
                box=ROUNDED
            )
        else:
            # Show collapsed preview
            preview_lines = self.content.splitlines()[:3]
            preview = '\n'.join(preview_lines)
            if len(self.content.splitlines()) > 3:
                preview += f"\n[dim]... ({len(self.content.splitlines()) - 3} more lines)[/dim]"
            
            panel = Panel(
                preview,
                title=f"[bold]{self.title}[/bold] [dim](collapsed)[/dim]",
                subtitle=self.subtitle,
                border_style="dim",
                padding=(0, 1),
                box=SIMPLE
            )
        
        console.print(panel)
    
    def __rich__(self):
        """Rich render method for composition."""
        if self.expanded:
            return Panel(
                self.content,
                title=f"[bold]{self.title}[/bold]",
                subtitle=self.subtitle,
                border_style=self.border_style,
                padding=self.padding,
                box=ROUNDED
            )
        else:
            preview_lines = self.content.splitlines()[:3]
            preview = '\n'.join(preview_lines)
            if len(self.content.splitlines()) > 3:
                preview += f"\n[dim]... ({len(self.content.splitlines()) - 3} more lines)[/dim]"
            
            return Panel(
                preview,
                title=f"[bold]{self.title}[/bold] [dim](collapsed)[/dim]",
                subtitle=self.subtitle,
                border_style="dim",
                padding=(0, 1),
                box=SIMPLE
            )


class ToolCallCard:
    """Structured card displaying tool call information.
    
    Industry pattern: Consistent visual representation of tool executions
    with status indicators, timing, and parameter summary.
    
    Example:
        card = ToolCallCard(
            tool_name="fs",
            operation="write",
            params={"path": "main.py"},
            status="success",
            duration_ms=145.2
        )
        card.render(console)
    """
    
    STATUS_ICONS = {
        'pending': '⏳',
        'running': '⚙️',
        'success': '✅',
        'error': '❌',
        'warning': '⚠️',
        'denied': '🚫'
    }
    
    RISK_COLORS = {
        'read': 'green',
        'write': 'yellow',
        'danger': 'red'
    }
    
    def __init__(
        self,
        tool_name: str,
        operation: str,
        params: Dict[str, Any],
        status: str = 'pending',
        duration_ms: Optional[float] = None,
        risk_level: str = 'read',
        show_params: bool = True,
        max_param_length: int = 100
    ):
        """Initialize tool call card.
        
        Args:
            tool_name: Name of the tool
            operation: Operation being performed
            params: Tool parameters
            status: Execution status (pending, running, success, error, denied)
            duration_ms: Execution duration in milliseconds
            risk_level: Risk level (read, write, danger)
            show_params: Whether to show parameters
            max_param_length: Maximum length for parameter values
        """
        self.tool_name = tool_name
        self.operation = operation
        self.params = params
        self.status = status
        self.duration_ms = duration_ms
        self.risk_level = risk_level
        self.show_params = show_params
        self.max_param_length = max_param_length
    
    def _format_params(self) -> str:
        """Format parameters for display.
        
        Returns:
            Formatted parameter string
        """
        if not self.show_params or not self.params:
            return ""
        
        lines = []
        for key, value in self.params.items():
            # Skip sensitive or large values
            if key in ['content', 'api_key', 'token', 'secret']:
                if isinstance(value, str) and len(value) > 50:
                    value = f"{value[:20]}... ({len(value)} chars)"
                else:
                    value = f"{value}"
            elif isinstance(value, str) and len(value) > self.max_param_length:
                value = f"{value[:self.max_param_length]}..."
            
            lines.append(f"  • {key}: {value}")
        
        return '\n'.join(lines)
    
    def _get_status_style(self) -> str:
        """Get color style for status.
        
        Returns:
            Color string
        """
        styles = {
            'pending': 'dim',
            'running': 'blue',
            'success': 'green',
            'error': 'red',
            'warning': 'yellow',
            'denied': 'magenta'
        }
        return styles.get(self.status, 'white')
    
    def render(self, console: Optional[Console] = None) -> None:
        """Render the tool call card.
        
        Args:
            console: Rich console instance
        """
        console = console or Console()
        
        # Build card content
        icon = self.STATUS_ICONS.get(self.status, '❓')
        status_style = self._get_status_style()
        risk_color = self.RISK_COLORS.get(self.risk_level, 'white')
        
        # Header line
        header = f"{icon} [bold]{self.tool_name}[/bold]::{self.operation}"
        
        # Build content
        content_parts = [header]
        
        # Add timing if available
        if self.duration_ms is not None:
            content_parts.append(f"[dim]Duration: {self.duration_ms:.0f}ms[/dim]")
        
        # Add risk indicator
        content_parts.append(f"[{risk_color}]Risk: {self.risk_level.upper()}[/{risk_color}]")
        
        # Add parameters
        params_text = self._format_params()
        if params_text:
            content_parts.append("")
            content_parts.append("[bold]Parameters:[/bold]")
            content_parts.append(params_text)
        
        # Add status badge
        status_text = f"[{status_style}]Status: {self.status.upper()}[/{status_style}]"
        content_parts.append("")
        content_parts.append(status_text)
        
        content = '\n'.join(content_parts)
        
        # Create panel with appropriate border
        border_color = status_style if self.status != 'pending' else 'dim'
        
        panel = Panel(
            content,
            title=f"[bold]Tool Call[/bold]",
            border_style=border_color,
            padding=(1, 2),
            box=ROUNDED
        )
        
        console.print(panel)
    
    def __rich__(self):
        """Rich render method for composition."""
        icon = self.STATUS_ICONS.get(self.status, '❓')
        status_style = self._get_status_style()
        risk_color = self.RISK_COLORS.get(self.risk_level, 'white')
        
        header = f"{icon} [bold]{self.tool_name}[/bold]::{self.operation}"
        
        content_parts = [header]
        
        if self.duration_ms is not None:
            content_parts.append(f"[dim]Duration: {self.duration_ms:.0f}ms[/dim]")
        
        content_parts.append(f"[{risk_color}]Risk: {self.risk_level.upper()}[/{risk_color}]")
        
        params_text = self._format_params()
        if params_text:
            content_parts.append("")
            content_parts.append("[bold]Parameters:[/bold]")
            content_parts.append(params_text)
        
        status_text = f"[{status_style}]Status: {self.status.upper()}[/{status_style}]"
        content_parts.append("")
        content_parts.append(status_text)
        
        content = '\n'.join(content_parts)
        border_color = status_style if self.status != 'pending' else 'dim'
        
        return Panel(
            content,
            title=f"[bold]Tool Call[/bold]",
            border_style=border_color,
            padding=(1, 2),
            box=ROUNDED
        )


class ResultSummary:
    """Auto-generated summary component for tool results.
    
    Industry pattern: Provide at-a-glance understanding of operation results
    with key metrics and status indicators.
    
    Example:
        summary = ResultSummary(
            title="File Write Complete",
            metrics={
                "Lines written": 150,
                "File size": "4.2 KB",
                "Backup created": True
            },
            status="success"
        )
        summary.render(console)
    """
    
    STATUS_CONFIG = {
        'success': {'icon': '✅', 'color': 'green', 'label': 'SUCCESS'},
        'error': {'icon': '❌', 'color': 'red', 'label': 'ERROR'},
        'warning': {'icon': '⚠️', 'color': 'yellow', 'label': 'WARNING'},
        'info': {'icon': 'ℹ️', 'color': 'cyan', 'label': 'INFO'},
    }
    
    def __init__(
        self,
        title: str,
        metrics: Dict[str, Any],
        status: str = 'info',
        details: Optional[str] = None,
        footer: Optional[str] = None
    ):
        """Initialize result summary.
        
        Args:
            title: Summary title
            metrics: Dictionary of metric name -> value
            status: Result status (success, error, warning, info)
            details: Optional detailed description
            footer: Optional footer text
        """
        self.title = title
        self.metrics = metrics
        self.status = status
        self.details = details
        self.footer = footer
    
    def render(self, console: Optional[Console] = None) -> None:
        """Render the result summary.
        
        Args:
            console: Rich console instance
        """
        console = console or Console()
        
        config = self.STATUS_CONFIG.get(self.status, self.STATUS_CONFIG['info'])
        
        # Build metrics table
        table = Table(show_header=False, box=SIMPLE, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="white")
        
        for key, value in self.metrics.items():
            # Format boolean values
            if isinstance(value, bool):
                value_str = "✓ Yes" if value else "✗ No"
                value_style = "green" if value else "dim"
            elif isinstance(value, int):
                value_str = f"{value:,}"
                value_style = "white"
            elif isinstance(value, float):
                value_str = f"{value:.2f}"
                value_style = "white"
            else:
                value_str = str(value)
                value_style = "white"
            
            table.add_row(f"{key}:", f"[{value_style}]{value_str}[/{value_style}]")
        
        # Build content
        content_parts = []
        
        # Title with status
        title_line = f"{config['icon']} [bold]{self.title}[/bold]"
        content_parts.append(title_line)
        content_parts.append("")
        
        # Metrics table
        content_parts.append(table)
        content_parts.append("")
        
        # Details
        if self.details:
            content_parts.append(self.details)
            content_parts.append("")
        
        # Footer
        if self.footer:
            content_parts.append(f"[dim]{self.footer}[/dim]")
        
        content = Group(*content_parts)
        
        # Create panel
        panel = Panel(
            content,
            title=f"[bold]{config['label']}[/bold]",
            border_style=config['color'],
            padding=(1, 2),
            box=ROUNDED
        )
        
        console.print(panel)


class DiffViewer:
    """Side-by-side code diff viewer.
    
    Industry pattern: Visual comparison of code changes with syntax
    highlighting and line numbers.
    
    Example:
        viewer = DiffViewer(
            old_code=original_code,
            new_code=modified_code,
            language="python",
            title="main.py changes"
        )
        viewer.render(console)
    """
    
    def __init__(
        self,
        old_code: str,
        new_code: str,
        language: str = "text",
        title: Optional[str] = None,
        context_lines: int = 3,
        theme: str = "monokai"
    ):
        """Initialize diff viewer.
        
        Args:
            old_code: Original code
            new_code: Modified code
            language: Code language for syntax highlighting
            title: Optional title for the diff
            context_lines: Lines of context around changes
            theme: Syntax highlighting theme
        """
        self.old_code = old_code
        self.new_code = new_code
        self.language = language
        self.title = title or "Code Diff"
        self.context_lines = context_lines
        self.theme = theme
    
    def _compute_diff(self) -> List[Dict[str, Any]]:
        """Compute simple line-by-line diff.
        
        Returns:
            List of diff hunks with line information
        """
        old_lines = self.old_code.splitlines()
        new_lines = self.new_code.splitlines()
        
        # Simple diff: mark added, removed, unchanged
        diff_result = []
        
        # Use simple heuristic for demo (proper diff would use difflib)
        import difflib
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=self.context_lines
        )
        
        hunks = []
        current_hunk = []
        
        for line in diff:
            if line.startswith('@@'):
                if current_hunk:
                    hunks.append('\n'.join(current_hunk))
                current_hunk = [line]
            else:
                current_hunk.append(line)
        
        if current_hunk:
            hunks.append('\n'.join(current_hunk))
        
        return hunks
    
    def render(self, console: Optional[Console] = None) -> None:
        """Render the diff viewer.
        
        Args:
            console: Rich console instance
        """
        console = console or Console()
        
        # Show old code
        console.print(f"[bold cyan]Before:[/bold cyan] {self.title}")
        old_syntax = Syntax(
            self.old_code,
            self.language,
            theme=self.theme,
            line_numbers=True,
            padding=(0, 1)
        )
        console.print(old_syntax)
        console.print()
        
        # Show diff
        console.print(f"[bold yellow]Changes:[/bold yellow]")
        hunks = self._compute_diff()
        for hunk in hunks:
            # Color-code diff lines
            for line in hunk.splitlines():
                if line.startswith('+') and not line.startswith('+++'):
                    console.print(f"[green]{line}[/green]")
                elif line.startswith('-') and not line.startswith('---'):
                    console.print(f"[red]{line}[/red]")
                elif line.startswith('@'):
                    console.print(f"[cyan]{line}[/cyan]")
                else:
                    console.print(f"[dim]{line}[/dim]")
        console.print()
        
        # Show new code
        console.print(f"[bold green]After:[/bold green] {self.title}")
        new_syntax = Syntax(
            self.new_code,
            self.language,
            theme=self.theme,
            line_numbers=True,
            padding=(0, 1)
        )
        console.print(new_syntax)


class OutputViewer:
    """Paginated output viewer for large text content.
    
    Industry pattern: Handle large outputs with pagination indicators
    and optional search capability.
    
    Example:
        viewer = OutputViewer(
            content=large_output,
            title="Command Output",
            page_size=50,
            show_line_numbers=True
        )
        viewer.render_page(0, console)  # Show first page
    """
    
    def __init__(
        self,
        content: str,
        title: str = "Output",
        page_size: int = 50,
        show_line_numbers: bool = False,
        syntax_language: Optional[str] = None,
        theme: str = "monokai"
    ):
        """Initialize output viewer.
        
        Args:
            content: Full output content
            title: Viewer title
            page_size: Lines per page
            show_line_numbers: Whether to show line numbers
            syntax_language: Language for syntax highlighting (None for plain text)
            theme: Syntax highlighting theme
        """
        self.content = content
        self.title = title
        self.page_size = page_size
        self.show_line_numbers = show_line_numbers
        self.syntax_language = syntax_language
        self.theme = theme
        
        self.lines = content.splitlines()
        self.total_pages = (len(self.lines) + page_size - 1) // page_size
    
    def get_page(self, page_num: int) -> str:
        """Get content for specific page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Page content string
        """
        if page_num < 0 or page_num >= self.total_pages:
            return f"[Error: Invalid page {page_num}/{self.total_pages}]"
        
        start = page_num * self.page_size
        end = min(start + self.page_size, len(self.lines))
        page_lines = self.lines[start:end]
        
        if self.show_line_numbers:
            numbered = []
            for i, line in enumerate(page_lines, start=start + 1):
                numbered.append(f"{i:6d} | {line}")
            return '\n'.join(numbered)
        
        return '\n'.join(page_lines)
    
    def render_page(
        self,
        page_num: int,
        console: Optional[Console] = None
    ) -> None:
        """Render specific page.
        
        Args:
            page_num: Page number to render
            console: Rich console instance
        """
        console = console or Console()
        
        page_content = self.get_page(page_num)
        
        # Create pagination info
        pagination = f"Page {page_num + 1}/{self.total_pages} | Lines {page_num * self.page_size + 1}-{min((page_num + 1) * self.page_size, len(self.lines))} of {len(self.lines)}"
        
        # Create content panel
        if self.syntax_language:
            content_panel = Panel(
                Syntax(
                    page_content,
                    self.syntax_language,
                    theme=self.theme,
                    line_numbers=False,
                    padding=(0, 1)
                ),
                border_style="cyan",
                box=ROUNDED
            )
        else:
            content_panel = Panel(
                page_content,
                border_style="cyan",
                box=ROUNDED,
                padding=(0, 1)
            )
        
        console.print(f"[bold]{self.title}[/bold]")
        console.print(content_panel)
        console.print(f"[dim]{pagination}[/dim]")
        console.print()
    
    def render_all(
        self,
        console: Optional[Console] = None,
        max_pages: Optional[int] = None
    ) -> None:
        """Render all pages (use with caution for large outputs).
        
        Args:
            console: Rich console instance
            max_pages: Maximum pages to render (None for all)
        """
        console = console or Console()
        
        pages_to_render = min(max_pages or self.total_pages, self.total_pages)
        
        for page_num in range(pages_to_render):
            self.render_page(page_num, console)


class TabbedDisplay:
    """Tabbed interface for multi-part results.
    
    Industry pattern: Organize related content into navigable tabs.
    Note: Full interactivity requires Textual framework.
    
    Example:
        tabs = TabbedDisplay(title="Results")
        tabs.add_tab("Summary", summary_content)
        tabs.add_tab("Details", detailed_content)
        tabs.add_tab("Errors", error_content)
        tabs.render(console, active_tab=0)
    """
    
    def __init__(
        self,
        title: str = "Output",
        border_style: str = "cyan"
    ):
        """Initialize tabbed display.
        
        Args:
            title: Display title
            border_style: Border color/style
        """
        self.title = title
        self.border_style = border_style
        self.tabs: List[Dict[str, str]] = []
        self.active_tab = 0
    
    def add_tab(self, label: str, content: str):
        """Add a tab with content.
        
        Args:
            label: Tab label
            content: Tab content
        """
        self.tabs.append({'label': label, 'content': content})
        logger.debug(f'Added tab: {label}')
    
    def set_active_tab(self, index: int):
        """Set active tab by index.
        
        Args:
            index: Tab index
        """
        if 0 <= index < len(self.tabs):
            self.active_tab = index
            logger.debug(f'Set active tab: {index} ({self.tabs[index]["label"]})')
    
    def render(
        self,
        console: Optional[Console] = None,
        active_tab: Optional[int] = None
    ) -> None:
        """Render the tabbed display.
        
        Args:
            console: Rich console instance
            active_tab: Override active tab index
        """
        console = console or Console()
        
        if not self.tabs:
            console.print(f"[dim]No tabs to display[/dim]")
            return
        
        tab_index = active_tab if active_tab is not None else self.active_tab
        tab_index = max(0, min(tab_index, len(self.tabs) - 1))
        
        # Render tab headers
        headers = []
        for i, tab in enumerate(self.tabs):
            if i == tab_index:
                headers.append(f"[bold {self.border_style}]● {tab['label']}[/bold {self.border_style}]")
            else:
                headers.append(f"[dim]○ {tab['label']}[/dim]")
        
        header_text = "  ".join(headers)
        console.print(f"[bold]{self.title}[/bold]")
        console.print(header_text)
        console.print(Rule(style="dim"))
        
        # Render active tab content
        active_content = self.tabs[tab_index]['content']
        console.print(active_content)
        
        # Render tab navigation hint
        if len(self.tabs) > 1:
            prev_idx = (tab_index - 1) % len(self.tabs)
            next_idx = (tab_index + 1) % len(self.tabs)
            console.print()
            console.print(
                f"[dim]Navigate: ← Previous ({self.tabs[prev_idx]['label']}) | "
                f"Next ({self.tabs[next_idx]['label']}) →[/dim]"
            )


class StatusBadge:
    """Compact status indicator badge.
    
    Industry pattern: Small, color-coded status indicators for quick
    visual scanning of operation states.
    
    Example:
        badge = StatusBadge("success", "Completed")
        badge.render(console)
    """
    
    CONFIG = {
        'success': {'icon': '✓', 'color': 'green'},
        'error': {'icon': '✗', 'color': 'red'},
        'warning': {'icon': '!', 'color': 'yellow'},
        'info': {'icon': 'ℹ', 'color': 'cyan'},
        'pending': {'icon': '⋯', 'color': 'dim'},
        'running': {'icon': '⟳', 'color': 'blue'},
    }
    
    def __init__(
        self,
        status: str = 'info',
        label: Optional[str] = None
    ):
        """Initialize status badge.
        
        Args:
            status: Status type
            label: Optional text label
        """
        self.status = status
        self.label = label
    
    def render(self, console: Optional[Console] = None) -> None:
        """Render the status badge.
        
        Args:
            console: Rich console instance
        """
        console = console or Console()
        
        config = self.CONFIG.get(self.status, self.CONFIG['info'])
        
        badge = f"[{config['color']}]{config['icon']} {self.label or self.status.upper()}[/{config['color']}]"
        console.print(badge)
    
    def __str__(self) -> str:
        """String representation."""
        config = self.CONFIG.get(self.status, self.CONFIG['info'])
        return f"{config['icon']} {self.label or self.status.upper()}"


def create_tool_result_display(
    result: Dict[str, Any],
    tool_name: str,
    duration_ms: Optional[float] = None
) -> None:
    """Create appropriate display for tool result.
    
    Factory function that chooses the best component based on result type.
    
    Args:
        result: Tool result dictionary
        tool_name: Name of the tool
        duration_ms: Execution duration
    """
    console = Console()
    
    # Check for output manager result
    if 'routing_decision' in result:
        # Output manager result
        if result.get('routing_decision') == 'inline':
            # Small output: show directly
            console.print(result.get('display_text', ''))
        elif result.get('routing_decision') == 'summarized':
            # Medium output: show summary + preview
            summary = result.get('summary', '')
            preview = result.get('display_text', '')
            
            summary_panel = Panel(
                summary,
                title="📊 Output Summary",
                border_style="cyan",
                box=ROUNDED
            )
            console.print(summary_panel)
            
            if preview:
                preview_panel = Panel(
                    preview,
                    title="📄 Preview (first/last lines)",
                    border_style="dim",
                    box=SIMPLE
                )
                console.print(preview_panel)
            
            # Show file path
            file_path = result.get('file_path')
            if file_path:
                console.print(f"[dim]Full output: {file_path}[/dim]")
        elif result.get('routing_decision') == 'file_only':
            # Large output: show summary only
            summary = result.get('summary', '')
            console.print(Markdown(summary))
            
            file_path = result.get('file_path')
            if file_path:
                console.print(f"[dim]Full output: {file_path}[/dim]")
    
    # Traditional result format
    elif 'success' in result:
        if result['success']:
            # Success: show result summary
            metrics = {}
            
            if 'lines' in result:
                metrics['Lines'] = result['lines']
            if 'size' in result:
                metrics['Size'] = result['size']
            if 'file_count' in result:
                metrics['Files'] = result['file_count']
            if 'matches' in result:
                metrics['Matches'] = result['matches']
            
            if metrics:
                summary = ResultSummary(
                    title=f"{tool_name} completed",
                    metrics=metrics,
                    status='success'
                )
                summary.render(console)
            else:
                console.print(f"[green]✓ {tool_name} completed successfully[/green]")
        else:
            # Error: show error panel
            error_msg = result.get('error', 'Unknown error')
            error_panel = Panel(
                f"[red]{error_msg}[/red]",
                title="❌ Error",
                border_style="red",
                box=ROUNDED
            )
            console.print(error_panel)
