"""Rich terminal UI with prompt_toolkit integration"""
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn
from rich.tree import Tree
from rich.box import ROUNDED, SIMPLE
from typing import Optional, List, Dict, Any, Tuple
import asyncio
from datetime import datetime
import sys
import os
import re
from pathlib import Path
import difflib

# Import new TUI components
try:
    from .ui_components import (
        CollapsiblePanel, ToolCallCard, ResultSummary,
        DiffViewer, OutputViewer, TabbedDisplay, StatusBadge,
        create_tool_result_display, TodoListPanel
    )
    TUI_COMPONENTS_AVAILABLE = True
except ImportError:
    CollapsiblePanel = None
    ToolCallCard = None
    ResultSummary = None
    DiffViewer = None
    OutputViewer = None
    TabbedDisplay = None
    StatusBadge = None
    create_tool_result_display = None
    TodoListPanel = None
    TUI_COMPONENTS_AVAILABLE = False

# Import output manager
try:
    from .output_manager import OutputManager, OutputResult
    OUTPUT_MANAGER_AVAILABLE = True
except ImportError:
    OutputManager = None
    OutputResult = None
    OUTPUT_MANAGER_AVAILABLE = False

# Import approval workflow types
try:
    from .approval_workflow import ApprovalMode, RiskLevel, ApprovalManager
    APPROVAL_AVAILABLE = True
except ImportError:
    ApprovalMode = None
    RiskLevel = None
    ApprovalManager = None
    APPROVAL_AVAILABLE = False

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    
    # Enable VT100 mode for better prompt_toolkit support on Windows
    try:
        from ctypes import windll, c_long, byref
        
        STD_OUTPUT_HANDLE = -11
        ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
        
        hStdOut = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
        if hStdOut != -1:  # INVALID_HANDLE_VALUE
            mode = c_long()
            if windll.kernel32.GetConsoleMode(hStdOut, byref(mode)):
                mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
                windll.kernel32.SetConsoleMode(hStdOut, mode)
    except Exception:
        pass  # Fall back to basic mode if VT100 not available

console = Console(legacy_windows=False)

# Command completer for autocomplete
COMMAND_COMPLETER = WordCompleter(
    [
        'help', 'exit', 'quit', 'clear', 'history', 'stats', 'config', 'configure', 'budget',
        'context', 'thrashing check', 'export', 'cache clear',
        'model list', 'model switch', 'model stats',
        'skills list', 'skills info',
        'subagents list', 'subagents status', 'subagents run'
    ],
    ignore_case=True,
    sentence=True
)


def _format_size(size_bytes: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f}TB"


def _render_content(content: str):
    """Render content with proper code block formatting"""
    pattern = r'```(\w*)\n(.*?)```'
    parts = re.split(pattern, content, flags=re.DOTALL)

    for i, part in enumerate(parts):
        if not part:
            continue
        if i % 3 == 1:
            continue
        elif i % 3 == 2:
            lang = parts[i - 1] if i > 0 and parts[i - 1] else 'text'
            syntax = Syntax(part, lang or 'text', theme='monokai', padding=(1, 1))
            console.print(syntax)
        else:
            if part.strip():
                console.print(Markdown(part))


class StreamingDisplay:
    """Handle streaming token display with syntax highlighting"""

    def __init__(self, console):
        self.console = console
        self.buffer = ""
        self.in_code_block = False
        self.code_language = ""
        self.code_buffer = ""

    def add_token(self, token: str):
        self.buffer += token
        if token.startswith('```') and not self.in_code_block:
            self.in_code_block = True
            self.code_language = token[3:].strip()
            return
        if token.endswith('```') and self.in_code_block:
            self.in_code_block = False
            code_content = self.code_buffer
            if code_content:
                syntax = Syntax(code_content, self.code_language or 'text', theme='monokai', padding=(0, 1))
                self.console.print(syntax)
            self.code_buffer = ""
            return
        if self.in_code_block:
            self.code_buffer += token

    def finish(self, full_content: str, usage: Optional[Dict] = None):
        _render_content(full_content)
        if usage:
            token_info = f"[yellow]Tokens: {usage.get('total_tokens', 0)}"
            if usage.get('cost', 0) > 0:
                token_info += f" | Cost: ${usage['cost']:.4f}"
            token_info += "[/yellow]"
            self.console.print(token_info)
        self.console.print()


class TokenBudgetDashboard:
    """Real-time token budget dashboard with progress visualization."""

    def __init__(self, console):
        self.console = console

    def display(self, current_usage: int, daily_limit: int, session_usage: int = 0):
        """Display token budget dashboard with progress bars."""
        usage_percentage = (current_usage / daily_limit * 100) if daily_limit > 0 else 0
        remaining = max(0, daily_limit - current_usage)

        # Determine color based on usage
        if usage_percentage >= 90:
            color = "red"
            status = "⚠️ CRITICAL"
        elif usage_percentage >= 80:
            color = "yellow"
            status = "⚠️ WARNING"
        elif usage_percentage >= 50:
            color = "cyan"
            status = "✓ MODERATE"
        else:
            color = "green"
            status = "✓ HEALTHY"

        # Create progress bar
        progress_bar = (
            f"[{color}][{'█' * int(usage_percentage / 2.5)}{'░' * (40 - int(usage_percentage / 2.5))}][/{color}]"
        )

        dashboard = Panel(
            f"[bold {color}]{status}[/bold {color}]\n\n"
            f"{progress_bar}\n\n"
            f"[bold]Current Usage:[/bold]    [yellow]{current_usage:,}[/yellow] / {daily_limit:,} tokens\n"
            f"[bold]Percentage:[/bold]      [{color}]{usage_percentage:.1f}%[/{color}]\n"
            f"[bold]Remaining:[/bold]       [green]{remaining:,} tokens[/green]\n"
            f"[bold]Session Usage:[/bold]   [cyan]{session_usage:,} tokens[/cyan]",
            title="📊 Token Budget Dashboard",
            border_style=color,
            title_align="left"
        )

        self.console.print(dashboard)

    def display_mini(self, current_usage: int, daily_limit: int) -> str:
        """Display compact token usage status line."""
        percentage = (current_usage / daily_limit * 100) if daily_limit > 0 else 0

        if percentage >= 90:
            color = "red"
            icon = "🔴"
        elif percentage >= 80:
            color = "yellow"
            icon = "🟡"
        elif percentage >= 50:
            color = "cyan"
            icon = "🔵"
        else:
            color = "green"
            icon = "🟢"

        return f"[{icon}] Tokens: [{color}]{current_usage:,}/{daily_limit:,} ({percentage:.1f}%)[/{color}]"


class StatusPanel:
    """Display agent status with spinners and progress indicators."""

    def __init__(self, console):
        self.console = console
        self.status_messages = {
            'thinking': '[bold cyan]🤔 Thinking...[/bold cyan]',
            'searching': '[bold blue]🔍 Searching codebase...[/bold blue]',
            'reading': '[bold green]📖 Reading files...[/bold green]',
            'writing': '[bold yellow]✏️  Writing code...[/bold yellow]',
            'executing': '[bold magenta]⚙️  Executing commands...[/bold magenta]',
            'testing': '[bold cyan]🧪 Running tests...[/bold cyan]',
            'complete': '[bold green]✓ Complete![/bold green]'
        }

    def show_status(self, status_key: str, detail: Optional[str] = None):
        """Show status message."""
        message = self.status_messages.get(status_key, f'[bold]{status_key}[/bold]')
        if detail:
            message += f" [dim]{detail}[/dim]"
        self.console.print(message)

    def create_progress(self, description: str = "Processing..."):
        """Create a progress indicator."""
        return Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console
        )


class AgentUI:
    """Main UI controller for the agent"""

    def __init__(self, config, approval_manager: Optional[Any] = None):
        self.config = config
        self.approval_manager = approval_manager
        self.session = None
        self.message_history: List[Dict[str, str]] = []
        self.current_response = ""
        self.token_usage = {'total': 0, 'cost': 0.0}
        self._interactive_mode = True
        self.token_dashboard = TokenBudgetDashboard(console)
        self.status_panel = StatusPanel(console)
        self.approval_prompt = ApprovalPrompt(console) if APPROVAL_AVAILABLE else None

        try:
            self.session = PromptSession(
                completer=COMMAND_COMPLETER,
                complete_while_typing=True,
                enable_history_search=True,
                mouse_support=False,
                complete_in_thread=True
            )
        except Exception:
            # prompt_toolkit may fail on Windows with certain terminal emulators
            # (Git Bash, VS Code terminal with xterm, etc.)
            # Fall back to basic input without autocomplete
            self._interactive_mode = False
            self.session = None
            console.print("[dim]Note: Advanced terminal features unavailable. Using basic input mode.[/dim]")

    def display_welcome(self):
        """Display welcome message"""
        welcome = Panel(
            "[bold cyan]🚀 RapidWebs Agentic CLI[/bold cyan]\n\n"
            "[green]Cross-platform AI agent optimized for free-tier LLMs[/green]\n\n"
            "[yellow]Type 'help' for commands, 'exit' to quit[/yellow]\n\n"
            "[dim]Features: Streaming, pipe support, diff display, conversation persistence[/dim]\n"
            "[dim]Token Budget: Check 'stats' or set RW_DAILY_TOKEN_LIMIT env var[/dim]\n"
            "[dim]Tab autocomplete: Use cmd.exe for full features[/dim]",
            title="[bold]RapidWebs Agent v2.0[/bold]",
            border_style="cyan"
        )
        console.print(welcome)
        
        # Display approval mode indicator if available
        if self.approval_manager:
            self.display_mode_indicator(self.approval_manager.get_mode())
        
        console.print()

    def display_mode_indicator(self, mode: Any, inline: bool = False):
        """Display current approval mode indicator.

        Args:
            mode: ApprovalMode enum value
            inline: If True, display as compact inline indicator
        """
        if not APPROVAL_AVAILABLE:
            return

        # Get mode color and icon
        colors = {
            ApprovalMode.PLAN: "blue",
            ApprovalMode.DEFAULT: "yellow",
            ApprovalMode.AUTO_EDIT: "cyan",
            ApprovalMode.YOLO: "red"
        }

        icons = {
            ApprovalMode.PLAN: "📋",
            ApprovalMode.DEFAULT: "🛡️",
            ApprovalMode.AUTO_EDIT: "⚡",
            ApprovalMode.YOLO: "🚀"
        }

        color = colors.get(mode, "white")
        icon = icons.get(mode, "❓")

        if inline:
            # Compact inline indicator for status bar
            indicator = f"[{color}]{icon} {mode.value.upper()}[/{color}]"
            console.print(indicator)
        else:
            # Full panel indicator
            # Get description
            if self.approval_manager:
                description = self.approval_manager.get_mode_description()
            else:
                description = "Unknown mode"

            indicator = Panel(
                f"[bold {color}]{icon} Mode: {mode.value.upper()}[/{color}]\n\n"
                f"[dim]{description}[/dim]",
                title="Approval Mode",
                border_style=color,
                title_align="left"
            )
            console.print(indicator)
            console.print()
    
    def display_mode_menu(self):
        """Display approval mode selection menu with quick-switch options."""
        if not APPROVAL_AVAILABLE:
            return

        current_mode = self.approval_manager.get_mode() if self.approval_manager else None

        console.print(Panel(
            "[bold cyan]Approval Modes[/bold cyan]\n\n"
            "Choose an approval mode based on your trust level and task complexity.\n",
            title="📋 Mode Selection",
            border_style="cyan"
        ))

        # Create modes table
        table = Table(
            title="Available Modes",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan"
        )
        table.add_column("Mode", style="bold", width=15)
        table.add_column("Icon", width=8)
        table.add_column("Description", width=45)
        table.add_column("Best For", width=25)
        table.add_column("Switch", width=12)

        modes_info = [
            ("plan", "📋", "Read-only. No write/destructive ops.", "Code exploration", "/mode plan"),
            ("default", "🛡️", "Confirm write/destructive ops.", "New codebases", "/mode default"),
            ("auto-edit", "⚡", "Auto-accept edits.", "Daily development", "/mode auto-edit"),
            ("yolo", "🚀", "Full automation.", "Trusted tasks", "/mode yolo"),
        ]

        for mode_name, icon, desc, best_for, switch_cmd in modes_info:
            # Highlight current mode
            is_current = current_mode and current_mode.value == mode_name
            mode_style = "bold green" if is_current else "white"
            current_marker = " ✓" if is_current else ""
            
            table.add_row(
                f"[{mode_style}]{mode_name}{current_marker}[/{mode_style}]",
                icon,
                desc,
                best_for,
                f"[dim]{switch_cmd}[/dim]"
            )

        console.print(table)
        console.print()
        console.print("[bold yellow]Quick Switch:[/bold yellow]")
        console.print("  [cyan]/mode plan[/cyan]       - Read-only exploration")
        console.print("  [cyan]/mode default[/cyan]    - Balanced (recommended)")
        console.print("  [cyan]/mode auto-edit[/cyan]  - Auto-accept edits")
        console.print("  [cyan]/mode yolo[/cyan]       - Full automation")
        console.print()
        console.print("[bold yellow]Keyboard Shortcuts:[/bold yellow]")
        console.print("  [cyan]Ctrl+P[/cyan] - Plan mode")
        console.print("  [cyan]Ctrl+D[/cyan] - Default mode")
        console.print("  [cyan]Ctrl+A[/cyan] - Auto-edit mode")
        console.print("  [cyan]Ctrl+Y[/cyan] - YOLO mode")
        console.print()

    def change_approval_mode(self, mode_str: str) -> Tuple[bool, str]:
        """Change approval mode with validation and confirmation.
        
        Args:
            mode_str: Mode name string (plan, default, auto-edit, yolo)
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        if not APPROVAL_AVAILABLE or not self.approval_manager:
            return False, "Approval workflow not available."
        
        # Normalize mode string
        mode_str = mode_str.lower().strip()
        
        # Handle aliases
        aliases = {
            'p': 'plan',
            'd': 'default',
            'a': 'auto-edit',
            'auto': 'auto-edit',
            'y': 'yolo',
        }
        mode_str = aliases.get(mode_str, mode_str)
        
        # Try to set mode
        if self.approval_manager.set_mode(mode_str):
            new_mode = self.approval_manager.get_mode()
            
            # Get mode info for confirmation message
            mode_colors = {
                ApprovalMode.PLAN: ('blue', '📋'),
                ApprovalMode.DEFAULT: ('yellow', '🛡️'),
                ApprovalMode.AUTO_EDIT: ('cyan', '⚡'),
                ApprovalMode.YOLO: ('red', '🚀'),
            }
            color, icon = mode_colors.get(new_mode, ('white', '❓'))
            
            # Create confirmation message
            message = (
                f"[bold {color}]{icon} Mode changed to: {new_mode.value.upper()}[/{color}]\n\n"
                f"[dim]{self.approval_manager.get_mode_description()}[/dim]"
            )
            
            # Log the mode change
            self.approval_manager.log_mode_change(mode_str)
            
            return True, message
        else:
            return False, (
                f"[red]✗ Invalid mode: {mode_str}[/red]\n\n"
                f"Valid modes: [cyan]plan[/cyan], [cyan]default[/cyan], "
                f"[cyan]auto-edit[/cyan], [cyan]yolo[/cyan]"
            )

    def display_help(self):
        """Display help message"""
        help_text = """
[bold cyan]Available Commands:[/bold cyan]

[green]General:[/green]
  help              - Show this help message
  exit / quit       - Exit the agent (conversation auto-saved)
  clear             - Clear the screen
  history           - Show conversation history (last 10 messages)
  stats             - Show token usage statistics with budget dashboard
  config            - Show current configuration
  configure         - Launch interactive configuration wizard
  budget            - Show token budget dashboard
  context           - Show context optimization status
  thrashing check   - Check for context thrashing
  export [format]   - Export conversation (markdown/json)

[green]Approval Modes:[/green]
  mode              - Show approval mode menu
  /mode             - Same as 'mode'
  mode <name>       - Switch approval mode
  /mode <name>      - Same as 'mode <name>'
  /mode plan        - Read-only mode (exploration)
  /mode default     - Balanced mode (recommended)
  /mode auto-edit   - Auto-accept edits
  /mode yolo        - Full automation

[green]Keyboard Shortcuts:[/green]
  Ctrl+P            - Switch to Plan mode
  Ctrl+D            - Switch to Default mode
  Ctrl+A            - Switch to Auto-Edit mode
  Ctrl+Y            - Switch to YOLO mode

[green]Cache Management:[/green]
  cache clear       - Clear response cache

[green]Model Management:[/green]
  model list        - List available models
  model switch <name> - Switch to different model (e.g., `model switch gemini`)
  model stats       - Show model usage statistics (includes cache stats)

[green]Skills:[/green]
  skills list       - List available skills
  skills info <name> - Show skill information

[green]SubAgents (Parallel Task Delegation):[/green]
  subagents list    - List available subagents
  subagents status  - Show subagent orchestrator status
  subagents run <type> <task> - Run a subagent task
                      Types: code, test, docs, research, security
                      Example: `subagents run code "Refactor main.py"`

[green]Examples (Natural Language Tasks):[/green]
  Create a Python script that lists all files
  Explain how async/await works in Python
  Search the web for latest Python news
  Read the contents of README.md
  Explore the codebase structure
  Search for function definitions: grep "def main" *.py

[bold yellow]Quick Start:[/bold yellow]
  ✨ Type [cyan]configure[/cyan] for interactive setup
  📊 Type [cyan]budget[/cyan] to monitor token usage
  📋 Type [cyan]mode[/cyan] to see approval options
  ⌨️  Press [cyan]Tab[/cyan] for command autocomplete (cmd.exe only)
  📁 Reference files with [cyan]@filename[/cyan] syntax

[bold yellow]Note on Tab Autocomplete:[/bold yellow]
  Tab completion works best in Windows [cyan]cmd.exe[/cyan] or PowerShell.
  Some terminals (Git Bash, VS Code) may not support this feature.

[bold yellow]Configuration Tips:[/bold yellow]
  - Set daily token limit via `RW_DAILY_TOKEN_LIMIT` env var
  - Or edit config at `~/.config/rapidwebs-agent/config.yaml`
  - Use [cyan]stats[/cyan] for detailed usage breakdown
"""
        console.print(Markdown(help_text))
        console.print()

    def display_streaming_message(self, role: str, usage: Optional[Dict] = None):
        """Display a streaming message with typing animation"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        if role == 'agent':
            console.print(f"[bold green][{timestamp}] Agent:[/bold green]")
        return StreamingDisplay(console)

    def display_message(self, role: str, content: str, usage: Optional[Dict] = None):
        """Display a message in the conversation"""
        timestamp = datetime.now().strftime("%H:%M:%S")

        if role == 'user':
            console.print(f"[bold blue][{timestamp}] You:[/bold blue]")
            console.print(Panel(content, border_style="blue"))
        elif role == 'agent':
            console.print(f"[bold green][{timestamp}] Agent:[/bold green]")
            _render_content(content)

        if usage and self.config.ui.show_token_usage:
            token_info = f"[yellow]Tokens: {usage.get('total_tokens', 0)}"
            if usage.get('cost', 0) > 0:
                token_info += f" | Cost: ${usage['cost']:.4f}"
            token_info += "[/yellow]"
            console.print(token_info)

        console.print()

    def display_stats(self, model_stats: Dict, token_usage: Dict, daily_limit: Optional[int] = None):
        """Display enhanced usage statistics with token budget dashboard."""
        # Show token budget dashboard if limit provided
        if daily_limit and daily_limit > 0:
            self.token_dashboard.display(
                current_usage=token_usage.get('total', 0),
                daily_limit=daily_limit,
                session_usage=token_usage.get('total', 0)
            )
            console.print()

        # Detailed statistics table
        table = Table(title="📊 Detailed Usage Statistics", show_header=True, header_style="bold cyan")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Metric", style="white", width=25)
        table.add_column("Value", style="green", width=20)

        # Model statistics
        for model_name, stats in model_stats.items():
            table.add_row(
                f"Model: {model_name.replace('_', ' ').title()}",
                "Requests",
                str(stats.get('requests', 0))
            )
            table.add_row(
                "",
                "Tokens",
                f"{stats.get('tokens', 0):,}"
            )
            table.add_row(
                "",
                "Cost",
                f"${stats.get('cost', 0):.4f}"
            )
            if 'cache_stats' in stats:
                cache = stats['cache_stats']
                table.add_row(
                    "",
                    "Cache",
                    f"{cache.get('size', 0)}/{cache.get('max_size', 0)} entries"
                )
            table.add_row("", "", "")

        # Totals
        table.add_row(
            "[bold]Session Total[/bold]",
            "Total Tokens",
            f"[yellow]{token_usage.get('total', 0):,}[/yellow]"
        )
        table.add_row(
            "",
            "Total Cost",
            f"${token_usage.get('cost', 0):.4f}"
        )

        console.print(table)
        console.print()

        # Quick tips
        if token_usage.get('total', 0) > daily_limit * 0.8 if daily_limit else False:
            console.print(Panel(
                "[yellow]⚠️  Approaching daily limit![/yellow]\n\n"
                "Tips to reduce token usage:\n"
                "  • Use [cyan]/cache clear[/cyan] to reset cache\n"
                "  • Use [cyan]/clear[/cyan] to reduce context\n"
                "  • Reference files with @ instead of pasting",
                title="Token Saving Tips",
                border_style="yellow"
            ))

    def display_token_budget(self, current_usage: int, daily_limit: int, session_usage: int = 0):
        """Display token budget dashboard."""
        self.token_dashboard.display(current_usage, daily_limit, session_usage)

    def show_thinking_enhanced(self, status: str = 'thinking'):
        """Show enhanced thinking status with spinner."""
        return self.status_panel.create_progress(
            self.status_panel.status_messages.get(status, 'Processing...')
        )

    def display_todos(self, todos: List[Dict[str, Any]], title: str = "📋 Tasks"):
        """Display TODO list using TodoListPanel component.

        Args:
            todos: List of TODO dictionaries with 'description' and 'status'
            title: Panel title
        """
        if TUI_COMPONENTS_AVAILABLE and TodoListPanel:
            panel = TodoListPanel(todos=todos, title=title, collapsed=False)
            panel.render(self.console)
        else:
            # Fallback to simple text display
            self.console.print(f"\n[bold cyan]{title}[/bold cyan]")
            for todo in todos:
                status = todo.get('status', 'pending')
                desc = todo.get('description', 'Unnamed')
                icon = '✓' if status == 'completed' else '⏳' if status == 'in_progress' else '⏸'
                color = 'green' if status == 'completed' else 'yellow' if status == 'in_progress' else 'dim'
                self.console.print(f"  {icon} [{color}]{desc}[/{color}]")
            self.console.print()

    def display_tool_call_card(
        self,
        tool_name: str,
        operation: str,
        params: Dict[str, Any],
        status: str = 'running',
        duration_ms: Optional[float] = None,
        risk_level: str = 'read',
        output_preview: Optional[str] = None
    ):
        """Display tool execution using ToolCallCard component.

        Args:
            tool_name: Name of the tool
            operation: Operation being performed
            params: Tool parameters
            status: Execution status (pending, running, success, error)
            duration_ms: Execution duration in milliseconds
            risk_level: Risk level (read, write, danger)
            output_preview: Preview of tool output
        """
        if TUI_COMPONENTS_AVAILABLE and ToolCallCard:
            card = ToolCallCard(
                tool_name=tool_name,
                operation=operation,
                params=params,
                status=status,
                duration_ms=duration_ms,
                risk_level=risk_level,
                output_preview=output_preview
            )
            card.render(self.console)
        else:
            # Fallback to simple display
            status_icons = {'pending': '⏳', 'running': '⚙️', 'success': '✅', 'error': '❌'}
            icon = status_icons.get(status, '❓')
            status_colors = {'pending': 'dim', 'running': 'blue', 'success': 'green', 'error': 'red'}
            color = status_colors.get(status, 'white')
            
            self.console.print(f"\n{icon} [bold {color}]{tool_name}::{operation}[/bold {color}]")
            if params:
                for key, value in params.items():
                    if key not in ['content', 'api_key', 'token'] or (isinstance(value, str) and len(value) < 50):
                        self.console.print(f"  [dim]• {key}:[/dim] [cyan]{value}[/cyan]")
            if duration_ms:
                self.console.print(f"  [dim]Duration: {duration_ms:.0f}ms[/dim]")
            self.console.print()

    def display_diff(
        self,
        old_code: str,
        new_code: str,
        file_path: str,
        language: str = "text"
    ):
        """Display code diff using DiffViewer component.

        Args:
            old_code: Original code
            new_code: Modified code
            file_path: Path to the file
            language: Code language for syntax highlighting
        """
        if TUI_COMPONENTS_AVAILABLE and DiffViewer:
            viewer = DiffViewer(
                old_code=old_code,
                new_code=new_code,
                language=language,
                title=file_path
            )
            viewer.render(self.console)
        else:
            # Fallback to simple diff display
            self.console.print(f"\n[bold yellow]📝 File modified:[/bold yellow] [cyan]{file_path}[/cyan]\n")
            
            # Compute and display diff
            old_lines = old_code.splitlines()
            new_lines = new_code.splitlines()
            diff = difflib.unified_diff(old_lines, new_lines, lineterm='', n=3)
            
            for line in diff:
                if line.startswith('+') and not line.startswith('+++'):
                    self.console.print(f"[green]{line}[/green]")
                elif line.startswith('-') and not line.startswith('---'):
                    self.console.print(f"[red]{line}[/red]")
                elif line.startswith('@'):
                    self.console.print(f"[cyan]{line}[/cyan]")
                elif line.startswith(' '):
                    self.console.print(f"[dim]{line}[/dim]")
            self.console.print()

    def display_code_block(
        self,
        code: str,
        language: str = "text",
        title: Optional[str] = None,
        line_numbers: bool = True,
        theme: str = "monokai"
    ):
        """Display syntax-highlighted code block.

        Args:
            code: Code to display
            language: Programming language
            title: Optional title
            line_numbers: Show line numbers
            theme: Syntax highlighting theme
        """
        if title:
            self.console.print(f"\n[bold cyan]📄 {title}[/bold cyan]")
        
        syntax = Syntax(
            code,
            language,
            theme=theme,
            line_numbers=line_numbers,
            padding=(1, 2),
            word_wrap=True
        )
        self.console.print(syntax)
        self.console.print()

    def display_collapsible_output(
        self,
        content: str,
        title: str = "Output",
        collapsed: bool = True,
        border_style: str = "cyan"
    ):
        """Display large output in collapsible panel.

        Args:
            content: Output content
            title: Panel title
            collapsed: Start collapsed
            border_style: Border color
        """
        if TUI_COMPONENTS_AVAILABLE and CollapsiblePanel:
            panel = CollapsiblePanel(
                title=title,
                content=content,
                collapsed=collapsed,
                border_style=border_style
            )
            panel.render(self.console)
        else:
            # Fallback to simple panel
            self.console.print(Panel(
                content[:500] + ("..." if len(content) > 500 else ""),
                title=title,
                border_style=border_style
            ))
            if len(content) > 500:
                self.console.print(f"[dim]({len(content) - 500} more characters hidden)[/dim]")

    def display_skill_result(
        self,
        result: Dict,
        tool_name: str = 'unknown',
        duration_ms: Optional[float] = None
    ):
        """Display skill execution result with enhanced TUI components.
        
        Args:
            result: Tool result dictionary
            tool_name: Name of the tool that was executed
            duration_ms: Execution duration in milliseconds
        """
        # Use new TUI components if available and result has output manager format
        if TUI_COMPONENTS_AVAILABLE and create_tool_result_display:
            # Check if result has output manager format
            if 'routing_decision' in result or 'original_size' in result:
                create_tool_result_display(result, tool_name, duration_ms)
                return
        
        # Fallback to traditional display
        self._display_skill_result_traditional(result, tool_name, duration_ms)
    
    def _display_skill_result_traditional(
        self,
        result: Dict,
        tool_name: str = 'unknown',
        duration_ms: Optional[float] = None
    ):
        """Traditional skill result display with enhanced formatting."""
        if result['success']:
            # Build header with timing
            header_parts = [f"[green]✓ {tool_name}[/green]"]
            if duration_ms:
                header_parts.append(f"[dim]({duration_ms:.0f}ms)[/dim]")
            self.console.print(" ".join(header_parts))
            self.console.print()
            
            if 'stdout' in result:
                # Terminal command output
                if result['stdout']:
                    self.display_collapsible_output(
                        result['stdout'],
                        title="📟 Command Output",
                        collapsed=len(result['stdout']) > 2000,
                        border_style="green"
                    )
                if result.get('stderr'):
                    self.display_collapsible_output(
                        result['stderr'],
                        title="⚠️ Errors",
                        collapsed=False,
                        border_style="yellow"
                    )
                    
            elif 'text' in result:
                # Web scraping result
                url = result.get('url', 'N/A')
                self.console.print(f"[dim]Source:[/dim] [cyan underline]{url}[/cyan underline]\n")
                content = result['text']
                if len(content) > 3000:
                    self.display_collapsible_output(
                        content,
                        title="📄 Scraped Content",
                        collapsed=True,
                        border_style="cyan"
                    )
                else:
                    self.display_collapsible_output(
                        content,
                        title="📄 Scraped Content",
                        collapsed=False,
                        border_style="cyan"
                    )
                    
            elif 'content' in result:
                # File read result
                file_path = result.get('path', 'N/A')
                content = result['content']
                
                # Detect language for syntax highlighting
                language = self._detect_language(file_path)
                
                if len(content) > 3000:
                    # Show preview with syntax highlighting
                    preview = content[:3000]
                    self.display_code_block(preview, language=language, title=f"📄 {file_path} (preview)")
                    self.console.print(f"[dim]... ({len(content) - 3000} more characters)[/dim]\n")
                else:
                    self.display_code_block(content, language=language, title=f"📄 {file_path}")
                    
            elif 'diff' in result and result.get('diff'):
                # File modification result
                file_path = result.get('path', 'N/A')
                old_code = result.get('old_code', '')
                new_code = result.get('new_code', '')
                language = self._detect_language(file_path)
                
                if old_code and new_code:
                    # Use full diff viewer
                    self.display_diff(old_code, new_code, file_path, language=language)
                else:
                    # Fallback to diff text
                    self.console.print(f"\n[bold yellow]📝 File modified:[/bold yellow] [cyan]{file_path}[/cyan]\n")
                    if result.get('modified'):
                        diff_syntax = Syntax(result['diff'], 'diff', theme='monokai', padding=(1, 2))
                        self.console.print(diff_syntax)
                    else:
                        self.console.print("[dim]No changes[/dim]")
                        
            elif 'structure' in result:
                # Directory exploration result
                path = result.get('path', 'N/A')
                self.console.print(f"[green]✓ Explored:[/green] [cyan]{path}[/cyan]")
                self.console.print(f"[dim]Files: {result.get('file_count', 0)} | Directories: {result.get('dir_count', 0)}[/dim]\n")
                
                tree = Tree("📁 Codebase Structure")
                dir_tree_map = {}
                for item in result['structure']:
                    path_item = item['path']
                    path_obj = Path(path_item)
                    parent = str(path_obj.parent)
                    if item['type'] == 'directory':
                        if path_item not in dir_tree_map:
                            dir_tree_map[path_item] = {
                                'name': path_obj.name or path_item,
                                'tree': Tree(f"📁 {path_obj.name or path_item}"),
                                'parent': parent
                            }
                    else:
                        size_str = f" ({_format_size(item['size'])})" if item.get('size') else ""
                        if parent not in dir_tree_map:
                            dir_tree_map[parent] = {
                                'name': path_obj.parent.name or parent,
                                'tree': Tree(f"📁 {path_obj.parent.name or parent}"),
                                'parent': str(Path(parent).parent)
                            }
                        dir_tree_map[parent]['tree'].add(f"📄 {path_obj.name}{size_str}")
                
                sorted_dirs = sorted(dir_tree_map.items(), key=lambda x: x[0].count(os.sep))
                added = set()
                for path_item, dir_info in sorted_dirs:
                    if path_item not in added and dir_info['parent'] not in dir_tree_map:
                        tree.add(dir_info['tree'])
                        added.add(path_item)
                    elif dir_info['parent'] in dir_tree_map and dir_info['parent'] in added:
                        parent_tree = dir_tree_map[dir_info['parent']]['tree']
                        parent_tree.add(dir_info['tree'])
                        added.add(path_item)
                self.console.print(tree)
                
            elif 'matches' in result:
                # Search results
                total = result.get('total_matches', 0)
                self.console.print(f"[green]✓ Search completed:[/green] [cyan]{total} matches found[/cyan]\n")
                if result.get('truncated'):
                    self.console.print("[yellow]⚠️ Results truncated (showing first 100)[/yellow]\n")
                
                if result['matches']:
                    for match in result['matches'][:20]:
                        file_path = match.get('file', 'unknown')
                        line = match.get('line', 0)
                        content = match.get('content', '')
                        self.console.print(f"  [bold cyan]{file_path}:{line}[/bold cyan]")
                        # Display code snippet with syntax highlighting
                        language = self._detect_language(file_path)
                        if content:
                            syntax = Syntax(content, language, theme='monokai', padding=(0, 2))
                            self.console.print(syntax)
                        self.console.print()
                        
            elif 'files' in result:
                # File search results
                self.console.print(f"[green]✓ Found {len(result['files'])} files[/green]\n")
                for file in result['files'][:30]:
                    size_str = f" ({_format_size(file['size'])})" if file.get('size') else ""
                    self.console.print(f"  📄 [cyan]{file['name']}[/cyan]{size_str}")
                if len(result['files']) > 30:
                    self.console.print(f"\n[dim]... and {len(result['files']) - 30} more files[/dim]")
                    
            elif 'message' in result:
                # Custom message
                self.console.print(Markdown(result['message']))
                
        else:
            # Error display
            error_msg = result.get('error', 'Unknown error')
            suggestion = result.get('suggestion', '')
            
            error_panel = Panel(
                f"[bold red]{error_msg}[/bold red]",
                title="❌ Error",
                border_style="red",
                box=ROUNDED
            )
            self.console.print(error_panel)
            
            if suggestion:
                tip_panel = Panel(
                    f"[yellow]💡 {suggestion}[/yellow]",
                    title="Tip",
                    border_style="yellow",
                    box=SIMPLE
                )
                self.console.print(tip_panel)
        
        self.console.print()

    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension.

        Args:
            file_path: Path to the file

        Returns:
            Language name for syntax highlighting
        """
        ext_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.md': 'markdown',
            '.sh': 'bash',
            '.bash': 'bash',
            '.zsh': 'bash',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rb': 'ruby',
            '.php': 'php',
            '.sql': 'sql',
            '.xml': 'xml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.env': 'dotenv',
        }
        ext = Path(file_path).suffix.lower()
        return ext_map.get(ext, 'text')

    async def get_input(self, prompt: str = "➤ ") -> str:
        """Get user input with prompt"""
        if not self._interactive_mode or self.session is None:
            import asyncio
            loop = asyncio.get_event_loop()
            try:
                user_input = await loop.run_in_executor(None, input, prompt)
                return user_input.strip()
            except EOFError:
                return 'exit'
            except KeyboardInterrupt:
                return 'exit'
        try:
            return await self.session.prompt_async(prompt, multiline=False)
        except EOFError:
            return 'exit'
        except KeyboardInterrupt:
            return 'exit'

    def clear_screen(self):
        """Clear the terminal screen"""
        console.clear()
        self.display_welcome()

    def handle_keyboard_shortcut(self, key: str) -> Optional[str]:
        """Handle keyboard shortcuts for quick mode switching.
        
        Args:
            key: Key combination (e.g., 'ctrl+p', 'ctrl+d')
            
        Returns:
            Command string to execute, or None if not a shortcut
        """
        if not APPROVAL_AVAILABLE or not self.approval_manager:
            return None
        
        shortcuts = {
            'ctrl+p': '/mode plan',
            'ctrl+d': '/mode default',
            'ctrl+a': '/mode auto-edit',
            'ctrl+y': '/mode yolo',
        }
        
        key_lower = key.lower().strip()
        return shortcuts.get(key_lower, None)

    async def request_tool_approval(
        self,
        tool_call: Dict[str, Any],
        risk_level: Any
    ) -> str:
        """Request user approval for tool execution.
        
        Args:
            tool_call: Tool call dictionary with 'tool' and 'params'
            risk_level: RiskLevel of the operation
            
        Returns:
            User decision: 'yes', 'no', 'always', 'never'
        """
        if not self.approval_prompt:
            # Fallback if approval prompt not available
            return 'yes'
        
        return await self.approval_prompt.request_approval(tool_call, risk_level)

    def show_thinking(self, message: str = "Thinking..."):
        """Show thinking/spinner animation with progress"""
        return Progress(
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console
        )

    def show_progress(self, total: Optional[int] = None):
        """Show progress bar for long operations.
        
        Args:
            total: Total number of items if known, None for indeterminate
            
        Returns:
            Rich Progress context manager
        """
        columns = [
            SpinnerColumn(spinner_name="dots"),
            TextColumn("[progress.description]{task.description}"),
        ]

        if total is not None:
            from rich.progress import BarColumn
            columns.append(BarColumn())
            columns.append(TextColumn("[progress.completed]{task.completed}/{task.total}"))
        else:
            columns.append(TextColumn("[dim]{task.fields[status]}[/dim]"))

        return Progress(
            *columns,
            transient=True,
            console=console,
            status="working" if total is None else None
        )

    def display_config(self, config_dict: Dict):
        """Display current configuration"""
        console.print("[bold cyan]Current Configuration:[/bold cyan]")
        console.print()
        console.print("[bold]Default Model:[/bold]", config_dict.get('default_model', 'N/A'))
        console.print("[bold]API Keys:[/bold]")
        for model_name in ['qwen_coder', 'gemini']:
            if model_name in config_dict.get('models', {}):
                console.print(f"  {model_name}: configured")
        console.print()
        skills = config_dict.get('skills', {})
        console.print("[bold]Enabled Skills:[/bold]")
        for skill_name, skill_config in skills.items():
            if isinstance(skill_config, dict) and skill_config.get('enabled', False):
                console.print(f"  ✓ {skill_name}")
        console.print()
        monitoring = config_dict.get('token_monitoring', {})
        console.print("[bold]Token Monitoring:[/bold]")
        console.print(f"  Enabled: {monitoring.get('enabled', True)}")
        console.print(f"  Daily Cap: ${monitoring.get('daily_cost_cap', 0.00):.2f}")
        console.print()


class InteractiveAgentUI(AgentUI):
    """Interactive TUI with prompt_toolkit"""

    def __init__(self, config):
        super().__init__(config)
        self.bindings = KeyBindings()
        self._setup_bindings()

    def _setup_bindings(self):
        """Setup keyboard bindings"""
        @self.bindings.add('c-c')
        def _(event):
            """Ctrl+C to exit"""
            event.app.exit()

        @self.bindings.add('c-l')
        def _(event):
            """Ctrl+L to clear"""
            self.clear_screen()


class ApprovalPrompt:
    """Display tool approval prompt with options.
    
    This class handles the interactive approval prompt for tool execution,
    showing tool details, risk level, and getting user input.
    """
    
    def __init__(self, console: Console):
        """Initialize approval prompt.
        
        Args:
            console: Rich console instance
        """
        self.console = console
    
    def _get_risk_color(self, risk_level: RiskLevel) -> str:
        """Get color for risk level.
        
        Args:
            risk_level: The risk level
            
        Returns:
            Color string for Rich formatting
        """
        colors = {
            RiskLevel.READ: "green",
            RiskLevel.WRITE: "yellow",
            RiskLevel.DESTRUCTIVE: "red"
        }
        return colors.get(risk_level, "white")
    
    def _get_risk_icon(self, risk_level: RiskLevel) -> str:
        """Get icon for risk level.
        
        Args:
            risk_level: The risk level
            
        Returns:
            Icon string
        """
        icons = {
            RiskLevel.READ: "✓",
            RiskLevel.WRITE: "⚠",
            RiskLevel.DESTRUCTIVE: "☠"
        }
        return icons.get(risk_level, "?")
    
    def _format_tool_details(self, tool_call: Dict[str, Any]) -> str:
        """Format tool call details for display.
        
        Args:
            tool_call: Tool call dictionary
            
        Returns:
            Formatted details string
        """
        tool_name = tool_call.get('tool', 'unknown')
        params = tool_call.get('params', {})
        
        lines = [
            f"[bold cyan]Tool:[/bold cyan] {tool_name}",
            f"[bold cyan]Operation:[/bold cyan] {params.get('operation', params.get('action', 'N/A'))}"
        ]
        
        # Add path if present
        if 'path' in params:
            lines.append(f"[bold cyan]Path:[/bold cyan] {params['path']}")
        
        # Add command if present
        if 'command' in params:
            lines.append(f"[bold cyan]Command:[/bold cyan] {params['command']}")
        
        # Add URL if present
        if 'url' in params:
            lines.append(f"[bold cyan]URL:[/bold cyan] {params['url']}")
        
        # Add content preview if present
        if 'content' in params:
            content = params['content']
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"[bold cyan]Content:[/bold cyan] {content}")
        
        return '\n'.join(lines)
    
    def _show_details(self, tool_call: Dict[str, Any]):
        """Show detailed tool information.
        
        Args:
            tool_call: Tool call dictionary
        """
        details = self._format_tool_details(tool_call)
        self.console.print(Panel(
            details,
            title="Tool Details",
            border_style="cyan"
        ))
        self.console.print()
    
    async def request_approval(
        self,
        tool_call: Dict[str, Any],
        risk_level: RiskLevel,
        timeout_seconds: int = 300
    ) -> str:
        """Display approval prompt and get user response.

        Args:
            tool_call: Tool call dictionary with 'tool' and 'params'
            risk_level: Risk level of the operation
            timeout_seconds: Approval timeout (default: 5 minutes)

        Returns:
            User decision: 'yes', 'no', 'always', 'never'
        """
        # Get risk color and icon
        risk_color = self._get_risk_color(risk_level)
        risk_icon = self._get_risk_icon(risk_level)

        # Get current approval mode info
        current_mode = None
        mode_info = ""
        if self.approval_manager:
            current_mode = self.approval_manager.get_mode()
            mode_colors = {
                ApprovalMode.PLAN: ('blue', '📋'),
                ApprovalMode.DEFAULT: ('yellow', '🛡️'),
                ApprovalMode.AUTO_EDIT: ('cyan', '⚡'),
                ApprovalMode.YOLO: ('red', '🚀'),
            }
            mode_color, mode_icon = mode_colors.get(current_mode, ('white', '❓'))
            mode_info = f"\n[dim]Mode: {mode_icon} {current_mode.value.upper()} (switch with /mode)[/dim]"

        # Format tool call for display
        details = self._format_tool_details(tool_call)

        # Create approval panel with mode indicator
        panel = Panel(
            f"{details}\n\n"
            f"[bold {risk_color}]Risk Level: {risk_icon} {risk_level.value.upper()}[/{risk_color}]"
            f"{mode_info}\n\n"
            f"[dim]Timeout: {timeout_seconds}s[/dim]",
            title="⚠️  Tool Execution Request",
            border_style=risk_color
        )

        self.console.print(panel)
        self.console.print()

        # Show options
        options_table = Table(
            title="Options",
            show_header=False,
            box=None,
            padding=(0, 2)
        )
        options_table.add_column("Key", style="bold cyan")
        options_table.add_column("Action", style="white")

        options_table.add_row("[green]y[/green]", "Yes, execute this time")
        options_table.add_row("[red]n[/red]", "No, skip this operation")
        options_table.add_row("[cyan]a[/cyan]", "Always allow this tool (session)")
        options_table.add_row("[magenta]v[/magenta]", "Never allow this tool (session)")
        options_table.add_row("[yellow]d[/yellow]", "Show details")

        self.console.print(options_table)
        self.console.print()

        # Get user input with timeout
        response = await self._get_user_input_async(timeout_seconds=timeout_seconds)

        if response in ['y', 'yes']:
            return 'yes'
        elif response in ['n', 'no']:
            return 'no'
        elif response in ['a', 'always']:
            return 'always'
        elif response in ['v', 'never']:
            return 'never'
        elif response in ['d', 'details']:
            self._show_details(tool_call)
            # Show details and loop back for input
            return await self.request_approval(tool_call, risk_level, timeout_seconds)
        elif response == 'timeout':
            self.console.print("[yellow]Approval timeout - denying request[/yellow]")
            return 'no'
        else:
            self.console.print("[red]Invalid option. Please try again.[/red]")
            self.console.print()
            # Retry on invalid input
            return await self.request_approval(tool_call, risk_level, timeout_seconds)

    async def _get_user_input_async(self, timeout_seconds: int = 300) -> str:
        """Get user input with Windows-compatible async handling.

        Uses a dedicated thread for blocking input to prevent event loop freezing.
        Includes timeout protection and fallback mechanisms.
        
        Args:
            timeout_seconds: Timeout in seconds (default: 5 minutes)

        Returns:
            User input string or 'timeout' on timeout
        """
        import threading
        import queue

        # Create a queue for thread communication
        input_queue = queue.Queue()
        result = {'value': None, 'error': None}

        def blocking_input():
            """Thread function to read input without blocking main loop."""
            try:
                user_input = input("Your choice [y/n/a/v/d]: ").strip().lower()
                result['value'] = user_input
            except EOFError:
                result['value'] = 'no'
            except KeyboardInterrupt:
                result['value'] = 'no'
            except Exception as e:
                result['error'] = str(e)
            finally:
                input_queue.put(True)  # Signal completion

        # Start input thread
        input_thread = threading.Thread(target=blocking_input, daemon=True)
        input_thread.start()

        # Wait for input with timeout
        try:
            loop = asyncio.get_event_loop()
            await asyncio.wait_for(
                loop.run_in_executor(None, input_queue.get),
                timeout=timeout_seconds
            )

            # Check result
            if result['error']:
                self.console.print(f"[dim]Input error: {result['error']}[/dim]")
                return 'no'

            if result['value'] is not None:
                return result['value']

            # Fallback if thread completed but no value
            return 'no'

        except asyncio.TimeoutError:
            self.console.print(f"[dim]No response within {timeout_seconds}s - auto-denying[/dim]")
            return 'timeout'
        except Exception as e:
            self.console.print(f"[dim]Unexpected error: {e}[/dim]")
            return 'no'


# InteractiveAgentUI was merged into AgentUI for simplicity
# The class at line 1224 is the main implementation
