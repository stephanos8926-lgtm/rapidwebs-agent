# Unified Prompt Optimization Hook

## Overview

This pre-commit hook combines **memory optimization** (A-MAC scoring) and **prompt compression** into a single, cohesive workflow.

### Three Modes

| Mode | Action | Use Case |
|------|--------|----------|
| **report** | Generate optimization report only | Review before applying changes |
| **optimize** | Apply optimizations, update originals | Automatic optimization |
| **save** | Save to `optimized-prompts/` folder | Preserve originals, review optimized |

---

## Configuration

### Method 1: Environment Variable (Quick)

```bash
# Windows
set QWEN_OPT_MODE=report
git commit -m "test"

# Unix
export QWEN_OPT_MODE=optimize
git commit -m "test"
```

### Method 2: Config File (Persistent)

Create `.qwen/optimizer-config.json`:

```json
{
  "mode": "optimize",
  "min_memory_score": 5.5,
  "compression_level": "standard",
  "create_backups": true,
  "optimized_folder": "optimized-prompts",
  "verbose": true
}
```

### Method 3: Command Line (One-time)

```bash
python tools/prompt_optimizer.py --input QWEN.md --mode optimize
```

---

## Installation

### Windows

```powershell
# Copy hook
copy hooks\pre-commit.bat .git\hooks\pre-commit.bat

# Test
git add QWEN.md
git commit -m "test"
```

### Unix/Linux/macOS

```bash
# Copy and make executable
cp hooks/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Test
git add QWEN.md
git commit -m "test"
```

---

## What Gets Optimized

### Memory Optimization (A-MAC Algorithm)

Scores memories on 5 dimensions:
- **Utility** (0.35 weight): Usefulness for future tasks
- **Novelty** (0.25 weight): Uniqueness vs existing
- **Recency** (0.15 weight): How recently accessed
- **Specificity** (0.15 weight): Precision/actionability
- **Position** (0.10 weight): Location in context

**Decisions:**
- Score ≥ 7.0: AUTO-ADMIT (keep)
- Score 5.5-6.9: REVIEW (consider keeping)
- Score < 5.5: SUMMARIZE (remove/condense)

### Prompt Compression

**Techniques:**
- Symbol substitutions (`✅` for "Correct", `❌` for "Wrong")
- Filler word removal ("Please note that", etc.)
- Header shortening ("Quick Start" → "Start")
- Table optimization
- Blank line cleanup

**Levels:**
- `light`: Minimal changes
- `standard`: Balanced (default)
- `aggressive`: Maximum compression

---

## Usage Examples

### Mode 1: Report Only (Review First)

```bash
# Set mode
export QWEN_OPT_MODE=report

# Commit (generates report, no changes)
git commit -m "Update docs"

# Output shows:
# - Memory scores and recommendations
# - Compression statistics
# - No files modified
```

### Mode 2: Auto-Optimize (Apply Changes)

```bash
# Set mode
export QWEN_OPT_MODE=optimize

# Commit (applies optimizations)
git commit -m "Update docs"

# Creates:
# - QWEN.md.bak (backup)
# - QWEN.md (optimized)
```

### Mode 3: Save to Folder (Preserve Originals)

```bash
# Set mode
export QWEN_OPT_MODE=save

# Commit (saves optimized copy)
git commit -m "Update docs"

# Creates:
# - optimized-prompts/QWEN.md (optimized)
# - QWEN.md (unchanged)
```

---

## Disable Temporarily

```bash
# Windows
set SKIP_PROMPT_OPT=1
git commit -m "Commit without optimization"

# Unix
export SKIP_PROMPT_OPT=1
git commit -m "Commit without optimization"
```

---

## Expected Output

### Report Mode
```
================================================================
 Unified Prompt Optimization
================================================================

Mode: report
Files: QWEN.md

Processing: QWEN.md
----------------------------------------
======================================================================
PROMPT OPTIMIZATION REPORT
======================================================================
Mode: REPORT
Memories: 18 total
  Keep (>=7.0): 1
  Review (5.5-6.9): 8
  Remove (<5.5): 9
  Average Score: 5.50
Compression: -12.3%
  Original: 12,369 chars
  Compressed: 10,850 chars
======================================================================

[OK] Optimization successful

================================================================
Processed 1 file(s)
Mode: report
Action: Report generated only (no files changed)
================================================================
```

### Optimize Mode
```
================================================================
 Unified Prompt Optimization
================================================================

Mode: optimize
Files: QWEN.md

Processing: QWEN.md
----------------------------------------
[Same report as above]
Backup: QWEN.md.bak
Output: QWEN.md

[OK] Optimization successful

================================================================
Processed 1 file(s)
Mode: optimize
Action: Files optimized and added to staging
================================================================
```

---

## Safety Features

✅ **Non-Breaking Changes Only**
- Symbol substitutions preserve meaning
- Filler removal doesn't affect content
- Memory scoring is recommendation-based

✅ **Backup Files** (optimize mode)
- `.bak` files created before changes
- Auto-restored if corruption detected

✅ **Logging**
- All operations logged with timestamps
- Logs saved to temp directory

✅ **Configurable**
- Three modes for different workflows
- Adjustable thresholds
- Can be disabled per-commit

---

## Troubleshooting

### Hook Not Running
- Ensure file is named `pre-commit` (or `pre-commit.bat`)
- Ensure executable (`chmod +x` on Unix)
- Check `.git/hooks/` directory

### Python Not Found
- Ensure virtual environment: `.venv/Scripts/python.exe`
- Or set `PYTHON` environment variable

### Want Different Mode?
```bash
# Change mode
export QWEN_OPT_MODE=save

# Or edit config file
# .qwen/optimizer-config.json
```

### Restore from Backup
```bash
# Windows
copy QWEN.md.bak QWEN.md

# Unix
cp QWEN.md.bak QWEN.md
```

---

## Configuration Options

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `mode` | string | `report` | `report`, `optimize`, or `save` |
| `min_memory_score` | float | `5.5` | Minimum score to keep memories |
| `compression_level` | string | `standard` | `light`, `standard`, or `aggressive` |
| `create_backups` | bool | `true` | Create `.bak` backup files |
| `optimized_folder` | string | `optimized-prompts` | Output folder for save mode |
| `verbose` | bool | `true` | Verbose output |

---

## Log Files

**Location:**
- Windows: `%TEMP%\prompt_opt_YYYYMMDD_HHMMSS.log`
- Unix: `/tmp/prompt_opt_YYYYMMDD_HHMMSS.log`

**Contents:**
- File name
- Timestamp
- Memory statistics
- Compression statistics
- Mode and actions taken

---

## Comparison: Old vs New

| Feature | Old (Separate) | New (Unified) |
|---------|---------------|---------------|
| Scripts | 2 (memory + compression) | 1 (combined) |
| Modes | Warning vs Auto | Report/Optimize/Save |
| Config | Env var only | Env + File + CLI |
| Output folder | N/A | `optimized-prompts/` |
| Code size | ~600 lines | ~500 lines |

---

## See Also

- `tools/prompt_optimizer.py` - Main optimization script
- `tools/memory_scorer.py` - A-MAC scoring algorithm
- `tools/prompt_compressor.py` - Compression (legacy)
- `tools/memory_optimizer.py` - Memory workflow (legacy)

---

**Version:** 2.0.0  
**Last Updated:** 2026-03-08  
**Safety:** Non-breaking changes, backups, logging
