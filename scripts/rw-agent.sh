#!/bin/bash
# RapidWebs Agent Launcher for Unix-like systems (macOS, Linux)
# 
# Usage:
#   ./rw-agent              - Interactive mode
#   ./rw-agent "task"       - Run single task
#   ./rw-agent --stats      - Show statistics
#   ./rw-agent --help       - Show help

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Check if uv is available
if ! command -v uv &> /dev/null; then
    echo "Error: uv is not installed or not in PATH."
    echo ""
    echo "Install uv from: https://docs.astral.sh/uv/getting-started/installation/"
    echo ""
    echo "Or use: python scripts/rw-agent.py $@"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo "Error: Virtual environment not found."
    echo ""
    echo "Run setup first:"
    echo "  cd $PROJECT_ROOT"
    echo "  python scripts/setup.py"
    echo ""
    echo "Or use: python scripts/rw-agent.py $@"
    exit 1
fi

# Run rw-agent using uv
cd "$PROJECT_ROOT"
uv run rw-agent "$@"
