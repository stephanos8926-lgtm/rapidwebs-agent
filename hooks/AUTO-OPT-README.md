# Auto Prompt Optimization Hook

## Overview

This pre-commit hook **automatically optimizes and compresses** QWEN.md files before commits. Unlike the warning-only hook (`pre-commit.bat`), this hook **applies changes directly**.

## Safety Features

✅ **Non-Breaking Changes Only**
- Symbol substitutions (✅ for "Correct", etc.)
- Filler word removal
- Table consolidation
- Header shortening
- Blank line optimization

✅ **Backup Files Created**
- Every optimized file gets a `.bak` backup
- Restored automatically if corruption detected

✅ **Logging**
- All changes logged with timestamps
- Logs saved to temp directory

✅ **Can Be Disabled**
- Set `SKIP_PROMPT_OPT=1` to skip optimization

---

## Installation

### Windows (CMD/PowerShell)

```powershell
# Copy hook to git hooks directory
copy hooks\pre-commit-opt.bat .git\hooks\pre-commit.bat

# Test it
git add QWEN.md
git commit -m "test"
```

### Unix/Linux/macOS (Bash)

```bash
# Copy and make executable
cp hooks/pre-commit-opt.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit

# Test it
git add QWEN.md
git commit -m "test"
```

---

## Usage

### Automatic (Default)

Just commit as normal. The hook will:
1. Detect staged QWEN.md files
2. Create `.bak` backups
3. Apply optimizations
4. Add optimized files to staging
5. Proceed with commit

```bash
git add QWEN.md
git commit -m "Update docs"
# Hook runs automatically, optimizes QWEN.md
```

### Disable Temporarily

#### Windows
```batch
set SKIP_PROMPT_OPT=1
git commit -m "Commit without optimization"
```

#### Unix/Linux/macOS
```bash
export SKIP_PROMPT_OPT=1
git commit -m "Commit without optimization"
```

### Disable Permanently

Remove or rename the hook:

```bash
# Windows
ren .git\hooks\pre-commit.bat pre-commit.bat.disabled

# Unix
mv .git/hooks/pre-commit .git/hooks/pre-commit.disabled
```

---

## What Gets Optimized

### Symbol Substitutions (~40% savings on phrases)
| Original | Replaced |
|----------|----------|
| "Correct" | ✅ |
| "Wrong" | ❌ |
| "Warning" | ⚠️ |
| "Critical" | **CRITICAL** |
| "Always" | ✅ |
| "Never" | ❌ |

### Filler Word Removal (~25% savings)
- "Please note that" → (removed)
- "It is important to" → (removed)
- "Keep in mind that" → (removed)
- "In order to" → (removed)

### Table Optimization
- Removes extra spaces in cells
- Consolidates redundant columns

### Header Shortening
- "## 🚀 Quick Start" → "## 🚀 Start"
- "## 🔌 MCP Servers" → "## 🔌 MCP"
- "## 📞 Quick Reference" → "## 📞 Ref"

### Blank Line Optimization
- Removes consecutive blank lines
- Removes blank lines at section boundaries

---

## Expected Results

### Typical Compression
- **Lines:** -15% to -35%
- **Characters:** -10% to -25%
- **Functionality:** 100% preserved

### Example Output
```
==================================================
 Auto Prompt Optimization
==================================================

Optimizing: QWEN.md
----------------------------------------
  Backup created: QWEN.md.bak
Line reduction: 22.5%
Char reduction: 18.3%
  [OK] Optimization applied successfully

==================================================
Optimized 1 file(s)
==================================================
```

---

## Troubleshooting

### Hook Not Running
- Ensure file is named `pre-commit` (or `pre-commit.bat` on Windows)
- Ensure file is executable (`chmod +x` on Unix)
- Check git hook directory: `.git/hooks/`

### Python Not Found
- Ensure virtual environment exists
- Or set `PYTHON` environment variable

### File Corruption (Rare)
If optimization corrupts a file:
1. Hook detects corruption automatically
2. Restores from `.bak` backup
3. Aborts commit

To manually restore:
```bash
# Windows
copy QWEN.md.bak QWEN.md

# Unix
cp QWEN.md.bak QWEN.md
```

### Want to Review Changes First?
Use the warning-only hook instead:
```bash
# Windows
copy hooks\pre-commit.bat .git\hooks\pre-commit.bat

# Unix
cp hooks/pre-commit.sh .git/hooks/pre-commit
```

---

## Log Files

Logs are saved to:
- **Windows:** `%TEMP%\prompt_opt_YYYYMMDD_HHMMSS.log`
- **Unix:** `/tmp/prompt_opt_YYYYMMDD_HHMMSS.log`

Logs contain:
- File name
- Timestamp
- Compression statistics
- Techniques applied

---

## Comparison: Warning vs Auto Hooks

| Feature | Warning Hook | Auto Hook |
|---------|-------------|-----------|
| **File:** | `pre-commit.bat` | `pre-commit-opt.bat` |
| **Action:** | Warns only | Applies changes |
| **Backups:** | No | Yes (`.bak` files) |
| **Logging:** | Minimal | Detailed |
| **Use Case:** | Review before changes | Automatic optimization |

---

## Best Practices

1. **Review First Commit**
   - Use warning hook for first few commits
   - Switch to auto hook once comfortable

2. **Check Backups**
   - Keep `.bak` files for 1-2 commits
   - Delete after verifying optimizations

3. **Disable for Sensitive Commits**
   - Use `SKIP_PROMPT_OPT=1` for documentation PRs
   - Manual review may be preferred

4. **Monthly Review**
   - Check log files for patterns
   - Adjust compressor settings if needed

---

## See Also

- `tools/prompt_compressor.py` - Compression script
- `tools/MEMORY_TOOLS_README.md` - Memory optimization tools
- `hooks/README.md` - Git hooks overview

---

**Version:** 1.0.0  
**Last Updated:** 2026-03-08  
**Safety:** Non-breaking changes only, backups created
