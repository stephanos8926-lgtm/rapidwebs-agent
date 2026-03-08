"""Command-line interface for RapidWebs Agent."""

import argparse
import asyncio
import sqlite3
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table

from agent.agent import Agent
from agent.config import Config
from agent.caching import create_caching

# Import approval workflow
try:
    from agent.approval_workflow import ApprovalMode, ApprovalManager
    APPROVAL_AVAILABLE = True
except ImportError:
    APPROVAL_AVAILABLE = False
    ApprovalMode = None
    ApprovalManager = None

# Import prompt_toolkit for tab completion
try:
    from prompt_toolkit import PromptSession
    from prompt_toolkit.completion import WordCompleter
    from prompt_toolkit.history import FileHistory
    from prompt_toolkit.key_binding import KeyBindings

    # Enable VT100 mode for Windows
    if sys.platform == 'win32':
        try:
            from ctypes import windll, c_long, byref
            STD_OUTPUT_HANDLE = -11
            ENABLE_VIRTUAL_TERMINAL_PROCESSING = 0x0004
            hStdOut = windll.kernel32.GetStdHandle(STD_OUTPUT_HANDLE)
            if hStdOut != -1:
                mode = c_long()
                if windll.kernel32.GetConsoleMode(hStdOut, byref(mode)):
                    mode.value |= ENABLE_VIRTUAL_TERMINAL_PROCESSING
                    windll.kernel32.SetConsoleMode(hStdOut, mode)
        except Exception:
            pass

    PROMPT_TOOLKIT_AVAILABLE = True
except ImportError:
    PROMPT_TOOLKIT_AVAILABLE = False

# Import code tools for CLI commands
try:
    from agent.code_analysis_tools import CodeTools
    CODE_TOOLS_AVAILABLE = True
except ImportError:
    CODE_TOOLS_AVAILABLE = False

console = Console()

# Command completer for tab completion
COMMAND_COMPLETER = WordCompleter(
    [
        # Basic commands
        'help', 'exit', 'quit', 'q', 'clear', 'stats', 'model', 'cache',
        'budget', 'configure', 'subagents', 'mode', 'version',
        
        # Conversation management
        'history', 'resume', 'export', 'search', 'compress',
        
        # Memory system
        'memory', 'memory create', 'memory get', 'memory list', 
        'memory delete', 'memory search', 'memory stats',
        
        # TODO system
        'todo', 'todo add', 'todo list', 'todo toggle', 'todo done',
        'todo in-progress', 'todo clear', 'todo stats', 'todo export',

        # Output management
        'expand-output', 'collapse-output',

        # Project analysis
        'project', 'project detect', 'project skeleton', 'project tools',
        'project languages',
        
        # SubAgents commands
        'subagents list', 'subagents status', 'subagents run',
        
        # Approval modes
        'mode plan', 'mode default', 'mode auto-edit', 'mode yolo',
        
        # Model commands
        'model list', 'model switch', 'model stats',
    ],
    ignore_case=True,
    sentence=False
)

# Create key bindings for better Windows support
bindings = KeyBindings()

@bindings.add('c-c')
def _(event):
    """Handle Ctrl+C"""
    event.app.exit(exception=KeyboardInterrupt())

@bindings.add('c-d')
def _(event):
    """Handle Ctrl+D - exit if input is empty"""
    if not event.app.current_buffer.text:
        event.app.exit()

@bindings.add('c-p')
def _(event):
    """Handle Ctrl+P - switch to Plan mode"""
    buffer = event.app.current_buffer
    buffer.text = '/mode plan'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-a')
def _(event):
    """Handle Ctrl+A - switch to Auto-Edit mode"""
    buffer = event.app.current_buffer
    buffer.text = '/mode auto-edit'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-y')
def _(event):
    """Handle Ctrl+Y - switch to YOLO mode"""
    buffer = event.app.current_buffer
    buffer.text = '/mode yolo'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-l')
def _(event):
    """Handle Ctrl+L - clear screen"""
    buffer = event.app.current_buffer
    buffer.text = '/clear'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-v')
def _(event):
    """Handle Ctrl+V - show version"""
    buffer = event.app.current_buffer
    buffer.text = '/version'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('c-t')
def _(event):
    """Handle Ctrl+T - toggle TODO list"""
    buffer = event.app.current_buffer
    buffer.text = '/todo toggle'
    # Auto-submit
    event.app.current_buffer.validate_and_handle()

@bindings.add('e')
def _(event):
    """Handle 'e' - expand collapsed tool output"""
    # Only trigger when input is empty (to avoid interfering with typing)
    if not event.app.current_buffer.text:
        buffer = event.app.current_buffer
        buffer.text = '/expand-output'
        # Auto-submit
        event.app.current_buffer.validate_and_handle()

@bindings.add('c')
def _(event):
    """Handle 'c' - collapse expanded tool output"""
    # Only trigger when input is empty (to avoid interfering with typing)
    if not event.app.current_buffer.text:
        buffer = event.app.current_buffer
        buffer.text = '/collapse-output'
        # Auto-submit
        event.app.current_buffer.validate_and_handle()

BANNER = """
╔════════════════════════╗
║      RW-AGENT v2.0     ║
╚════════════════════════╝
"""


def print_banner():
    """Print the agent banner."""
    console.print(Panel(BANNER, style="bold cyan"))


def print_welcome():
    """Print welcome message with quick start tips."""
    welcome = """
**Quick Start:**
- Type your task naturally (e.g., "Refactor main.py to use async/await")
- Use `@filename` to reference specific files
- Use `/help` for available commands
- Use `/stats` to see token usage
- Press `Ctrl+C` to interrupt, `Ctrl+D` or `/exit` to quit

**Keyboard Shortcuts:**
- `Ctrl+P` - Plan mode (read-only)
- `Ctrl+D` - Default mode (confirm writes)
- `Ctrl+A` - Auto-Edit mode (auto-accept edits)
- `Ctrl+Y` - YOLO mode (no confirmations)
- `Ctrl+L` - Clear screen
- `Ctrl+V` - Show version
- `Ctrl+T` - Toggle TODO list

**Features:**
- 🚀 Free-tier optimized (Qwen Coder + Gemini)
- 🔒 Secure command execution with whitelisting
- 💾 Smart caching (70-85% token savings)
- 🤖 SubAgents for parallel task delegation
- 📊 Real-time token monitoring
- ✅ Approval workflow with 4 modes
- 📋 TODO/task management with progress tracking
"""
    console.print(Markdown(welcome))


def create_parser() -> argparse.ArgumentParser:
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog="rw-agent",
        description="RapidWebs Agent - Cross-platform agentic CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  rw-agent                    # Start interactive mode
  rw-agent "Fix bugs in app.py"  # Run single task
  rw-agent --model gemini     # Use Gemini model
  rw-agent --no-cache         # Disable caching
  rw-agent --stats            # Show usage statistics
  rw-agent --check-tools      # Check code tools availability
  rw-agent --install-tools    # Install Tier 1 code tools
  rw-agent --format main.py   # Format a file
  rw-agent --lint main.py     # Lint a file

Environment Variables:
  RW_QWEN_API_KEY            # Qwen Coder API key
  RW_GEMINI_API_KEY          # Gemini API key
  RW_DAILY_TOKEN_LIMIT       # Daily token budget (default: 100000)
        """
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="Task description (if provided, runs in non-interactive mode)"
    )

    parser.add_argument(
        "--model", "-m",
        choices=["qwen_coder", "gemini"],
        default=None,
        help="LLM model to use (default: qwen_coder)"
    )

    parser.add_argument(
        "--config", "-c",
        type=str,
        default=None,
        help="Path to config file (default: ~/.config/rapidwebs-agent/config.yaml)"
    )

    parser.add_argument(
        "--workspace", "-w",
        type=str,
        default=None,
        help="Working directory (default: current directory)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable response caching"
    )

    parser.add_argument(
        "--no-stream",
        action="store_true",
        help="Disable streaming responses"
    )

    parser.add_argument(
        "--token-limit",
        type=int,
        default=100000,
        help="Daily token budget (default: 100000)"
    )

    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show usage statistics and exit"
    )

    parser.add_argument(
        "--version", "-v",
        action="version",
        version="%(prog)s 1.0.0"
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output"
    )

    # Code tools commands
    parser.add_argument(
        "--check-tools",
        action="store_true",
        help="Check which code tools are installed (ruff, prettier, etc.)"
    )

    parser.add_argument(
        "--install-tools",
        action="store_true",
        help="Install Tier 1 code tools (ruff, prettier)"
    )

    parser.add_argument(
        "--format",
        type=str,
        metavar="FILE",
        help="Format a code file and print result"
    )

    parser.add_argument(
        "--lint",
        type=str,
        metavar="FILE",
        help="Lint a code file and print diagnostics"
    )

    parser.add_argument(
        "--install-tier2",
        action="store_true",
        help="Show installation commands for Tier 2 tools (Go, Rust, Shell, SQL)"
    )

    parser.add_argument(
        "--scan-workspace",
        action="store_true",
        help="Scan workspace for languages and suggest missing tools"
    )

    # New code analysis commands (Phase 2)
    parser.add_argument(
        "--symbols",
        type=str,
        metavar="FILE",
        help="Show symbols (functions, classes, imports) in a Python file"
    )

    parser.add_argument(
        "--related",
        type=str,
        metavar="FILE",
        help="Show files related to a given file"
    )

    parser.add_argument(
        "--callers",
        type=str,
        metavar="FUNCTION",
        help="Find all callers of a function in the codebase"
    )

    parser.add_argument(
        "--imports",
        type=str,
        metavar="FILE",
        help="Show import dependency graph for a Python file"
    )

    # Security and Research commands
    parser.add_argument(
        "--security-audit",
        action="store_true",
        help="Run comprehensive security audit on workspace"
    )

    parser.add_argument(
        "--scan-secrets",
        action="store_true",
        help="Scan workspace for exposed secrets and credentials"
    )

    parser.add_argument(
        "--audit-deps",
        action="store_true",
        help="Audit dependencies for known vulnerabilities"
    )

    parser.add_argument(
        "--research",
        type=str,
        metavar="TOPIC",
        help="Research a topic using web search and documentation"
    )

    parser.add_argument(
        "--budget",
        action="store_true",
        help="Show current token budget status"
    )

    parser.add_argument(
        "--configure",
        action="store_true",
        help="Launch interactive configuration wizard"
    )

    return parser


class CLIAgent:
    """CLI wrapper for the agent with caching integration."""

    def __init__(
        self,
        config_path: Optional[str] = None,
        model: Optional[str] = None,
        workspace: Optional[str] = None,
        enable_cache: bool = True,
        token_limit: int = 100000,
        verbose: bool = False
    ):
        self.config_path = config_path
        self.model = model
        self.workspace = Path(workspace) if workspace else Path.cwd()
        self.enable_cache = enable_cache
        self.token_limit = token_limit
        self.verbose = verbose

        # Initialize caching
        self.caching = None
        if enable_cache:
            self.caching = create_caching(
                str(self.workspace),
                daily_token_limit=token_limit
            )

        # Initialize agent
        self.agent: Optional[Agent] = None

        # Initialize approval manager
        self.approval_manager: Optional[ApprovalManager] = None
        if APPROVAL_AVAILABLE:
            try:
                self.approval_manager = ApprovalManager(self.agent.config if self.agent else Config())
            except Exception:
                pass  # Approval manager optional

        # Initialize prompt toolkit session for tab completion
        self.prompt_session = None
        self.interactive_mode = False
        
        if PROMPT_TOOLKIT_AVAILABLE:
            try:
                # Create history file in user's local app data
                history_path = Path.home() / '.local' / 'share' / 'rapidwebs-agent' / 'cli_history'
                history_path.parent.mkdir(parents=True, exist_ok=True)
                
                self.prompt_session = PromptSession(
                    completer=COMMAND_COMPLETER,
                    complete_while_typing=True,
                    enable_history_search=True,
                    mouse_support=False,
                    complete_in_thread=True,
                    history=FileHistory(str(history_path)),
                    key_bindings=bindings,
                )
                self.interactive_mode = True
            except Exception as e:
                if verbose:
                    console.print(f"[dim]Note: Advanced terminal features unavailable: {e}[/dim]")
                self.interactive_mode = False

    def _run_preflight_checks(self) -> bool:
        """Run pre-flight checks for caching and memory systems.
        
        This runs at the start of every session to ensure MCP tools are ready.
        Returns True if all critical checks pass.
        """
        if not self.caching:
            console.print("[dim]⚠ Caching disabled, skipping pre-flight checks[/dim]\n")
            return False
        
        console.print("\n[bold cyan]🔍 Running Pre-Flight Checks...[/bold cyan]")
        
        checks_passed = 0
        checks_total = 3
        
        # Check 1: Token Budget Status
        try:
            budget_report = self.caching.budget.get_usage_report()
            daily_limit = budget_report.get('daily_limit', 0)
            used_today = budget_report.get('used_today', 0)
            remaining = daily_limit - used_today
            usage_percent = (used_today / daily_limit * 100) if daily_limit > 0 else 0
            
            if usage_percent < 70:
                status = "✓"
                checks_passed += 1
            elif usage_percent < 90:
                status = "⚠"
                checks_passed += 1
            else:
                status = "❌"
            
            console.print(f"  {status} Token Budget: {used_today:,}/{daily_limit:,} ({usage_percent:.1f}% used, {remaining:,} remaining)")
        except Exception as e:
            console.print(f"  ❌ Token Budget: Check failed - {e}")
        
        # Check 2: Response Cache Status
        try:
            cache_stats = self.caching.responses.get_stats()
            cache_entries = cache_stats.get('entries', 0)
            hit_rate = cache_stats.get('hit_rate', '0.0%')

            # hit_rate is already a string like '0.0%'
            console.print(f"  ✓ Response Cache: {cache_entries} entries, {hit_rate} hit rate")
            checks_passed += 1
        except Exception as e:
            console.print(f"  ⚠ Response Cache: Status unavailable - {e}")
        
        # Check 3: Memory Skill Status
        # Note: Python agent has its own MemorySkill (not MCP - that's Qwen Code CLI only)
        try:
            if self.agent and hasattr(self.agent, 'skill_manager'):
                memory_skill = self.agent.skill_manager.registry.get('memory')
                if memory_skill and getattr(memory_skill, 'enabled', False):
                    memory_path = memory_skill.storage_path
                    if memory_path.exists():
                        try:
                            conn = sqlite3.connect(str(memory_path))
                            cursor = conn.cursor()
                            cursor.execute("SELECT COUNT(*) FROM entities")
                            entity_count = cursor.fetchone()[0]
                            conn.close()
                            console.print(f"  ✓ Memory: {entity_count} entities at {memory_path}")
                        except:
                            console.print(f"  ✓ Memory: Database at {memory_path}")
                        checks_passed += 1
                    else:
                        console.print(f"  ✓ Memory: Database will be created on first use")
                        checks_passed += 1
                else:
                    # Memory skill not registered
                    console.print(f"  ⚠ Memory: Skill not registered")
            else:
                console.print(f"  ⚠ Memory: Agent not initialized")
        except Exception as e:
            console.print(f"  ⚠ Memory: Check failed - {e}")
        
        # Summary
        console.print(f"\n[dim]Pre-flight: {checks_passed}/{checks_total} checks passed[/dim]\n")
        
        return checks_passed >= 2  # At least 2 of 3 checks should pass
    
    def initialize(self):
        """Initialize the agent."""
        try:
            # Build CLI args dict for configuration layer
            cli_config = {
                'model': self.model,
                'workspace': self.workspace,
                'no_cache': not self.enable_cache,
                'token_limit': self.token_limit,
                'verbose': self.verbose
            }

            self.agent = Agent(config_path=self.config_path, cli_args=cli_config)

            # Override model if specified (already handled by config layers)
            if self.model and not self.agent.config.get('default_model') == self.model:
                self.agent.config.set('default_model', self.model)

            # Initialize approval manager from agent
            if APPROVAL_AVAILABLE and hasattr(self.agent, 'approval_manager') and self.agent.approval_manager:
                self.approval_manager = self.agent.approval_manager
                console.print(f"[dim]Approval workflow enabled (current mode: {self.approval_manager.mode.value})[/dim]")

            # Run pre-flight checks for caching and memory (NEW)
            self._run_preflight_checks()

            # Disable streaming if requested
            if self.verbose:
                console.print(f"[dim]Working directory: {self.workspace}[/dim]")
                console.print(f"[dim]Cache enabled: {self.enable_cache}[/dim]")
                console.print(f"[dim]Token limit: {self.token_limit:,}[/dim]")

        except Exception as e:
            console.print(f"[red]Error initializing agent: {e}[/red]")
            if self.verbose:
                import traceback
                console.print(traceback.format_exc())
            # Cleanup caching resources if initialization failed
            if self.caching:
                try:
                    # Any cleanup needed
                    pass
                except Exception:
                    pass
            sys.exit(1)

    def run_task(self, task: str) -> int:
        """Run a single task."""
        if not self.agent:
            self.initialize()

        try:
            # Check cache first
            if self.caching:
                cached_response = self.caching.check_and_get_cached(
                    prompt=task,
                    model=self.agent.model_manager.current_model,
                    files=[]
                )
                if cached_response:
                    console.print(Panel(
                        cached_response,
                        title="Cached Response",
                        style="green"
                    ))
                    return 0

            # Run task
            console.print(f"\n[cyan]Processing:[/cyan] {task}\n")

            # Use agent's run method
            result = asyncio.run(self._run_agent_task(task))

            # Cache result if caching enabled
            if self.caching and result and result.get('success'):
                # Use tracked files for cache invalidation
                accessed_files = result.get('accessed_files', [])
                self.caching.cache_response_and_record_usage(
                    prompt=task,
                    model=self.agent.model_manager.current_model,
                    files=accessed_files,  # NOW tracking files!
                    response=result.get('output', ''),
                    tokens=result.get('tokens_used', 0)
                )

            return 0

        except KeyboardInterrupt:
            console.print("\n[yellow]Task interrupted.[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if self.verbose:
                import traceback
                console.print(traceback.format_exc())
            return 1

    async def _run_agent_task(self, task: str) -> dict:
        """Run agent task asynchronously."""
        # This integrates with the agent's core functionality
        # The actual implementation depends on agent.core structure
        return await self.agent.run(task)

    def run_interactive(self) -> int:
        """Run interactive mode."""
        if not self.agent:
            self.initialize()

        print_banner()
        print_welcome()
        
        # Show tab completion status
        if self.interactive_mode:
            console.print("[dim]✓ Tab completion enabled (use cmd.exe or PowerShell for best results)[/dim]\n")
        else:
            console.print("[dim]Note: Using basic input mode (tab completion unavailable)[/dim]\n")

        try:
            while True:
                try:
                    # Get user input using prompt_toolkit if available
                    if self.interactive_mode and self.prompt_session:
                        try:
                            user_input = self.prompt_session.prompt(
                                [('class:prompt', '\nYou: ')]
                            )
                            if user_input is None:  # EOF/Ctrl+D
                                break
                            user_input = user_input.strip()
                        except EOFError:
                            break
                        except KeyboardInterrupt:
                            console.print("\n[yellow]Use /exit to quit[/yellow]")
                            continue
                    else:
                        # Fallback to basic input
                        try:
                            user_input = console.input("[bold cyan]You:[/bold cyan] ")
                            if user_input is None:  # EOF
                                break
                            user_input = user_input.strip()
                        except EOFError:
                            break

                    if not user_input:
                        continue

                    # Handle commands (both with / prefix and special commands without)
                    if user_input.startswith('/'):
                        cmd_result = self._handle_command(user_input)
                        if cmd_result == 'exit':
                            break
                        continue
                    
                    # Handle special commands without / prefix
                    if user_input.lower().startswith('subagents'):
                        cmd_result = self._handle_command(user_input)
                        if cmd_result == 'exit':
                            break
                        continue

                    # Run task
                    console.print("\n[bold cyan]Agent:[/bold cyan]")

                    # Check cache first in interactive mode too
                    if self.caching:
                        model_name = self.agent.model_manager.current_model
                        cached_response = self.caching.check_and_get_cached(
                            prompt=user_input,
                            model=model_name,
                            files=[]  # TODO: Track files accessed during task
                        )
                        if cached_response:
                            console.print("\n[green]✓ Cached response:[/green]")
                            console.print(cached_response)
                            continue

                    result = asyncio.run(self._run_agent_task(user_input))

                    # Cache result if caching enabled
                    if self.caching and result and result.get('success'):
                        model_name = self.agent.model_manager.current_model
                        # Use tracked files for cache invalidation
                        accessed_files = result.get('accessed_files', [])
                        self.caching.cache_response_and_record_usage(
                            prompt=user_input,
                            model=model_name,
                            files=accessed_files,  # NOW tracking files!
                            response=result.get('output', ''),
                            tokens=result.get('tokens_used', 0)
                        )

                    # Display result
                    if result and result.get('output'):
                        console.print(result['output'])

                    # Show token usage if available
                    if result and result.get('tokens_used'):
                        console.print(f"\n[dim]Tokens used: {result['tokens_used']:,}[/dim]")

                except KeyboardInterrupt:
                    console.print("\n[yellow]Use /exit to quit[/yellow]")
                    continue

        except Exception as e:
            console.print(f"[red]Fatal error: {e}[/red]")
            if self.verbose:
                import traceback
                console.print(traceback.format_exc())
            return 1

        # Save conversation on exit
        if self.agent:
            self.agent.conversation.save()
            console.print("\n[green]Conversation saved.[/green]")

        return 0

    def _handle_command(self, command: str) -> str:
        """Handle slash commands."""
        parts = command.split()
        cmd = parts[0].lower()

        if cmd in ['/exit', '/quit', '/q']:
            return 'exit'

        elif cmd == '/help':
            self._show_help()

        elif cmd == '/clear':
            if self.agent:
                self.agent.conversation.clear()
                console.print("[green]Conversation cleared.[/green]")

        elif cmd == '/history':
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            else:
                conversations = self.agent.conversation.list_conversations()
                if not conversations:
                    console.print("[yellow]No saved conversations found.[/yellow]")
                else:
                    console.print(Panel(
                        f"[bold]Saved Conversations ({len(conversations)}):[/bold]\n\n" +
                        '\n'.join([
                            f"  [cyan]{i+1}.[/cyan] [bold]{conv['id']}[/bold]\n"
                            f"     📅 {conv['date']} | 💬 {conv['message_count']} messages\n"
                            f"     [dim]First: {conv['first_message'][:60]}...[/dim]"
                            for i, conv in enumerate(conversations[-10:])
                        ]) +
                        "\n\n[dim]💡 Resume with: /resume <conversation_id>[/dim]",
                        title="📜 Conversation History",
                        border_style="cyan"
                    ))

        elif cmd == '/resume':
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            elif len(parts) < 2:
                console.print("[red]Usage: /resume <conversation_id>[/red]")
                console.print("[dim]Example: /resume conversation_20260307_143022[/dim]")
                console.print("[dim]Use /history to see available conversations[/dim]")
            else:
                conversation_id = parts[1]
                success = self.agent.conversation.load_conversation(conversation_id)
                if success:
                    console.print(f"[green]✓ Resumed conversation: {conversation_id}[/green]")
                    console.print(f"[dim]Loaded {len(self.agent.conversation.history)} messages[/dim]")
                else:
                    console.print(f"[red]Failed to resume conversation: {conversation_id}[/red]")
                    console.print("[dim]Use /history to see available conversations[/dim]")

        elif cmd == '/export':
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            else:
                format = parts[1].lower() if len(parts) > 1 else 'markdown'
                output_file = parts[2] if len(parts) > 2 else None
                
                if format not in ['markdown', 'json', 'text']:
                    console.print("[red]Invalid format. Use: markdown, json, or text[/red]")
                else:
                    content = self.agent.conversation.export(format)
                    
                    if output_file:
                        output_path = Path(output_file)
                    else:
                        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                        extensions = {'markdown': 'md', 'json': 'json', 'text': 'txt'}
                        output_path = Path(f"conversation_export_{timestamp}.{extensions[format]}")
                    
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    
                    console.print(f"[green]✓ Exported conversation to: {output_path}[/green]")

        elif cmd == '/search':
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            elif len(parts) < 2:
                console.print("[red]Usage: /search <query>[/red]")
                console.print("[dim]Example: /search database migration[/dim]")
            else:
                query = ' '.join(parts[1:])
                results = self.agent.conversation.search(query)
                
                if not results:
                    console.print(f"[yellow]No results found for: {query}[/yellow]")
                else:
                    console.print(Panel(
                        f"[bold]Search Results for '{query}'[/bold] ({len(results)} found)\n\n" +
                        '\n'.join([
                            f"  [cyan]#{i+1}[/cyan] [{r['role']}]\n"
                            f"  {r['content'][:150]}...\n"
                            f"  [dim]Position: message {r['index']}[/dim]\n"
                            for i, r in enumerate(results[:5])
                        ]),
                        title="🔍 Search Results",
                        border_style="cyan"
                    ))

        elif cmd == '/compress':
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            else:
                console.print("[yellow]Compressing conversation...[/yellow]")
                with console.status("[bold]Summarizing with LLM..."):
                    summary, usage = asyncio.run(self.agent.conversation.compress(
                        self.agent.model_manager.generate
                    ))
                
                if usage:
                    console.print("[green]✓ Conversation compressed![/green]")
                    console.print(Panel(
                        summary,
                        title="📝 Summary",
                        border_style="green",
                        title_align="left"
                    ))
                else:
                    console.print(f"[yellow]{summary}[/yellow]")

        elif cmd == '/memory':
            # Handle memory commands
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            elif len(parts) < 2:
                console.print(Panel(
                    "[bold]Memory Commands:[/bold]\n\n"
                    "  [cyan]/memory create <type> <name> [content][/cyan]\n"
                    "      Create a new memory entity\n\n"
                    "  [cyan]/memory get <type> <name>[/cyan]\n"
                    "      Retrieve a memory entity\n\n"
                    "  [cyan]/memory list [type][/cyan]\n"
                    "      List all memories (optionally filtered by type)\n\n"
                    "  [cyan]/memory delete <type> <name>[/cyan]\n"
                    "      Delete a memory entity\n\n"
                    "  [cyan]/memory search <query>[/cyan]\n"
                    "      Search memories by content\n\n"
                    "  [cyan]/memory stats[/cyan]\n"
                    "      Show memory statistics\n\n"
                    "[dim]Types: concept, fact, code, pattern, decision, note[/dim]",
                    title="🧠 Memory System",
                    border_style="cyan"
                ))
            else:
                subcommand = parts[1].lower()
                
                if subcommand == 'create' and len(parts) >= 4:
                    mem_type = parts[2]
                    mem_name = parts[3]
                    mem_content = ' '.join(parts[4:]) if len(parts) > 4 else ""
                    
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='create_entity',
                        name=mem_name,
                        type=mem_type,
                        content=mem_content
                    ))
                    
                    if result.get('success'):
                        console.print(f"[green]✓ Created memory: {mem_type}/{mem_name}[/green]")
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'get' and len(parts) >= 4:
                    mem_type = parts[2]
                    mem_name = parts[3]
                    
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='get_entity',
                        name=mem_name,
                        type=mem_type
                    ))
                    
                    if result.get('success'):
                        entity = result['entity']
                        console.print(Panel(
                            f"[bold]Name:[/bold] {entity['name']}\n"
                            f"[bold]Type:[/bold] {entity['type']}\n"
                            f"[bold]Content:[/bold]\n{entity['content']}\n"
                            f"[dim]Accessed: {entity['access_count']} times[/dim]",
                            title=f"🧠 Memory: {entity['name']}",
                            border_style="green"
                        ))
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'list':
                    mem_type = parts[2] if len(parts) > 2 else None
                    
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='list_entities',
                        type=mem_type
                    ))
                    
                    if result.get('success'):
                        entities = result['entities']
                        if not entities:
                            console.print("[yellow]No memories found.[/yellow]")
                        else:
                            console.print(Panel(
                                f"[bold]Memories ({len(entities)}):[/bold]\n\n" +
                                '\n'.join([
                                    f"  [cyan]{e['type']}[/cyan]/[bold]{e['name']}[/bold] - [dim]accessed {e['access_count']}x[/dim]"
                                    for e in entities
                                ]),
                                title="🧠 Memory List",
                                border_style="cyan"
                            ))
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'delete' and len(parts) >= 4:
                    mem_type = parts[2]
                    mem_name = parts[3]
                    
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='delete_entity',
                        name=mem_name,
                        type=mem_type
                    ))
                    
                    if result.get('success'):
                        console.print(f"[green]✓ Deleted memory: {mem_type}/{mem_name}[/green]")
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'search' and len(parts) >= 3:
                    query = ' '.join(parts[2:])
                    
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='search',
                        query=query
                    ))
                    
                    if result.get('success'):
                        results = result['results']
                        if not results:
                            console.print(f"[yellow]No memories found for: {query}[/yellow]")
                        else:
                            console.print(Panel(
                                f"[bold]Search Results ({len(results)}):[/bold]\n\n" +
                                '\n'.join([
                                    f"  [cyan]{r['type']}[/cyan]/[bold]{r['name']}[/bold]\n"
                                    f"  [dim]{r['content'][:100]}...[/dim]\n"
                                    for r in results
                                ]),
                                title=f"🔍 Search: {query}",
                                border_style="cyan"
                            ))
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'stats':
                    result = asyncio.run(self.agent.skill_manager.execute(
                        'memory',
                        action='query',
                        query_type='stats'
                    ))
                    
                    if result.get('success'):
                        console.print(Panel(
                            f"[bold]Total Entities:[/bold] {result['total_entities']}\n"
                            f"[bold]Total Relations:[/bold] {result['total_relations']}\n\n"
                            f"[bold]By Type:[/bold]\n" +
                            '\n'.join([
                                f"  [cyan]{k}[/cyan]: {v}"
                                for k, v in result['entities_by_type'].items()
                            ]),
                            title="🧠 Memory Statistics",
                            border_style="green"
                        ))
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                else:
                    console.print("[red]Invalid memory command. Use /memory for help.[/red]")

        elif cmd == '/todo':
            # Handle TODO commands
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            elif not hasattr(self.agent, 'todo_skill'):
                console.print("[red]TODO system not available. Make sure TodoSkill is imported.[/red]")
            elif len(parts) < 2:
                # Show TODO help
                console.print(Panel(
                    "[bold]TODO Commands:[/bold]\n\n"
                    "  [cyan]/todo add <description>[/cyan]\n"
                    "      Add a new TODO item\n\n"
                    "  [cyan]/todo list[/cyan]\n"
                    "      List all TODOs (shows current state)\n\n"
                    "  [cyan]/todo toggle[/cyan]\n"
                    "      Toggle TODO panel visibility (or use Ctrl+T)\n\n"
                    "  [cyan]/todo done <index>[/cyan]\n"
                    "      Mark a TODO as completed (1-based index)\n\n"
                    "  [cyan]/todo in-progress <index>[/cyan]\n"
                    "      Mark a TODO as in progress\n\n"
                    "  [cyan]/todo clear[/cyan]\n"
                    "      Remove completed TODOs\n\n"
                    "  [cyan]/todo stats[/cyan]\n"
                    "      Show TODO statistics\n\n"
                    "  [cyan]/todo export [format][/cyan]\n"
                    "      Export TODOs (json, markdown, text)\n\n"
                    "[dim]Tip: Use Ctrl+T to quickly toggle TODO visibility[/dim]",
                    title="📋 TODO System",
                    border_style="cyan"
                ))
            else:
                subcommand = parts[1].lower()
                todo_skill = self.agent.todo_skill
                
                if subcommand in ['add', 'create']:
                    # Add new TODO
                    if len(parts) < 3:
                        console.print("[red]Usage: /todo add <description>[/red]")
                    else:
                        description = ' '.join(parts[2:])
                        result = asyncio.run(todo_skill.execute('create', description=description))
                        
                        if result.get('success'):
                            console.print(f"[green]✓ Added TODO: {description}[/green]")
                            console.print(f"[dim]Total tasks: {result.get('total', 0)}[/dim]")
                        else:
                            console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'list':
                    # List all TODOs
                    result = asyncio.run(todo_skill.execute('list'))
                    
                    if result.get('success'):
                        from agent.ui_components import TodoListPanel
                        tasks = result.get('tasks', [])
                        
                        if not tasks:
                            console.print("[yellow]No TODOs yet. Add one with /todo add <description>[/yellow]")
                        else:
                            # Show TODO panel
                            panel = TodoListPanel.from_todo_skill_result(
                                result,
                                title='📋 Current Tasks',
                                collapsed=False,
                                max_visible=15
                            )
                            panel.render(console)
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'toggle':
                    # Toggle TODO visibility (placeholder - actual toggle needs UI state)
                    result = asyncio.run(todo_skill.execute('list'))
                    
                    if result.get('success'):
                        tasks = result.get('tasks', [])
                        
                        if not tasks:
                            console.print("[yellow]No TODOs yet. Add one with /todo add <description>[/yellow]")
                        else:
                            from agent.ui_components import TodoListPanel
                            # Toggle between collapsed and expanded
                            collapsed = hasattr(self, '_todo_collapsed') and self._todo_collapsed
                            self._todo_collapsed = not collapsed
                            
                            panel = TodoListPanel.from_todo_skill_result(
                                result,
                                title='📋 Current Tasks',
                                collapsed=self._todo_collapsed
                            )
                            panel.render(console)
                            
                            if self._todo_collapsed:
                                console.print("[dim]TODO panel collapsed. Press Ctrl+T to expand.[/dim]")
                            else:
                                console.print("[dim]TODO panel expanded. Press Ctrl+T to collapse.[/dim]")
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'done':
                    # Mark as completed
                    if len(parts) < 3:
                        console.print("[red]Usage: /todo done <index>[/red]")
                        console.print("[dim]Use /todo list to see indexes[/dim]")
                    else:
                        try:
                            index = int(parts[2]) - 1  # 1-based to 0-based
                            result = asyncio.run(todo_skill.execute('update', index=index, status='completed'))
                            
                            if result.get('success'):
                                console.print(f"[green]✓ Marked task {parts[2]} as completed[/green]")
                            else:
                                console.print(f"[red]Error: {result.get('error')}[/red]")
                        except (ValueError, IndexError):
                            console.print(f"[red]Invalid index: {parts[2]}[/red]")
                
                elif subcommand == 'in-progress':
                    # Mark as in progress
                    if len(parts) < 3:
                        console.print("[red]Usage: /todo in-progress <index>[/red]")
                    else:
                        try:
                            index = int(parts[2]) - 1
                            result = asyncio.run(todo_skill.execute('update', index=index, status='in_progress'))
                            
                            if result.get('success'):
                                console.print(f"[green]✓ Marked task {parts[2]} as in progress[/green]")
                            else:
                                console.print(f"[red]Error: {result.get('error')}[/red]")
                        except (ValueError, IndexError):
                            console.print(f"[red]Invalid index: {parts[2]}[/red]")
                
                elif subcommand == 'clear':
                    # Clear completed
                    result = asyncio.run(todo_skill.execute('clear', keep_incomplete=True))
                    
                    if result.get('success'):
                        console.print(f"[green]✓ Removed {result.get('removed', 0)} completed tasks[/green]")
                        console.print(f"[dim]Remaining: {result.get('remaining', 0)} tasks[/dim]")
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'stats':
                    # Show statistics
                    result = asyncio.run(todo_skill.execute('stats'))
                    
                    if result.get('success'):
                        stats = result.get('stats', {})
                        by_status = stats.get('by_status', {})
                        
                        console.print(Panel(
                            f"[bold]Total Tasks:[/bold] {stats.get('total', 0)}\n"
                            f"[bold]Completion Rate:[/bold] {stats.get('completion_rate', 0)}%\n\n"
                            f"[bold]By Status:[/bold]\n"
                            f"  ⏸ Pending: {by_status.get('pending', 0)}\n"
                            f"  ⏳ In Progress: {by_status.get('in_progress', 0)}\n"
                            f"  ✓ Completed: {by_status.get('completed', 0)}\n"
                            f"  ✗ Cancelled: {by_status.get('cancelled', 0)}",
                            title="📊 TODO Statistics",
                            border_style="green"
                        ))
                    else:
                        console.print(f"[red]Error: {result.get('error')}[/red]")
                
                elif subcommand == 'export':
                    # Export TODOs
                    format = parts[2].lower() if len(parts) > 2 else 'json'
                    
                    if format not in ['json', 'markdown', 'text']:
                        console.print("[red]Invalid format. Use: json, markdown, or text[/red]")
                    else:
                        result = asyncio.run(todo_skill.execute('export', format=format))
                        
                        if result.get('success'):
                            console.print(f"[green]✓ Exported TODOs to: {result.get('path')}[/green]")
                        else:
                            console.print(f"[red]Error: {result.get('error')}[/red]")
                
                else:
                    console.print("[red]Unknown TODO command. Use /todo for help.[/red]")

        elif cmd == '/expand-output':
            # Expand collapsed tool output
            if not self.agent or not hasattr(self.agent, 'ui'):
                console.print("[red]Agent not initialized[/red]")
            elif hasattr(self.agent.ui, 'expand_last_output'):
                self.agent.ui.expand_last_output()
            else:
                console.print("[yellow]Expand/collapse not available in this session[/yellow]")

        elif cmd == '/collapse-output':
            # Collapse expanded tool output
            if not self.agent or not hasattr(self.agent, 'ui'):
                console.print("[red]Agent not initialized[/red]")
            elif hasattr(self.agent.ui, 'collapse_last_output'):
                self.agent.ui.collapse_last_output()
            else:
                console.print("[yellow]Expand/collapse not available in this session[/yellow]")

        elif cmd == '/project':
            # Handle project analysis commands
            if not self.agent:
                console.print("[red]Agent not initialized[/red]")
            elif len(parts) < 2:
                console.print(Panel(
                    "[bold]Project Commands:[/bold]\n\n"
                    "  [cyan]/project detect[/cyan]\n"
                    "      Detect project type and show summary\n\n"
                    "  [cyan]/project skeleton[/cyan]\n"
                    "      Generate full project skeleton\n\n"
                    "  [cyan]/project tools[/cyan]\n"
                    "      Suggest missing tools for this project\n\n"
                    "  [cyan]/project languages[/cyan]\n"
                    "      List detected languages\n\n"
                    "[dim]Analyzes workspace to help LLM understand project structure[/dim]",
                    title="📁 Project Analysis",
                    border_style="cyan"
                ))
            else:
                subcommand = parts[1].lower()
                
                try:
                    from agent.project_detector import ProjectTypeDetector
                    detector = ProjectTypeDetector()
                    workspace = Path.cwd()
                    
                    if subcommand == 'detect':
                        info = detector.detect(workspace)
                        
                        console.print(Panel(
                            f"[bold]Project Type:[/bold] [cyan]{info.project_type}[/cyan]\n"
                            f"[bold]Confidence:[/bold] {info.confidence:.0%}\n"
                            f"[bold]Name:[/bold] {info.name}\n"
                            f"[bold]Version:[/bold] {info.version or 'N/A'}\n"
                            f"[bold]Description:[/bold] {info.description or 'N/A'}\n\n"
                            f"[bold]Languages:[/bold] {', '.join(sorted(info.languages)) if info.languages else 'None detected'}\n"
                            f"[bold]Frameworks:[/bold] {', '.join(sorted(info.frameworks)) if info.frameworks else 'None detected'}\n\n"
                            f"[bold]Entry Points:[/bold] {', '.join(info.entry_points) if info.entry_points else 'None found'}\n"
                            f"[bold]Key Files:[/bold] {', '.join(info.key_files[:5]) if info.key_files else 'None'}\n\n"
                            f"[bold]Recommended Tools:[/bold] {', '.join(info.tools_needed) if info.tools_needed else 'None'}",
                            title="📁 Project Detection",
                            border_style="green",
                            title_align="left"
                        ))
                    
                    elif subcommand == 'skeleton':
                        skeleton = detector.generate_skeleton(workspace)
                        
                        console.print(Panel(
                            skeleton['summary'],
                            title="📁 Project Summary",
                            border_style="green"
                        ))
                        
                        structure = skeleton['structure'][:30]  # Limit display
                        if structure:
                            console.print(Panel(
                                "[bold]Project Structure:[/bold]\n\n" +
                                '\n'.join([
                                    f"  {'📁' if item['type'] == 'directory' else '📄'} {item['path']}"
                                    for item in structure
                                ]) +
                                (f"\n\n[dim]... and {len(structure) - 30} more items[/dim]" if len(skeleton['structure']) > 30 else ""),
                                title="📂 Structure",
                                border_style="cyan"
                            ))
                    
                    elif subcommand == 'tools':
                        info = detector.detect(workspace)
                        
                        if info.tools_needed:
                            console.print(Panel(
                                "[bold]Recommended Tools:[/bold]\n\n" +
                                '\n'.join([
                                    f"  [cyan]•[/cyan] {tool}"
                                    for tool in info.tools_needed
                                ]) +
                                f"\n\n[dim]Install with: pip install {' '.join(info.tools_needed[:3])}[/dim]",
                                title="🔧 Tool Suggestions",
                                border_style="yellow"
                            ))
                        else:
                            console.print("[green]✓ No additional tools recommended.[/green]")
                    
                    elif subcommand == 'languages':
                        info = detector.detect(workspace)
                        
                        if info.languages:
                            console.print(Panel(
                                "[bold]Detected Languages:[/bold]\n\n" +
                                '\n'.join([
                                    f"  [cyan]•[/cyan] {lang}"
                                    for lang in sorted(info.languages)
                                ]),
                                title="🌐 Languages",
                                border_style="cyan"
                            ))
                        else:
                            console.print("[yellow]No specific languages detected.[/yellow]")
                    
                    else:
                        console.print("[red]Invalid project command. Use /project for help.[/red]")
                
                except ImportError as e:
                    console.print(f"[red]Error: Project detector not available - {e}[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {str(e)}[/red]")

        elif cmd == '/stats':
            self._show_stats()

        elif cmd == '/model':
            if len(parts) > 1:
                model_name = parts[1]
                if self.agent:
                    # Switch model
                    self.agent.config.set('default_model', model_name)
                    console.print(f"[green]Switched to model: {model_name}[/green]")
            else:
                # Show current model
                if self.agent:
                    current = self.agent.config.default_model
                    console.print(f"Current model: [cyan]{current}[/cyan]")
                    console.print("Available models: qwen_coder, gemini")

        elif cmd == '/cache':
            if self.caching:
                stats = self.caching.get_all_stats()
                self._display_cache_stats(stats)
            else:
                console.print("[yellow]Caching is disabled.[/yellow]")

        elif cmd == '/budget':
            # Show token budget status
            if self.caching:
                stats = self.caching.get_all_stats()
                daily_limit = self.token_limit
                current_usage = stats.get('total_tokens_processed', 0)
                remaining = max(0, daily_limit - current_usage)
                percentage = (current_usage / daily_limit * 100) if daily_limit > 0 else 0
                
                # Determine color based on usage
                if percentage >= 90:
                    color = "red"
                    status = "⚠️ CRITICAL"
                elif percentage >= 80:
                    color = "yellow"
                    status = "⚠️ WARNING"
                elif percentage >= 50:
                    color = "cyan"
                    status = "✓ MODERATE"
                else:
                    color = "green"
                    status = "✓ HEALTHY"
                
                console.print(Panel(
                    f"[bold {color}]{status}[/bold {color}]\n\n"
                    f"[bold]Current Usage:[/bold]    [yellow]{current_usage:,}[/yellow] / {daily_limit:,} tokens\n"
                    f"[bold]Percentage:[/bold]      [{color}]{percentage:.1f}%[/{color}]\n"
                    f"[bold]Remaining:[/bold]       [green]{remaining:,} tokens[/green]\n"
                    f"[bold]Cache Hits:[/bold]      [green]{stats.get('cache_hits', 0)}[/green]\n"
                    f"[bold]Cache Misses:[/bold]    [yellow]{stats.get('cache_misses', 0)}[/yellow]",
                    title="📊 Token Budget Status",
                    border_style=color,
                    title_align="left"
                ))
            else:
                console.print(f"[bold]Token Budget:[/bold] {self.token_limit:,} tokens/day")
                console.print("[dim]Enable caching for detailed tracking[/dim]")

        elif cmd == '/version':
            # Show version information
            from importlib.metadata import version, PackageNotFoundError
            try:
                pkg_version = version('rapidwebs-agent')
            except PackageNotFoundError:
                pkg_version = '1.0.0 (dev)'
            
            console.print(Panel(
                f"[bold cyan]RapidWebs Agent[/bold cyan]\n\n"
                f"[bold]Version:[/bold]  [green]{pkg_version}[/green]\n"
                f"[bold]Python:[/bold]   {sys.version.split()[0]}\n"
                f"[bold]Platform:[/bold] {sys.platform}",
                title="ℹ️ Version Information",
                border_style="cyan",
                title_align="left"
            ))

        elif cmd == '/configure':
            # Launch configuration wizard
            try:
                from agent.configuration_wizard import ConfigWizard
                wizard = ConfigWizard(self.config_path)
                wizard.run()
                console.print("[green]Configuration updated![/green]")
            except ImportError:
                console.print("[yellow]Configuration wizard not available.[/yellow]")
                config_path = self.config_path or Path.home() / '.config' / 'rapidwebs-agent' / 'config.yaml'
                console.print(f"Edit config file directly: [cyan]{config_path}[/cyan]")

        elif cmd == '/subagents' or cmd == 'subagents':
            # Handle subagents commands
            result = asyncio.run(self._handle_subagents_command(command))
            if result:
                console.print(result)

        elif cmd == '/mode':
            # Handle approval mode switching
            if not APPROVAL_AVAILABLE or not self.approval_manager:
                console.print("[yellow]Approval workflow not available.[/yellow]")
            elif len(parts) > 1:
                mode_str = parts[1].lower()
                try:
                    new_mode = ApprovalMode(mode_str)
                    self.approval_manager.mode = new_mode
                    console.print(f"[green]✓ Switched to [bold]{new_mode.value}[/bold] mode[/green]")
                    
                    # Show mode description
                    mode_descriptions = {
                        'plan': "Read-only mode - no tool execution allowed",
                        'default': "Confirm all write/destructive operations",
                        'auto-edit': "Auto-accept edits, confirm destructive operations",
                        'yolo': "No confirmations - full automation"
                    }
                    console.print(f"[dim]{mode_descriptions.get(mode_str, '')}[/dim]")
                except ValueError:
                    console.print(f"[red]Invalid mode: {mode_str}[/red]")
                    console.print("Available modes: plan, default, auto-edit, yolo")
            else:
                # Show current mode
                if self.approval_manager:
                    current_mode = self.approval_manager.mode
                    console.print(f"Current approval mode: [bold cyan]{current_mode.value}[/bold cyan]")
                    console.print("\n[bold]Available modes:[/bold]")
                    console.print("  [cyan]plan[/cyan]       - Read-only, no tool execution")
                    console.print("  [cyan]default[/cyan]    - Confirm write/destructive ops")
                    console.print("  [cyan]auto-edit[/cyan]  - Auto-accept edits")
                    console.print("  [cyan]yolo[/cyan]       - No confirmations")
                    console.print("\n[dim]Usage: /mode <name> (e.g., /mode yolo)[/dim]")
                    console.print("\n[dim]Keyboard shortcuts: Ctrl+P (plan), Ctrl+D (default), Ctrl+A (auto-edit), Ctrl+Y (yolo)[/dim]")

        else:
            console.print(f"[red]Unknown command: {cmd}[/red]")
            console.print("Type /help for available commands.")

        return 'continue'

    def _show_help(self):
        """Show help message with all available commands."""
        help_text = """
# 🚀 RapidWebs Agent - Command Reference

## Basic Commands

| Command | Description |
|---------|-------------|
| `/help` | Show this help message |
| `/exit`, `/quit`, `/q` | Exit the agent (conversation auto-saved) |
| `/clear` | Clear conversation history |
| `/stats` | Show session statistics with token budget dashboard |
| `/version` | Show version information |
| `/configure` | Launch interactive configuration wizard |

## Conversation Management

| Command | Description |
|---------|-------------|
| `/history` | List saved conversations with date and message count |
| `/resume <id>` | Resume a saved conversation (use `/history` to find IDs) |
| `/export [format]` | Export conversation (markdown, json, text) |
| `/search <query>` | Search conversation history |
| `/compress` | Compress conversation using LLM summarization |

## Memory System 🧠

| Command | Description |
|---------|-------------|
| `/memory` | Show memory command reference |
| `/memory create <type> <name> [content]` | Create a memory entity |
| `/memory get <type> <name>` | Retrieve a memory |
| `/memory list [type]` | List all memories (optionally filtered by type) |
| `/memory delete <type> <name>` | Delete a memory entity |
| `/memory search <query>` | Search memories by content |
| `/memory stats` | Show memory statistics |

**Memory Types:** `concept`, `fact`, `code`, `pattern`, `decision`, `note`

## TODO System 📋

| Command | Description |
|---------|-------------|
| `/todo` | Show TODO command reference |
| `/todo add <description>` | Add a new TODO item |
| `/todo list` | List all TODOs with status indicators |
| `/todo toggle` | Toggle TODO panel visibility (or use `Ctrl+T`) |
| `/todo done <index>` | Mark TODO as completed |
| `/todo in-progress <index>` | Mark TODO as in progress |
| `/todo clear` | Remove completed TODOs |
| `/todo stats` | Show completion statistics |
| `/todo export [format]` | Export TODOs (json, markdown, text) |

## Output Management 📺

| Command | Description |
|---------|-------------|
| `/expand-output` | Expand collapsed tool output (or press `e`) |
| `/collapse-output` | Collapse expanded tool output (or press `c`) |

## Project Analysis 📊

| Command | Description |
|---------|-------------|
| `/project` | Show project analysis command reference |
| `/project detect` | Detect project type and show summary |
| `/project skeleton` | Generate full project skeleton |
| `/project tools` | Suggest missing tools for detected languages |
| `/project languages` | List all detected languages in workspace |

## Model Management 🤖

| Command | Description |
|---------|-------------|
| `/model` | Show current model and available models |
| `/model list` | List all available models |
| `/model switch <name>` | Switch to a different model |
| `/model stats` | Show model-specific statistics |

## Cache & Budget 💾

| Command | Description |
|---------|-------------|
| `/cache` | Show cache statistics (hits, misses, tokens saved) |
| `/budget` | Show token budget status with progress bar |

## Approval Modes 🛡️

| Command | Description |
|---------|-------------|
| `/mode` | Show current mode and available modes |
| `/mode plan` | Read-only mode (no tool execution) |
| `/mode default` | Confirm all write/destructive operations (recommended) |
| `/mode auto-edit` | Auto-accept edits, confirm destructive operations |
| `/mode yolo` | No confirmations, full automation (use with caution!) |

## SubAgents 🤖

| Command | Description |
|---------|-------------|
| `/subagents` or `subagents` | Show subagent command reference |
| `subagents list` | List available subagent types |
| `subagents status` | Show subagent system status |
| `subagents run <type> <task>` | Run a subagent task |

**SubAgent Types:** `code`, `test`, `docs`, `research`, `security`

**Example:** `subagents run code "Refactor main.py to use async/await"`

## Keyboard Shortcuts ⌨️

| Shortcut | Action |
|----------|--------|
| `Ctrl+P` | Switch to Plan mode |
| `Ctrl+D` | Switch to Default mode |
| `Ctrl+A` | Switch to Auto-Edit mode |
| `Ctrl+Y` | Switch to YOLO mode |
| `Ctrl+L` | Clear screen |
| `Ctrl+V` | Show version |
| `Ctrl+T` | Toggle TODO list |
| `Ctrl+C` | Interrupt current operation |
| `e` | Expand collapsed tool output (when input is empty) |
| `c` | Collapse expanded tool output (when input is empty) |

## Usage Tips 💡

1. **Reference files:** Use `@filename` to reference specific files (e.g., `Fix bugs in @main.py`)
2. **Be specific:** "Refactor `utils.py` to use async/await" is better than "Improve the code"
3. **Break down tasks:** Complex tasks work better when split into smaller steps
4. **Monitor tokens:** Use `/stats` and `/budget` to track token usage in real-time
5. **Choose mode wisely:**
   - `/mode plan` for safe exploration and understanding
   - `/mode default` for normal development (recommended)
   - `/mode auto-edit` for rapid iteration on known-safe changes
   - `/mode yolo` for trusted, repetitive tasks (use with caution!)
6. **Save tokens:** Use `/compress` on long conversations to reduce context size
7. **Continue work:** Use `/history` and `/resume` to pick up where you left off
8. **Track tasks:** Use `/todo add` to keep track of action items during complex work

## CLI Commands (Terminal)

Run these directly from your terminal (not inside the agent):

| Command | Description |
|---------|-------------|
| `rw-agent --format FILE` | Format a code file |
| `rw-agent --lint FILE` | Lint a code file |
| `rw-agent --symbols FILE` | Show symbols in a Python file |
| `rw-agent --related FILE` | Find related files |
| `rw-agent --callers FUNCTION` | Find all callers of a function |
| `rw-agent --imports FILE` | Show import dependency graph |
| `rw-agent --check-tools` | Check installed code tools |
| `rw-agent --install-tools` | Install Tier 1 code tools (ruff, prettier) |
| `rw-agent --scan-workspace` | Detect languages in workspace |
| `rw-agent --security-audit` | Run security audit on workspace |
| `rw-agent --scan-secrets` | Scan for exposed secrets/credentials |
| `rw-agent --audit-deps` | Audit dependencies for vulnerabilities |
| `rw-agent --research TOPIC` | Research a topic using web search |

## Environment Variables

| Variable | Description |
|----------|-------------|
| `RW_QWEN_API_KEY` | Qwen Coder API key (required) |
| `RW_GEMINI_API_KEY` | Gemini API key (optional) |
| `RW_DAILY_TOKEN_LIMIT` | Daily token budget (default: 100000) |
        """
        console.print(Markdown(help_text))

    def _show_stats(self):
        """Show usage statistics."""
        if not self.agent:
            return

        # Get agent stats
        stats = {
            'Total Tokens': getattr(self.agent, 'total_tokens', 0),
            'Total Cost': f"${getattr(self.agent, 'total_cost', 0.0):.4f}",
            'Model': self.agent.config.default_model,
        }

        # Add cache stats if available
        if self.caching:
            cache_stats = self.caching.get_all_stats()
            stats['Cache Hits'] = cache_stats.get('cache_hits', 0)
            stats['Cache Misses'] = cache_stats.get('cache_misses', 0)
            stats['Tokens Saved'] = cache_stats.get('estimated_tokens_saved', 0)

        # Display
        console.print("\n[bold]Session Statistics:[/bold]")
        for key, value in stats.items():
            console.print(f"  {key}: [cyan]{value}[/cyan]")

    def _display_cache_stats(self, stats: dict):
        """Display cache statistics."""
        console.print("\n[bold]Cache Statistics:[/bold]")
        console.print(f"  Hits: [green]{stats.get('cache_hits', 0)}[/green]")
        console.print(f"  Misses: [yellow]{stats.get('cache_misses', 0)}[/yellow]")
        console.print(f"  Hit Rate: [cyan]{stats.get('hit_rate', 0):.1%}[/cyan]")
        console.print(f"  Estimated Tokens Saved: [green]{stats.get('estimated_tokens_saved', 0):,}[/green]")
        console.print(f"  Cache Size: {stats.get('cache_size', 0)} entries")

    async def _handle_subagents_command(self, command: str) -> str:
        """Handle subagents commands by delegating to the agent.

        Args:
            command: The full command string (e.g., 'subagents list', 'subagents run code ...')

        Returns:
            Result message to display
        """
        if not self.agent:
            return "[red]Agent not initialized. Please wait for initialization to complete.[/red]"

        # Check if subagents are available (check orchestrator directly)
        if not hasattr(self.agent, 'subagent_orchestrator') or not self.agent.subagent_orchestrator:
            return (
                "❌ **SubAgents system is not available.**\n\n"
                "💡 The agent may not have subagents support enabled.\n"
                "Check that `agent.subagents` module is properly installed."
            )

        # Delegate to agent's handler
        try:
            result = await self.agent._handle_subagent_command(command)
            return result
        except asyncio.CancelledError:
            return "⏱️ **Subagent command cancelled.**"
        except Exception as e:
            if self.verbose:
                import traceback
                traceback.print_exc()
            return f"❌ **Error:** {str(e)}\n\n💡 Try `subagents list` to see available agents."



def show_stats(config_path: Optional[str] = None):
    """Show usage statistics."""
    console.print("[bold]RapidWebs Agent - Usage Statistics[/bold]\n")

    # Try to load from config
    config = Config(config_path)

    # Show model info
    console.print(f"Default Model: [cyan]{config.default_model}[/cyan]")

    # Show API key status
    for model_name, env_var in Config.API_KEY_ENV_VARS.items():
        has_key = bool(os.environ.get(env_var) or config.get(f'models.{model_name}.api_key'))
        status = "[green]✓ Configured[/green]" if has_key else "[red]✗ Not configured[/red]"
        console.print(f"  {model_name}: {status}")

    console.print()


# =============================================================================
# NEW: Code Analysis CLI Commands (Phase 2)
# =============================================================================

def show_symbols_cli(file_path: str):
    """Show symbols in a Python file."""
    from agent import get_file_symbols

    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return 1
    
    if not path.is_file():
        console.print(f"[red]Not a file: {file_path}[/red]")
        return 1

    if path.suffix != '.py':
        console.print(f"[yellow]Warning: Not a Python file ({path.suffix})[/yellow]")

    symbols = get_file_symbols(path)

    if not symbols:
        console.print(f"[yellow]No symbols found in {file_path}[/yellow]")
        return 0
    
    # Group by type
    functions = [s for s in symbols if s['type'] == 'function']
    classes = [s for s in symbols if s['type'] == 'class']
    imports = [s for s in symbols if s['type'] == 'import']
    
    console.print(f"[bold]Symbols in {file_path}[/bold]\n")
    
    # Show imports
    if imports:
        console.print("[cyan]Imports:[/cyan]")
        for sym in imports:
            console.print(f"  {sym['signature']}")
        console.print()
    
    # Show classes
    if classes:
        console.print("[cyan]Classes:[/cyan]")
        for sym in classes:
            console.print(f"  {sym['signature']} (line {sym['line']})")
        console.print()
    
    # Show functions
    if functions:
        console.print("[cyan]Functions:[/cyan]")
        for sym in functions:
            console.print(f"  {sym['signature']} (line {sym['line']})")
    
    console.print(f"\n[dim]Total: {len(symbols)} symbols ({len(classes)} classes, {len(functions)} functions, {len(imports)} imports)[/dim]")
    return 0


def show_related_files_cli(file_path: str):
    """Show files related to a given file."""
    from agent import suggest_related_files
    
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return 1
    
    workspace = Path.cwd()
    suggestions = suggest_related_files(path, workspace, max_suggestions=10)
    
    if not suggestions:
        console.print(f"[yellow]No related files found for {file_path}[/yellow]")
        return 0
    
    console.print(f"[bold]Files related to {file_path}[/bold]\n")
    
    # Categorize suggestions
    test_files = [s for s in suggestions if 'test' in s.name.lower()]
    siblings = [s for s in suggestions if s.parent == path.parent and s != path]
    others = [s for s in suggestions if s not in test_files and s not in siblings]
    
    if test_files:
        console.print("[cyan]Test Files:[/cyan]")
        for f in test_files:
            try:
                rel = f.relative_to(workspace)
                console.print(f"  [green]✓[/green] {rel}")
            except ValueError:
                console.print(f"  [green]✓[/green] {f}")
        console.print()
    
    if siblings:
        console.print("[cyan]Same Directory:[/cyan]")
        for f in siblings[:5]:
            try:
                rel = f.relative_to(workspace)
                console.print(f"  {rel}")
            except ValueError:
                console.print(f"  {f}")
        console.print()
    
    if others:
        console.print("[cyan]Other Related:[/cyan]")
        for f in others[:5]:
            try:
                rel = f.relative_to(workspace)
                console.print(f"  {rel}")
            except ValueError:
                console.print(f"  {f}")
    
    return 0


def find_callers_cli(function_name: str):
    """Find all callers of a function."""
    from agent import find_callers
    
    workspace = Path.cwd()
    callers = find_callers(function_name, workspace, max_results=20)
    
    if not callers:
        console.print(f"[yellow]No callers found for '{function_name}'[/yellow]")
        return 0
    
    console.print(f"[bold]Callers of '{function_name}'[/bold]\n")
    
    # Group by file
    by_file = {}
    for file_path, line_num, content in callers:
        if file_path not in by_file:
            by_file[file_path] = []
        by_file[file_path].append((line_num, content))
    
    for file_path, calls in sorted(by_file.items()):
        try:
            rel_path = Path(file_path).relative_to(workspace)
        except ValueError:
            rel_path = file_path
        
        console.print(f"[cyan]{rel_path}:[/cyan]")
        for line_num, content in calls:
            # Truncate long lines
            if len(content) > 80:
                content = content[:77] + "..."
            console.print(f"  [dim]{line_num}:[/dim] {content}")
        console.print()
    
    console.print(f"[dim]Total: {len(callers)} callers found[/dim]")
    return 0


def show_imports_cli(file_path: str):
    """Show import dependency graph for a Python file."""
    from agent import get_import_graph
    
    path = Path(file_path)
    if not path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        return 1
    
    if path.suffix != '.py':
        console.print(f"[yellow]Warning: Not a Python file ({path.suffix})[/yellow]")
    
    workspace = Path.cwd()
    imports = get_import_graph(path, workspace)
    
    if not imports:
        console.print(f"[yellow]No imports found in {file_path}[/yellow]")
        return 0
    
    console.print(f"[bold]Import graph for {file_path}[/bold]\n")
    
    # Group by module
    by_module = {}
    for name, module in imports.items():
        if module not in by_module:
            by_module[module] = []
        by_module[module].append(name)
    
    # Show as tree
    for module, names in sorted(by_module.items()):
        if len(names) == 1:
            console.print(f"[cyan]{names[0]}[/cyan] from [green]{module}[/green]")
        else:
            console.print(f"[green]{module}[/green]:")
            for name in names:
                console.print(f"  [cyan]{name}[/cyan]")
    
    console.print(f"\n[dim]Total: {len(imports)} imports from {len(by_module)} modules[/dim]")
    return 0


def show_budget_status_cli(config_path: Optional[str], token_limit: int):
    """Show current token budget status."""
    from agent import Config
    
    config = Config(config_path)
    daily_limit = config.get('performance.token_budget', token_limit)
    
    # Try to get current usage from environment or config
    # For now, show the limit and suggest checking /stats in interactive mode
    console.print("[bold]Token Budget Status[/bold]\n")
    
    console.print(f"Daily Limit: [cyan]{daily_limit:,} tokens[/cyan]")
    console.print("\n[dim]Note: For real-time usage, run 'rw-agent' and use /stats command[/dim]")
    console.print("[dim]Or run 'rw-agent --stats' for session statistics[/dim]")
    
    return 0


# =============================================================================
# Code Tools CLI Commands (existing)
# =============================================================================


def check_code_tools():
    """Check which code tools are installed."""
    if not CODE_TOOLS_AVAILABLE:
        console.print("[red]Code tools module not available[/red]")
        return

    tools = CodeTools()
    status = tools.get_all_tools_status()

    console.print("[bold]Code Tools Status[/bold]\n")

    table = Table(title="Installed Code Tools")
    table.add_column("Tool", style="cyan")
    table.add_column("Language", style="green")
    table.add_column("Purpose", style="yellow")
    table.add_column("Version", style="white")
    table.add_column("Status", justify="right")

    for tool_name, info in sorted(status.items()):
        status_icon = "✓" if info['installed'] else "✗"
        status_style = "green" if info['installed'] else "red"
        version = info.get('version', 'N/A') or 'N/A'
        # Truncate long version strings
        if len(version) > 40:
            version = version[:37] + "..."

        table.add_row(
            tool_name,
            info['language'],
            info['purpose'],
            version,
            f"[{status_style}]{status_icon}[/{status_style}]"
        )

    console.print(table)

    # Show installation hints
    console.print("\n[bold]Installation Commands:[/bold]")
    console.print("  [cyan]pip install ruff[/cyan]                    # Python (bundled)")
    console.print("  [cyan]npm install -g prettier[/cyan]             # JS/TS/JSON/YAML/MD/CSS")
    console.print("  [cyan]go install golang.org/x/tools/cmd/goimports@latest[/cyan]  # Go")
    console.print("  [cyan]rustup component add rustfmt[/cyan]        # Rust")
    console.print("  [cyan]go install mvdan.cc/sh/v3/cmd/shfmt@latest[/cyan]  # Shell")
    console.print("  [cyan]pip install sqlfluff[/cyan]                # SQL")


def install_code_tools():
    """Install Tier 1 code tools with auto-detection."""
    console.print("[bold]Installing Tier 1 Code Tools[/bold]\n")

    if not CODE_TOOLS_AVAILABLE:
        console.print("[red]Code tools module not available[/red]")
        return

    tools = CodeTools()

    # Auto-detect workspace languages
    console.print("Scanning workspace for languages...")
    languages = tools.detect_workspace_languages('.', max_files=100)

    if languages:
        lang_list = ', '.join(f"{lang} ({count})" for lang, count in sorted(languages.items(), key=lambda x: -x[1])[:5])
        console.print(f"[green]✓ Detected:[/green] {lang_list}")
    else:
        console.print("[dim]No specific languages detected (will install common tools)[/dim]")

    # Check what's missing
    missing_info = tools.get_missing_tools(list(languages.keys()) if languages else None)

    # Ruff is always bundled
    console.print("\n[green]✓ ruff[/green] (Python linting/formatting) - bundled with rapidwebs-agent")

    # Check if prettier is needed and missing
    if 'prettier' in missing_info['missing']:
        console.print("\nInstalling prettier (JavaScript/TypeScript/JSON/YAML/Markdown/CSS/HTML)...")
        result = tools.install_tool('prettier')

        if result.get('success'):
            if result.get('already_installed'):
                console.print("[green]✓ prettier already installed[/green]")
            else:
                console.print("[green]✓ prettier installed successfully[/green]")
        else:
            error = result.get('error', 'Unknown error')
            console.print("[yellow]⚠ prettier installation failed[/yellow]")
            console.print(f"  Error: {error[:200] if error else 'Unknown'}")
            console.print("  Install manually: [cyan]npm install -g prettier[/cyan]")
    else:
        console.print("[green]✓ prettier[/green] already installed")

    # Show Tier 2 tools if detected
    if missing_info['missing']:
        tier2_missing = [t for t in missing_info['missing'] if tools.get_tool_tier(t) == 2]
        if tier2_missing:
            console.print("\n[yellow]Tier 2 tools detected but not installed:[/yellow]")
            for tool in tier2_missing:
                cmd = tools.get_install_command(tool)
                console.print(f"  [cyan]{tool}[/cyan]: {cmd}")
            console.print("\nRun [cyan]rw-agent --install-tier2[/cyan] for installation instructions")

    console.print("\n[green]Tier 1 tools ready![/green]")
    console.print("\nUsage:")
    console.print("  [cyan]rw-agent --format file.py[/cyan]    # Format a file")
    console.print("  [cyan]rw-agent --lint file.py[/cyan]      # Lint a file")
    console.print("  [cyan]rw-agent --scan-workspace[/cyan]    # Detect languages")
    console.print("  [cyan]rw-agent --check-tools[/cyan]       # Check tool status")


def format_file_cli(file_path: str):
    """Format a file and print result."""
    if not CODE_TOOLS_AVAILABLE:
        console.print("[red]Code tools module not available[/red]")
        return 1

    tools = CodeTools()
    result = tools.format_file(file_path, check_only=False)

    if result.success:
        console.print(f"[green]✓ Formatted: {file_path}[/green]")
        if result.output:
            console.print(result.output)
        if result.files_modified:
            console.print(f"[dim]Files modified: {', '.join(result.files_modified)}[/dim]")
        console.print(f"[dim]Duration: {result.duration_ms:.0f}ms[/dim]")
        return 0
    else:
        console.print(f"[red]✗ Format failed: {file_path}[/red]")
        if result.errors:
            console.print(f"[red]{result.errors}[/red]")
        return 1


def lint_file_cli(file_path: str):
    """Lint a file and print diagnostics."""
    if not CODE_TOOLS_AVAILABLE:
        console.print("[red]Code tools module not available[/red]")
        return 1

    tools = CodeTools()
    result = tools.lint_file(file_path)

    if result.success:
        if result.diagnostics:
            console.print(f"[yellow]⚠ Found {len(result.diagnostics)} issue(s): {file_path}[/yellow]")
            for diag in result.diagnostics[:20]:  # Show first 20
                line = diag.get('line', '?')
                code = diag.get('code', '')
                message = diag.get('message', '')
                console.print(f"  [yellow]L{line}:{code}[/yellow] {message}")
            if len(result.diagnostics) > 20:
                console.print(f"  [dim]... and {len(result.diagnostics) - 20} more[/dim]")
        else:
            console.print(f"[green]✓ No issues found: {file_path}[/green]")
        console.print(f"[dim]Duration: {result.duration_ms:.0f}ms[/dim]")
        return 0
    else:
        console.print(f"[red]✗ Lint failed: {file_path}[/red]")
        if result.errors:
            console.print(f"[red]{result.errors}[/red]")
        return 1


def scan_workspace():
    """Scan workspace for languages and suggest missing tools."""
    if not CODE_TOOLS_AVAILABLE:
        console.print("[red]Code tools module not available[/red]")
        return


    tools = CodeTools()

    console.print("[bold]Scanning Workspace for Code Languages...[/bold]\n")

    # Detect languages
    languages = tools.detect_workspace_languages('.', max_files=200)

    if not languages:
        console.print("[yellow]No code files detected in current directory[/yellow]")
        return

    # Display detected languages
    table = Table(title="Detected Languages")
    table.add_column("Language", style="cyan")
    table.add_column("Files", justify="right", style="green")
    table.add_column("Required Tool", style="yellow")
    table.add_column("Status", style="white")

    language_tools_map = {
        'python': 'ruff',
        'javascript': 'prettier',
        'typescript': 'prettier',
        'json': 'prettier',
        'yaml': 'prettier',
        'markdown': 'prettier',
        'css': 'prettier',
        'html': 'prettier',
        'go': 'gofmt',
        'rust': 'rustfmt',
        'shell': 'shfmt',
        'sql': 'sqlfluff',
    }

    for lang, count in sorted(languages.items(), key=lambda x: -x[1]):
        tool = language_tools_map.get(lang, 'unknown')
        installed = tools.check_tool_installed(tool) if tool != 'unknown' else False
        status = "[green]✓ Installed[/green]" if installed else "[red]✗ Missing[/red]"

        table.add_row(
            lang.capitalize(),
            str(count),
            tool,
            status
        )

    console.print(table)

    # Show missing tools
    missing_info = tools.get_missing_tools(list(languages.keys()))

    if missing_info['missing']:
        console.print("\n[bold red]Missing Tools:[/bold red]")
        for tool in missing_info['missing']:
            tier = tools.get_tool_tier(tool)
            cmd = tools.get_install_command(tool)

            if tier == 1:
                console.print(f"  [cyan]{tool}[/cyan] (Tier 1) - [yellow]{cmd}[/yellow]")
            else:
                console.print(f"  [cyan]{tool}[/cyan] (Tier 2) - [dim]{cmd}[/dim]")

        console.print("\n[yellow]Tip:[/yellow] Run [cyan]rw-agent --install-tools[/cyan] to auto-install Tier 1 tools")
        console.print("      Run [cyan]rw-agent --install-tier2[/cyan] for Tier 2 installation instructions")
    else:
        console.print("\n[green]✓ All required tools are installed![/green]")


def install_tier2_tools():
    """Show installation instructions for Tier 2 tools."""
    console.print("[bold]Tier 2 Tools Installation Guide[/bold]\n")

    console.print("Tier 2 tools are language-specific and installed only when needed.\n")

    table = Table(title="Tier 2 Tools")
    table.add_column("Language", style="cyan")
    table.add_column("Tool", style="green")
    table.add_column("Installation Command", style="yellow")
    table.add_column("When to Install", style="white")

    tier2_tools = [
        ("Go", "gofmt", "Built-in with Go", "Install Go from https://go.dev/"),
        ("Rust", "rustfmt", "rustup component add rustfmt", "When writing Rust code"),
        ("Shell", "shfmt", "go install mvdan.cc/sh/v3/cmd/shfmt@latest", "For shell script formatting"),
        ("SQL", "sqlfluff", "pip install sqlfluff", "For SQL linting/formatting"),
    ]

    for lang, tool, cmd, when in tier2_tools:
        table.add_row(lang, tool, cmd, when)

    console.print(table)

    console.print("\n[dim]Note: Tier 2 tools are optional. Install only when working with these languages.[/dim]")


# =============================================================================
# Security and Research CLI Commands
# =============================================================================

def run_security_audit():
    """Run comprehensive security audit using SecurityAgent."""
    console.print("[bold cyan]🔒 Running Comprehensive Security Audit...[/bold cyan]\n")

    try:
        from agent.subagents import SecurityAgent, SubAgentTask, SubAgentType
        from agent.config import Config

        config = Config()
        agent = SecurityAgent()

        # Create audit task
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Run comprehensive security audit",
            context={'type': 'full_audit', 'workspace': str(Path.cwd())}
        )

        console.print("[dim]Scanning for:[/dim]")
        console.print("  - 🔴 Vulnerable dependencies")
        console.print("  - 🟠 Code security issues (OWASP Top 10)")
        console.print("  - 🟡 Exposed secrets and credentials")
        console.print()

        # Run audit (synchronous for CLI)
        import asyncio
        result = asyncio.run(agent.execute(task))

        if result.success():
            console.print(result.output)
            return 0
        else:
            console.print(f"[red]Audit failed: {result.error}[/red]")
            return 1

    except ImportError:
        console.print("[red]SecurityAgent not available[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Error running security audit: {e}[/red]")
        import traceback
        console.print(traceback.format_exc())
        return 1


def scan_secrets_cli():
    """Scan workspace for exposed secrets."""
    console.print("[bold cyan]🔍 Scanning for Exposed Secrets and Credentials...[/bold cyan]\n")

    try:
        from agent.subagents import SecurityAgent, SubAgentTask, SubAgentType

        agent = SecurityAgent()
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Scan for secrets and credentials",
            context={'type': 'secret_scan', 'workspace': str(Path.cwd())}
        )

        import asyncio
        result = asyncio.run(agent.execute(task))

        if result.success():
            console.print(result.output)
            return 0
        else:
            console.print(f"[red]Scan failed: {result.error}[/red]")
            return 1

    except Exception as e:
        console.print(f"[red]Error scanning for secrets: {e}[/red]")
        return 1


def audit_deps_cli():
    """Audit dependencies for vulnerabilities."""
    console.print("[bold cyan]📦 Auditing Dependencies for Known Vulnerabilities...[/bold cyan]\n")

    try:
        from agent.subagents import SecurityAgent, SubAgentTask, SubAgentType

        agent = SecurityAgent()
        task = SubAgentTask.create(
            SubAgentType.SECURITY,
            "Audit dependencies",
            context={'type': 'dependency_audit', 'workspace': str(Path.cwd())}
        )

        import asyncio
        result = asyncio.run(agent.execute(task))

        if result.success():
            console.print(result.output)
            return 0
        else:
            console.print(f"[red]Audit failed: {result.error}[/red]")
            return 1

    except Exception as e:
        console.print(f"[red]Error auditing dependencies: {e}[/red]")
        return 1


def research_topic_cli(topic: str):
    """Research a topic using ResearchAgent."""
    console.print(f"[bold cyan]🔬 Researching: {topic}[/bold cyan]\n")

    try:
        from agent.subagents import ResearchAgent, SubAgentTask, SubAgentType

        agent = ResearchAgent()
        task = SubAgentTask.create(
            SubAgentType.RESEARCH,
            f"Research: {topic}",
            context={'query': topic}
        )

        import asyncio
        result = asyncio.run(agent.execute(task))

        if result.success():
            console.print(result.output)
            return 0
        else:
            console.print(f"[red]Research failed: {result.error}[/red]")
            return 1

    except Exception as e:
        console.print(f"[red]Error researching topic: {e}[/red]")
        return 1


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle code tools commands
    if args.check_tools:
        check_code_tools()
        return 0

    if args.install_tools:
        install_code_tools()
        return 0

    if args.install_tier2:
        install_tier2_tools()
        return 0

    if args.scan_workspace:
        scan_workspace()
        return 0

    if args.format:
        return format_file_cli(args.format)

    if args.lint:
        return lint_file_cli(args.lint)

    # NEW: Handle code analysis commands (Phase 2)
    if args.symbols:
        return show_symbols_cli(args.symbols)

    if args.related:
        return show_related_files_cli(args.related)

    if args.callers:
        return find_callers_cli(args.callers)

    if args.imports:
        return show_imports_cli(args.imports)

    # Handle security and research commands
    if args.security_audit:
        return run_security_audit()

    if args.scan_secrets:
        return scan_secrets_cli()

    if args.audit_deps:
        return audit_deps_cli()

    if args.research:
        return research_topic_cli(args.research)

    if args.budget:
        return show_budget_status_cli(args.config, args.token_limit)

    # Handle --configure (interactive configuration wizard)
    if args.configure:
        try:
            from agent.configuration_wizard import ConfigWizard
            wizard = ConfigWizard(args.config)
            return 0 if wizard.run() else 1
        except ImportError:
            console.print("[red]Configuration wizard not available. Please edit config file directly.[/red]")
            return 1

    # Handle --stats
    if args.stats:
        show_stats(args.config)
        return 0

    # Create CLI agent
    cli = CLIAgent(
        config_path=args.config,
        model=args.model,
        workspace=args.workspace,
        enable_cache=not args.no_cache,
        token_limit=args.token_limit,
        verbose=args.verbose
    )

    # Run in appropriate mode
    if args.task:
        # Non-interactive mode
        return cli.run_task(args.task)
    else:
        # Interactive mode
        return cli.run_interactive()


if __name__ == "__main__":
    sys.exit(main())
