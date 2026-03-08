# Git Hooks for RapidWebs Agent

This directory contains optional git hooks for the project.

## Installation

To install the pre-commit hook, copy it to your `.git/hooks/` directory:

### Windows (CMD/PowerShell)
```powershell
copy hooks\pre-commit.bat .git\hooks\pre-commit.bat
```

### Unix/Linux/macOS (Bash)
```bash
cp hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Available Hooks

### pre-commit (Memory Optimization Check)

**Purpose:** Checks if QWEN.md files could benefit from memory optimization before commits.

**Behavior:** Warning-only (does NOT block commits)

**What it does:**
1. Detects staged QWEN.md files
2. Runs memory optimization analysis
3. Reports memories recommended for removal (score < 5.5)
4. Shows command to optimize if needed
5. Allows commit to proceed regardless

**Example Output:**
```
==================================================
 Memory Optimization Check
==================================================

Checking: QWEN.md
----------------------------------------
  Total memories: 18
  Keep (>=7.0): 1
  Remove (<5.5): 9
  Average score: 5.50

[WARNING] Some memories recommended for removal
   Run: python tools/memory_optimizer.py --input QWEN.md --output QWEN.optimized.md

Proceeding with commit anyway (warning only)...
```

## Manual Installation Script

Run this from the project root to install all hooks:

### Windows
```batch
@echo off
echo Installing git hooks...
copy hooks\pre-commit.bat .git\hooks\pre-commit.bat
echo Done! Pre-commit hook installed.
```

### Unix/Linux/macOS
```bash
#!/bin/bash
echo "Installing git hooks..."
cp hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
echo "Done! Pre-commit hook installed."
```

## Disabling the Hook

To temporarily disable the pre-commit hook:

### Windows
```batch
ren .git\hooks\pre-commit.bat pre-commit.bat.disabled
```

### Unix/Linux/macOS
```bash
mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled
```

## How It Works

The pre-commit hook uses the memory optimization tools:

1. **extract_memories.py** - Extracts memories from QWEN.md
2. **memory_scorer.py** - Scores memories using A-MAC algorithm
3. **memory_optimizer.py** - Complete workflow orchestration

The hook runs `memory_optimizer.py --report-only` and parses the output to determine if optimization is recommended.

## Requirements

- Python 3.10+
- Virtual environment at `.venv/` (or system Python)
- Memory optimization tools in `tools/` directory

## Troubleshooting

### Hook not running
- Ensure file is named `pre-commit` (no extension on Unix)
- Ensure file is executable (`chmod +x` on Unix)
- Check git hook directory: `.git/hooks/`

### Python not found
- Ensure virtual environment exists: `.venv/Scripts/python.exe`
- Or set PYTHON environment variable

### False positives
- The hook is warning-only and won't block commits
- Review recommendations manually before optimizing
- Some low-score memories may be contextually important

## See Also

- `tools/MEMORY_TOOLS_README.md` - Full memory tools documentation
- `tools/memory_optimizer.py --help` - Command-line options
