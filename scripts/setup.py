#!/usr/bin/env python3
"""Cross-platform setup script for RapidWebs Agent.

This script handles:
- Python version verification (3.10+)
- uv installation check
- Virtual environment creation
- Dependency installation
- Configuration setup
- Environment variable guidance
- Optional tool installation (ruff, prettier, etc.)

Usage:
    python scripts/setup.py [--force] [--no-venv] [--skip-config]
"""

import argparse
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple

# ANSI color codes for terminal output
class Colors:
    """ANSI color codes for cross-platform terminal colors."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    MAGENTA = "\033[95m"
    CYAN = "\033[96m"
    
    @classmethod
    def disable(cls):
        """Disable colors for non-TTY output."""
        cls.RESET = cls.BOLD = cls.RED = cls.GREEN = cls.YELLOW = ""
        cls.BLUE = cls.MAGENTA = cls.CYAN = ""


# Check if output supports colors
if not sys.stdout.isatty():
    Colors.disable()


def print_header(text: str):
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{text.center(60)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.CYAN}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str):
    """Print success message."""
    print(f"{Colors.GREEN}✓ {text}{Colors.RESET}")


def print_error(text: str):
    """Print error message."""
    print(f"{Colors.RED}✗ {text}{Colors.RESET}")


def print_warning(text: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠ {text}{Colors.RESET}")


def print_info(text: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ {text}{Colors.RESET}")


def run_command(cmd: list, cwd: Optional[Path] = None, check: bool = True) -> Tuple[bool, str]:
    """Run a shell command and return success status and output."""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            shell=(sys.platform == 'win32')
        )
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, f"Command failed: {e}\n{e.stderr}"
    except Exception as e:
        return False, str(e)


def check_python_version() -> bool:
    """Check if Python version is 3.10+."""
    print_info(f"Checking Python version...")
    
    if sys.version_info < (3, 10):
        print_error(f"Python 3.10+ required, found {sys.version_info.major}.{sys.version_info.minor}")
        return False
    
    print_success(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} OK")
    return True


def check_uv() -> bool:
    """Check if uv is installed."""
    print_info("Checking for uv package manager...")
    
    success, output = run_command(["uv", "--version"])
    
    if success:
        print_success(f"uv found: {output}")
        return True
    
    print_warning("uv not found in PATH")
    return False


def install_uv() -> bool:
    """Install uv package manager."""
    print_info("Installing uv...")
    
    # Use official installer
    if sys.platform == 'win32':
        # Windows: Use PowerShell
        install_cmd = [
            "powershell", "-ExecutionPolicy", "ByPass", "-Command",
            "irm https://astral.sh/uv/install.ps1 | iex"
        ]
    else:
        # Unix-like: Use curl
        install_cmd = ["curl", "-LsSf", "https://astral.sh/uv/install.sh", "|", "sh"]
    
    print_warning("uv installation requires manual intervention on some systems")
    print_info("Visit https://docs.astral.sh/uv/getting-started/installation/ for instructions")
    
    return False


def create_venv(project_root: Path, force: bool = False) -> bool:
    """Create virtual environment if it doesn't exist."""
    venv_path = project_root / ".venv"
    
    if venv_path.exists():
        if force:
            print_info(f"Removing existing virtual environment: {venv_path}")
            shutil.rmtree(venv_path)
        else:
            print_success(f"Virtual environment already exists: {venv_path}")
            return True
    
    print_info("Creating virtual environment with uv...")
    
    success, output = run_command(
        ["uv", "venv"],
        cwd=project_root
    )
    
    if success:
        print_success(f"Virtual environment created: {venv_path}")
        return True
    
    print_error(f"Failed to create venv: {output}")
    return False


def install_dependencies(project_root: Path, dev: bool = False) -> bool:
    """Install project dependencies."""
    print_info("Installing dependencies with uv...")
    
    cmd = ["uv", "pip", "sync", "uv.lock"]
    if dev:
        cmd = ["uv", "pip", "install", "-e", ".[dev]"]
    
    success, output = run_command(cmd, cwd=project_root)
    
    if success:
        print_success("Dependencies installed successfully")
        return True
    
    print_error(f"Failed to install dependencies: {output}")
    return False


def setup_configuration(project_root: Path) -> bool:
    """Create default configuration if it doesn't exist."""
    print_info("Setting up configuration...")
    
    # Determine config directory based on platform
    if sys.platform == 'win32':
        config_dir = Path.home() / 'AppData' / 'Roaming' / 'rapidwebs-agent'
    elif sys.platform == 'darwin':
        config_dir = Path.home() / 'Library' / 'Preferences' / 'rapidwebs-agent'
    else:
        config_dir = Path.home() / '.config' / 'rapidwebs-agent'
    
    config_file = config_dir / 'config.yaml'
    
    if config_file.exists():
        print_success(f"Configuration already exists: {config_file}")
        return True
    
    try:
        config_dir.mkdir(parents=True, exist_ok=True)
        
        # Create default config
        default_config = """# RapidWebs Agent Configuration
# Generated by setup script

# LLM Configuration
llm:
  default_model: qwen_coder
  models:
    qwen_coder:
      enabled: true
      # Set RW_QWEN_API_KEY environment variable
    gemini:
      enabled: true
      # Set RW_GEMINI_API_KEY environment variable

# Logging
logging:
  enabled: true
  level: INFO
  console: true
  json_format: false

# Performance
performance:
  token_budget: 100000
  context_optimization: true

# Output Management
output_management:
  enabled: true
  inline_max_bytes: 10240
  summary_max_bytes: 1048576
  max_inline_lines: 50

# TUI Settings
tui:
  theme: dracula
  show_tool_cards: true
  collapsible_results: true

# Approval Workflow
approval_workflow:
  timeout_seconds: 300
  fail_on_timeout: true
  log_decisions: true

# SubAgents
subagents:
  max_concurrent: 3
  enabled: true
"""
        
        config_file.write_text(default_config)
        print_success(f"Configuration created: {config_file}")
        return True
        
    except Exception as e:
        print_error(f"Failed to create configuration: {e}")
        return False


def check_environment_variables() -> dict:
    """Check for required environment variables."""
    print_info("Checking environment variables...")
    
    required = {
        'RW_QWEN_API_KEY': 'Qwen Coder API key (DashScope)',
        'RW_GEMINI_API_KEY': 'Google Gemini API key (optional)',
        'RW_DAILY_TOKEN_LIMIT': 'Daily token budget (default: 100000)',
    }
    
    status = {}
    for var, description in required.items():
        value = os.environ.get(var)
        if value:
            # Mask the value for display
            masked = value[:4] + '...' + value[-4:] if len(value) > 8 else '***'
            print_success(f"{var}: {masked}")
            status[var] = True
        else:
            print_warning(f"{var}: Not set - {description}")
            status[var] = False
    
    return status


def setup_env_file(project_root: Path, env_vars: dict) -> bool:
    """Create .env file with template values."""
    env_file = project_root / '.env.example'
    
    if env_file.exists():
        print_success(f".env.example already exists")
        return True
    
    try:
        env_content = """# RapidWebs Agent Environment Variables
# Copy this file to .env and fill in your values
# cp .env.example .env

# Qwen Coder API Key (required for qwen_coder model)
# Get from: https://dashscope.console.aliyun.com/
RW_QWEN_API_KEY=your_qwen_api_key_here

# Google Gemini API Key (optional, for gemini model)
# Get from: https://makersuite.google.com/app/apikey
RW_GEMINI_API_KEY=your_gemini_api_key_here

# Daily Token Budget (optional, default: 100000)
RW_DAILY_TOKEN_LIMIT=100000

# Brave Search API Key (optional, for web search)
# Get from: https://brave.com/search/api/
BRAVE_API_KEY=your_brave_api_key_here
"""
        env_file.write_text(env_content)
        print_success(f".env.example created: {env_file}")
        return True
        
    except Exception as e:
        print_error(f"Failed to create .env.example: {e}")
        return False


def install_optional_tools(project_root: Path) -> bool:
    """Offer to install optional code tools."""
    print_header("Optional Code Tools")
    
    tools = {
        'ruff': 'Python linter/formatter (recommended)',
        'prettier': 'Code formatter for JS/TS/CSS/JSON (requires Node.js)',
        'sqlfluff': 'SQL linter (requires pip install sqlfluff)',
    }
    
    print_info("Recommended code tools:")
    for tool, desc in tools.items():
        print(f"  - {tool}: {desc}")
    
    print_info("\nThese will be auto-installed when needed, or install manually:")
    print("  uv pip install ruff sqlfluff")
    print("  npm install -g prettier")
    
    return True


def print_next_steps(project_root: Path, venv_path: Path):
    """Print next steps for the user."""
    print_header("Setup Complete! Next Steps:")
    
    # Determine activation command based on platform
    if sys.platform == 'win32':
        activate_cmd = r".venv\Scripts\activate"
        rw_agent_cmd = "rw-agent"
    else:
        activate_cmd = "source .venv/bin/activate"
        rw_agent_cmd = "rw-agent"
    
    print(f"""
{Colors.BOLD}1. Activate the virtual environment:{Colors.RESET}
   {Colors.CYAN}cd {project_root}{Colors.RESET}
   {Colors.GREEN}{activate_cmd}{Colors.RESET}

{Colors.BOLD}2. Set up your API keys:{Colors.RESET}
   - Copy {Colors.CYAN}.env.example{Colors.RESET} to {Colors.CYAN}.env{Colors.RESET}
   - Edit {Colors.CYAN}.env{Colors.RESET} and add your API keys
   - Or set environment variables directly

{Colors.BOLD}3. Launch RapidWebs Agent:{Colors.RESET}
   {Colors.GREEN}{rw_agent_cmd}{Colors.RESET}
   or
   {Colors.GREEN}rw-agent "your task here"{Colors.RESET}

{Colors.BOLD}4. Alternative: Use uv run (no activation needed):{Colors.RESET}
   {Colors.GREEN}uv run rw-agent{Colors.RESET}
   {Colors.GREEN}uv run rw-agent "your task here"{Colors.RESET}

{Colors.BOLD}5. View help:{Colors.RESET}
   {Colors.GREEN}rw-agent --help{Colors.RESET}
   {Colors.GREEN}rw-agent --stats{Colors.RESET}

{Colors.YELLOW}Note:{Colors.RESET} Log files will be created at:
  - Windows: %LOCALAPPDATA%\\rapidwebs-agent\\logs\\
  - macOS: ~/Library/Logs/rapidwebs-agent/
  - Linux: ~/.local/share/rapidwebs-agent/logs/
""")


def main():
    """Main setup function."""
    parser = argparse.ArgumentParser(
        description="RapidWebs Agent Cross-Platform Setup",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup.py              # Standard setup
  python scripts/setup.py --force      # Force recreate venv
  python scripts/setup.py --no-config  # Skip config creation
  python scripts/setup.py --dev        # Install dev dependencies
        """
    )
    
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force recreate virtual environment'
    )
    parser.add_argument(
        '--no-venv',
        action='store_true',
        help='Skip virtual environment creation (use system Python)'
    )
    parser.add_argument(
        '--skip-config',
        action='store_true',
        help='Skip configuration file creation'
    )
    parser.add_argument(
        '--dev', '-d',
        action='store_true',
        help='Install development dependencies'
    )
    parser.add_argument(
        '--no-colors',
        action='store_true',
        help='Disable colored output'
    )
    
    args = parser.parse_args()
    
    if args.no_colors:
        Colors.disable()
    
    # Get project root (parent of scripts directory)
    project_root = Path(__file__).parent.parent.resolve()
    venv_path = project_root / ".venv"
    
    print_header("RapidWebs Agent Setup")
    print_info(f"Project root: {project_root}")
    print_info(f"Platform: {platform.system()} {platform.release()} ({platform.machine()})")
    print_info(f"Python: {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Step 1: Check Python version
    print_header("Step 1: Python Version Check")
    if not check_python_version():
        print_error("\nPlease install Python 3.10 or higher from https://www.python.org/")
        sys.exit(1)
    
    # Step 2: Check/install uv
    print_header("Step 2: UV Package Manager")
    if not check_uv():
        print_warning("\nUV is required for dependency management.")
        print_info("Installing uv...")
        
        if not install_uv():
            print_error("\nPlease install uv manually:")
            print("  Windows: powershell -ExecutionPolicy ByPass -Command \"irm https://astral.sh/uv/install.ps1 | iex\"")
            print("  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh")
            sys.exit(1)
    
    # Step 3: Create virtual environment
    if not args.no_venv:
        print_header("Step 3: Virtual Environment")
        if not create_venv(project_root, args.force):
            print_error("\nFailed to create virtual environment")
            sys.exit(1)
    
    # Step 4: Install dependencies
    print_header("Step 4: Dependencies")
    if not install_dependencies(project_root, args.dev):
        print_error("\nFailed to install dependencies")
        sys.exit(1)
    
    # Step 5: Setup configuration
    if not args.skip_config:
        print_header("Step 5: Configuration")
        setup_configuration(project_root)
        setup_env_file(project_root, {})
    
    # Step 6: Check environment variables
    print_header("Step 6: Environment Variables")
    env_status = check_environment_variables()
    
    if not env_status.get('RW_QWEN_API_KEY'):
        print_warning("\n⚠ RW_QWEN_API_KEY is required for the qwen_coder model")
        print_info("Get your API key from: https://dashscope.console.aliyun.com/")
    
    # Step 7: Optional tools
    install_optional_tools(project_root)
    
    # Print next steps
    print_next_steps(project_root, venv_path)
    
    print_success("\nSetup complete! 🚀\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
