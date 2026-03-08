"""Interactive configuration wizard for RapidWebs Agent.

Provides a user-friendly TUI for configuring rw-agent on-the-fly
with real-time validation and helpful descriptions.
"""
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from typing import Dict, Any, Optional
import yaml
from pathlib import Path


console = Console()


class ConfigWizard:
    """Interactive configuration wizard with TUI."""

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._default_config_path()
        self.config: Dict[str, Any] = {}
        self._load_config()

    def _default_config_path(self) -> str:
        config_dir = Path.home() / '.config' / 'rapidwebs-agent'
        config_dir.mkdir(parents=True, exist_ok=True)
        return str(config_dir / 'config.yaml')

    def _load_config(self):
        """Load existing configuration."""
        if Path(self.config_path).exists():
            with open(self.config_path, 'r') as f:
                self.config = yaml.safe_load(f) or {}
        else:
            self.config = {}

    def _save_config(self):
        """Save configuration to disk."""
        with open(self.config_path, 'w') as f:
            yaml.dump(self.config, f, default_flow_style=False, sort_keys=False)
        console.print(f"[green]✓ Configuration saved to {self.config_path}[/green]")

    def display_welcome(self):
        """Display wizard welcome screen."""
        welcome = Panel(
            "[bold cyan]🔧 RapidWebs Agent Configuration Wizard[/bold cyan]\n\n"
            "[green]Interactive setup for your agent preferences[/green]\n\n"
            "This wizard will help you configure:\n"
            "  • LLM Models & API Keys\n"
            "  • Token Budget & Performance\n"
            "  • Skills & Permissions\n"
            "  • User Interface Preferences\n\n"
            "[yellow]Press Ctrl+C at any time to cancel[/yellow]",
            title="[bold]Configuration Wizard v1.0[/bold]",
            border_style="cyan"
        )
        console.print(welcome)
        console.print()

    def display_section(self, title: str, description: str):
        """Display section header."""
        console.print()
        console.print(f"[bold cyan]═══ {title} ═══[/bold cyan]")
        console.print(f"[dim]{description}[/dim]")
        console.print()

    def configure_models(self) -> bool:
        """Configure LLM models interactively."""
        self.display_section(
            "LLM Models",
            "Configure your AI models and API keys"
        )

        models_enabled = []

        # Qwen Coder
        console.print(Panel(
            "[bold]Qwen Coder[/bold] - Primary model (recommended)\n"
            "Free tier: 2000 requests/day\n"
            "Best for: Code generation, refactoring, debugging",
            title="Model 1/5",
            border_style="blue"
        ))

        enable_qwen = Confirm.ask(
            "Enable Qwen Coder?",
            default=self.config.get('models', {}).get('qwen_coder', {}).get('enabled', True)
        )

        if enable_qwen:
            current_key = self.config.setdefault('models', {}).setdefault('qwen_coder', {}).get('api_key', '')
            api_key = Prompt.ask(
                "Qwen API Key",
                default=current_key if current_key else "",
                password=True
            )
            if api_key:
                self.config['models']['qwen_coder'] = {
                    'enabled': True,
                    'api_key': api_key,
                    'base_url': 'https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation',
                    'model': 'qwen-coder',
                    'max_requests_per_day': 2000,
                    'rate_limit': 60,
                    'timeout': 30
                }
                models_enabled.append('qwen_coder')
                console.print("[green]✓ Qwen Coder enabled[/green]")

        console.print()

        # Gemini
        console.print(Panel(
            "[bold]Gemini[/bold] - Alternative model\n"
            "Free tier available\n"
            "Best for: General queries, fallback option",
            title="Model 2/5",
            border_style="blue"
        ))

        enable_gemini = Confirm.ask(
            "Enable Gemini?",
            default=self.config.get('models', {}).get('gemini', {}).get('enabled', False)
        )

        if enable_gemini:
            current_key = self.config.setdefault('models', {}).setdefault('gemini', {}).get('api_key', '')
            api_key = Prompt.ask(
                "Gemini API Key",
                default=current_key if current_key else "",
                password=True
            )
            if api_key:
                self.config['models']['gemini'] = {
                    'enabled': True,
                    'api_key': api_key,
                    'base_url': 'https://generativelanguage.googleapis.com/v1beta/models',
                    'model': 'gemini-2.5-flash',
                    'max_requests_per_day': 1000,
                    'timeout': 30
                }
                models_enabled.append('gemini')
                console.print("[green]✓ Gemini enabled[/green]")

        console.print()

        # OpenAI
        console.print(Panel(
            "[bold]OpenAI[/bold] - GPT-4o, GPT-4 Turbo\n"
            "Paid tier (high quality)\n"
            "Best for: Complex reasoning, premium quality",
            title="Model 3/5",
            border_style="green"
        ))

        enable_openai = Confirm.ask(
            "Enable OpenAI?",
            default=self.config.get('models', {}).get('openai_gpt4o', {}).get('enabled', False)
        )

        if enable_openai:
            current_key = self.config.setdefault('models', {}).setdefault('openai_gpt4o', {}).get('api_key', '')
            api_key = Prompt.ask(
                "OpenAI API Key",
                default=current_key if current_key else "",
                password=True
            )
            if api_key:
                self.config['models']['openai_gpt4o'] = {
                    'enabled': True,
                    'api_key': api_key,
                    'base_url': 'https://api.openai.com/v1',
                    'model': 'gpt-4o',
                    'max_requests_per_day': 1000,
                    'rate_limit': 60,
                    'timeout': 30
                }
                models_enabled.append('openai_gpt4o')
                console.print("[green]✓ OpenAI GPT-4o enabled[/green]")

        console.print()

        # Anthropic
        console.print(Panel(
            "[bold]Anthropic[/bold] - Claude Sonnet\n"
            "Paid tier (excellent for code)\n"
            "Best for: Code generation, long context",
            title="Model 4/5",
            border_style="green"
        ))

        enable_anthropic = Confirm.ask(
            "Enable Anthropic?",
            default=self.config.get('models', {}).get('anthropic_claude_sonnet', {}).get('enabled', False)
        )

        if enable_anthropic:
            current_key = self.config.setdefault('models', {}).setdefault('anthropic_claude_sonnet', {}).get('api_key', '')
            api_key = Prompt.ask(
                "Anthropic API Key",
                default=current_key if current_key else "",
                password=True
            )
            if api_key:
                self.config['models']['anthropic_claude_sonnet'] = {
                    'enabled': True,
                    'api_key': api_key,
                    'base_url': 'https://api.anthropic.com',
                    'model': 'claude-sonnet-4-20250514',
                    'max_requests_per_day': 1000,
                    'rate_limit': 60,
                    'timeout': 30
                }
                models_enabled.append('anthropic_claude_sonnet')
                console.print("[green]✓ Anthropic Claude enabled[/green]")

        console.print()

        # OpenRouter
        console.print(Panel(
            "[bold]OpenRouter[/bold] - 100+ models via single API\n"
            "Pay-per-use (flexible model access)\n"
            "Best for: Trying different models, cost optimization",
            title="Model 5/5",
            border_style="green"
        ))

        enable_openrouter = Confirm.ask(
            "Enable OpenRouter?",
            default=self.config.get('models', {}).get('openrouter', {}).get('enabled', False)
        )

        if enable_openrouter:
            current_key = self.config.setdefault('models', {}).setdefault('openrouter', {}).get('api_key', '')
            api_key = Prompt.ask(
                "OpenRouter API Key",
                default=current_key if current_key else "",
                password=True
            )
            if api_key:
                self.config['models']['openrouter'] = {
                    'enabled': True,
                    'api_key': api_key,
                    'base_url': 'https://openrouter.ai/api/v1',
                    'model': 'anthropic/claude-3.5-sonnet',
                    'max_requests_per_day': 1000,
                    'rate_limit': 60,
                    'timeout': 30
                }
                models_enabled.append('openrouter')
                console.print("[green]✓ OpenRouter enabled (access to 100+ models)[/green]")

        # Set default model
        if models_enabled:
            self.config['default_model'] = models_enabled[0]
            console.print(f"\n[bold]Default model:[/bold] [cyan]{models_enabled[0]}[/cyan]")
            console.print("[dim]Change anytime with: /model switch <name>[/dim]")

        return len(models_enabled) > 0

    def configure_performance(self):
        """Configure performance and token budget settings."""
        self.display_section(
            "Performance & Token Budget",
            "Control token usage and optimize performance"
        )

        perf = self.config.get('performance', {})

        # Token Budget
        console.print("[bold]Daily Token Budget[/bold]")
        console.print("[dim]Controls maximum tokens used per day (resets at midnight UTC)[/dim]")
        console.print("[dim]Recommended: 50,000-200,000 for daily development[/dim]\n")

        current_budget = perf.get('token_budget', 100000)
        token_budget = IntPrompt.ask(
            "Daily token limit",
            default=current_budget
        )
        perf['token_budget'] = token_budget

        # Show budget impact
        if token_budget < 20000:
            console.print("[yellow]⚠️  Warning: Very low budget may limit functionality[/yellow]")
        elif token_budget > 500000:
            console.print("[yellow]⚠️  Note: High budget - monitor usage with /stats[/yellow]")
        else:
            console.print(f"[green]✓ Budget set to {token_budget:,} tokens/day[/green]")

        console.print()

        # Caching
        console.print("[bold]Response Caching[/bold]")
        console.print("[dim]Cache LLM responses to save 60-80% on repeated queries[/dim]\n")

        perf['cache_responses'] = Confirm.ask(
            "Enable response caching?",
            default=perf.get('cache_responses', True)
        )

        if perf['cache_responses']:
            current_ttl = perf.get('cache_ttl', 3600)
            cache_ttl = IntPrompt.ask(
                "Cache duration (seconds)",
                default=current_ttl
            )
            perf['cache_ttl'] = cache_ttl
            console.print(f"[green]✓ Cache TTL set to {cache_ttl}s ({cache_ttl//60} minutes)[/green]")

        console.print()

        # Streaming
        perf['streaming'] = Confirm.ask(
            "Enable streaming responses?",
            default=perf.get('streaming', True)
        )

        # Parallel tool calls
        perf['parallel_tool_calls'] = Confirm.ask(
            "Enable parallel tool calls?",
            default=perf.get('parallel_tool_calls', True)
        )

        if perf['parallel_tool_calls']:
            max_concurrent = IntPrompt.ask(
                "Max concurrent tools",
                default=perf.get('max_concurrent_tools', 5)
            )
            perf['max_concurrent_tools'] = max_concurrent

        self.config['performance'] = perf

    def configure_skills(self):
        """Configure agent skills and permissions."""
        self.display_section(
            "Skills & Permissions",
            "Enable/disable agent capabilities and set security limits"
        )

        skills = self.config.get('skills', {})

        # Terminal Executor
        console.print(Panel(
            "[bold]Terminal Executor[/bold]\n"
            "Allows agent to run shell commands with whitelist\n"
            "Allowed: ls, pwd, cat, grep, find, echo, which, git",
            title="Skill 1/3",
            border_style="green"
        ))

        term_config = skills.get('terminal_executor', {})
        term_config['enabled'] = Confirm.ask(
            "Enable terminal executor?",
            default=term_config.get('enabled', True)
        )

        if term_config['enabled']:
            current_whitelist = term_config.get('whitelist', ['ls', 'pwd', 'cat', 'grep', 'find', 'echo', 'which', 'git'])
            console.print(f"[dim]Current whitelist: {', '.join(current_whitelist)}[/dim]")
            custom_whitelist = Prompt.ask(
                "Custom whitelist (comma-separated, or press Enter to keep current)",
                default=','.join(current_whitelist)
            )
            if custom_whitelist:
                term_config['whitelist'] = [cmd.strip() for cmd in custom_whitelist.split(',')]

            term_config['max_execution_time'] = IntPrompt.ask(
                "Max command execution time (seconds)",
                default=term_config.get('max_execution_time', 30)
            )

        skills['terminal_executor'] = term_config
        console.print()

        # Filesystem
        console.print(Panel(
            "[bold]Filesystem Access[/bold]\n"
            "Allows agent to read/write files\n"
            "Restricted to allowed directories only",
            title="Skill 2/3",
            border_style="green"
        ))

        fs_config = skills.get('filesystem', {})
        fs_config['enabled'] = Confirm.ask(
            "Enable filesystem access?",
            default=fs_config.get('enabled', True)
        )

        if fs_config['enabled']:
            current_dirs = fs_config.get('allowed_directories', ['~', './'])
            console.print(f"[dim]Current directories: {', '.join(current_dirs)}[/dim]")
            custom_dirs = Prompt.ask(
                "Allowed directories (comma-separated, or press Enter to keep current)",
                default=','.join(current_dirs)
            )
            if custom_dirs:
                fs_config['allowed_directories'] = [d.strip() for d in custom_dirs.split(',')]

        skills['filesystem'] = fs_config
        console.print()

        # Web Scraper
        console.print(Panel(
            "[bold]Web Scraper[/bold]\n"
            "Allows agent to fetch and parse web pages\n"
            "Includes SSRF protection",
            title="Skill 3/3",
            border_style="green"
        ))

        web_config = skills.get('web_scraper', {})
        web_config['enabled'] = Confirm.ask(
            "Enable web scraper?",
            default=web_config.get('enabled', True)
        )

        if web_config['enabled']:
            web_config['timeout'] = IntPrompt.ask(
                "Web request timeout (seconds)",
                default=web_config.get('timeout', 10)
            )

        skills['web_scraper'] = web_config

        self.config['skills'] = skills

    def configure_ui(self):
        """Configure user interface preferences."""
        self.display_section(
            "User Interface",
            "Customize the agent's appearance and behavior"
        )

        ui = self.config.get('ui', {})

        ui['show_token_usage'] = Confirm.ask(
            "Show token usage after each response?",
            default=ui.get('show_token_usage', True)
        )

        ui['show_cost_estimates'] = Confirm.ask(
            "Show cost estimates?",
            default=ui.get('show_cost_estimates', True)
        )

        console.print()
        console.print("[bold]Theme Selection[/bold]")
        console.print("[dim]Choose your preferred color theme[/dim]\n")

        themes = ['default', 'monokai', 'dracula', 'nord', 'github-dark']
        current_theme = ui.get('theme', 'default')

        for i, theme in enumerate(themes, 1):
            marker = "✓" if theme == current_theme else " "
            console.print(f"  [{i}] {marker} {theme}")

        try:
            choice = IntPrompt.ask(
                "Select theme (1-5)",
                default=themes.index(current_theme) + 1 if current_theme in themes else 1
            )
            ui['theme'] = themes[choice - 1]
        except (ValueError, IndexError):
            ui['theme'] = 'default'

        console.print()
        console.print("[bold]Output Management[/bold]")
        console.print("[dim]Configure tool output display preferences[/dim]\n")

        ui['collapse_tool_output'] = Confirm.ask(
            "Collapse large tool outputs by default?",
            default=ui.get('collapse_tool_output', True)
        )

        ui['output_preview_lines'] = IntPrompt.ask(
            "Lines to show in collapsed preview",
            default=ui.get('output_preview_lines', 5)
        )

        self.config['ui'] = ui

    def review_configuration(self):
        """Display configuration summary for review."""
        self.display_section(
            "Review Configuration",
            "Verify your settings before saving"
        )

        table = Table(title="Configuration Summary", show_header=True, header_style="bold cyan")
        table.add_column("Category", style="cyan", width=20)
        table.add_column("Setting", style="green", width=30)
        table.add_column("Value", style="white", width=30)

        # Models
        models = self.config.get('models', {})
        for model_name, model_config in models.items():
            if model_config.get('enabled'):
                table.add_row(
                    "Models",
                    model_name.replace('_', ' ').title(),
                    "✓ Enabled"
                )

        # Performance
        perf = self.config.get('performance', {})
        table.add_row(
            "Performance",
            "Token Budget",
            f"{perf.get('token_budget', 100000):,} tokens/day"
        )
        table.add_row(
            "Performance",
            "Caching",
            "✓ On" if perf.get('cache_responses') else "✗ Off"
        )
        table.add_row(
            "Performance",
            "Cache TTL",
            f"{perf.get('cache_ttl', 3600)}s"
        )

        # Skills
        skills = self.config.get('skills', {})
        for skill_name, skill_config in skills.items():
            if skill_config.get('enabled'):
                table.add_row(
                    "Skills",
                    skill_name.replace('_', ' ').title(),
                    "✓ Enabled"
                )

        # UI
        ui = self.config.get('ui', {})
        table.add_row(
            "UI",
            "Collapse Tool Output",
            "✓ On" if ui.get('collapse_tool_output') else "✗ Off"
        )
        table.add_row(
            "UI",
            "Preview Lines",
            str(ui.get('output_preview_lines', 5))
        )

        console.print(table)
        console.print()

        return Confirm.ask("Save this configuration?", default=True)

    def run(self) -> bool:
        """Run the complete configuration wizard."""
        try:
            self.display_welcome()

            if not Confirm.ask("Start configuration?", default=True):
                console.print("[yellow]Configuration cancelled[/yellow]")
                return False

            # Run configuration sections
            if not self.configure_models():
                console.print("[red]✗ At least one model must be enabled[/red]")
                return False

            self.configure_performance()
            self.configure_skills()
            self.configure_ui()

            # Review and save
            if self.review_configuration():
                self._save_config()
                console.print()
                console.print(Panel(
                    "[bold green]✓ Configuration Complete![/bold green]\n\n"
                    "Your settings have been saved. You can:\n"
                    "  • Run [cyan]rw-agent[/cyan] to start using the agent\n"
                    "  • Run [cyan]rw-agent --config[/cyan] to view current settings\n"
                    "  • Run this wizard again anytime with [cyan]rw-agent --configure[/cyan]",
                    title="Success",
                    border_style="green"
                ))
                return True
            else:
                console.print("[yellow]Configuration discarded[/yellow]")
                return False

        except KeyboardInterrupt:
            console.print("\n[yellow]Configuration cancelled by user[/yellow]")
            return False


def quick_configure_token_budget(config_path: Optional[str] = None) -> bool:
    """Quick configuration for token budget only."""
    console.print()
    console.print("[bold cyan]⚙️  Quick Config: Token Budget[/bold cyan]")
    console.print()

    wizard = ConfigWizard(config_path)
    current = wizard.config.get('performance', {}).get('token_budget', 100000)

    console.print(f"Current token budget: [yellow]{current:,}[/yellow] tokens/day")
    console.print()

    new_budget = IntPrompt.ask(
        "New daily token limit",
        default=current
    )

    wizard.config.setdefault('performance', {})['token_budget'] = new_budget
    wizard._save_config()

    console.print(f"[green]✓ Token budget updated to {new_budget:,} tokens/day[/green]")
    return True


def quick_show_config(config_path: Optional[str] = None):
    """Display current configuration in a readable format."""
    wizard = ConfigWizard(config_path)

    console.print()
    console.print(Panel(
        f"[bold]Configuration File:[/bold] {wizard.config_path}",
        border_style="cyan"
    ))
    console.print()

    table = Table(title="Current Configuration", show_header=True, header_style="bold cyan")
    table.add_column("Category", style="cyan")
    table.add_column("Setting", style="green")
    table.add_column("Value", style="white")

    # Default Model
    table.add_row(
        "General",
        "Default Model",
        wizard.config.get('default_model', 'qwen_coder')
    )

    # Models
    models = wizard.config.get('models', {})
    for name, cfg in models.items():
        status = "✓" if cfg.get('enabled') else "✗"
        table.add_row("Models", f"{name} ({cfg.get('model', 'N/A')})", status)

    # Performance
    perf = wizard.config.get('performance', {})
    table.add_row("Performance", "Token Budget", f"{perf.get('token_budget', 100000):,}")
    table.add_row("Performance", "Caching", "✓" if perf.get('cache_responses') else "✗")
    table.add_row("Performance", "Streaming", "✓" if perf.get('streaming') else "✗")

    # Skills
    skills = wizard.config.get('skills', {})
    for name, cfg in skills.items():
        status = "✓" if cfg.get('enabled') else "✗"
        table.add_row("Skills", name.replace('_', ' ').title(), status)

    # UI
    ui = wizard.config.get('ui', {})
    table.add_row("UI", "Theme", ui.get('theme', 'default'))
    table.add_row("UI", "Show Tokens", "✓" if ui.get('show_token_usage') else "✗")

    console.print(table)
    console.print()
