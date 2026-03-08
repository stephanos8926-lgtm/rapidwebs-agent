#!/usr/bin/env python3
"""RapidWebs Agent launcher for uv users.

This script provides a convenient way to run rw-agent with uv
without needing to activate the virtual environment.

Usage:
    python scripts/rw-agent              # Interactive mode
    python scripts/rw-agent "task"       # Run single task
    python scripts/rw-agent --stats      # Show statistics
    python scripts/rw-agent --help       # Show help
"""

import os
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.resolve()


def check_uv_installed() -> bool:
    """Check if uv is installed."""
    try:
        result = subprocess.run(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def check_venv_exists(project_root: Path) -> bool:
    """Check if virtual environment exists."""
    venv_path = project_root / ".venv"
    return venv_path.exists()


def ensure_dependencies(project_root: Path) -> bool:
    """Ensure dependencies are installed."""
    try:
        result = subprocess.run(
            ["uv", "pip", "sync", "uv.lock"],
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error installing dependencies: {e.stderr}", file=sys.stderr)
        return False


def run_rw_agent(args: list) -> int:
    """Run rw-agent with the provided arguments."""
    project_root = get_project_root()
    
    # Check prerequisites
    if not check_uv_installed():
        print("Error: uv is not installed.", file=sys.stderr)
        print("\nInstall uv:", file=sys.stderr)
        print("  Windows: powershell -ExecutionPolicy ByPass -Command \"irm https://astral.sh/uv/install.ps1 | iex\"", file=sys.stderr)
        print("  macOS/Linux: curl -LsSf https://astral.sh/uv/install.sh | sh", file=sys.stderr)
        return 1
    
    if not check_venv_exists(project_root):
        print("Error: Virtual environment not found.", file=sys.stderr)
        print(f"\nRun setup first:", file=sys.stderr)
        print(f"  cd {project_root}", file=sys.stderr)
        print("  python scripts/setup.py", file=sys.stderr)
        return 1
    
    # Ensure dependencies are up to date
    if not ensure_dependencies(project_root):
        print("Warning: Could not update dependencies. Continuing with existing installation.", file=sys.stderr)
    
    # Run rw-agent using uv run
    cmd = ["uv", "run", "rw-agent"] + args
    
    try:
        # On Windows, we need to handle the command differently
        if sys.platform == 'win32':
            result = subprocess.run(cmd, cwd=project_root)
        else:
            result = subprocess.run(cmd, cwd=project_root)
        
        return result.returncode
        
    except KeyboardInterrupt:
        print("\nInterrupted.")
        return 130
    except Exception as e:
        print(f"Error running rw-agent: {e}", file=sys.stderr)
        return 1


def show_help():
    """Show help message."""
    help_text = """
RapidWebs Agent Launcher (uv)

Usage:
    python scripts/rw-agent [OPTIONS] [TASK]

Commands:
    (no args)              Start interactive mode
    "task description"     Run a single task
    --help                 Show this help message
    --version              Show version
    --stats                Show usage statistics
    --configure            Launch configuration wizard

Options:
    --model MODEL          Use specified model (qwen_coder, gemini)
    --no-cache             Disable response caching
    --verbose              Enable verbose output
    --token-limit N        Set daily token budget (default: 100000)

Code Tools:
    --check-tools          Check installed code tools
    --install-tools        Install Tier 1 code tools
    --lint FILE            Lint a code file
    --format FILE          Format a code file

Examples:
    python scripts/rw-agent
    python scripts/rw-agent "Refactor main.py to use async/await"
    python scripts/rw-agent --stats
    python scripts/rw-agent --model gemini "Explain this code"
    python scripts/rw-agent --lint main.py

Quick Start:
    1. Run setup: python scripts/setup.py
    2. Set API key: Set RW_QWEN_API_KEY environment variable
    3. Launch: python scripts/rw-agent

For more information, see README.md or run: rw-agent --help
"""
    print(help_text)


def main() -> int:
    """Main entry point."""
    # Handle --help specially before checking prerequisites
    if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h', 'help']:
        show_help()
        return 0
    
    return run_rw_agent(sys.argv[1:])


if __name__ == "__main__":
    sys.exit(main())
