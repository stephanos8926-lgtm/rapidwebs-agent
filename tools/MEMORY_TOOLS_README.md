# Memory Optimization Tools - Quick Reference

## Overview

Three tools for optimizing Qwen Code CLI memories:

1. **extract_memories.py** - Extract memories from QWEN.md files
2. **memory_scorer.py** - Score memories using A-MAC algorithm
3. **memory_optimizer.py** - Complete workflow (extract + score + optimize)

---

## Quick Start

### One-Command Optimization

```bash
# Optimize project QWEN.md
cd E:\Projects\rapidwebs-agent
.venv\Scripts\python.exe tools\memory_optimizer.py --project --output QWEN.optimized.md

# Optimize global QWEN.md
.venv\Scripts\python.exe tools\memory_optimizer.py --global --output C:\Users\Bratp\.qwen\QWEN.optimized.md
```

---

## Tool 1: extract_memories.py

**Purpose:** Extract memories from markdown files into JSON format.

### Usage

```bash
# Extract from specific file
python tools/extract_memories.py --input QWEN.md --output memories.json --verbose

# Extract from global QWEN.md
python tools/extract_memories.py --global --output global_memories.json --verbose

# Extract from project QWEN.md
python tools/extract_memories.py --project --output project_memories.json --verbose

# Extract from stdin
type QWEN.md | python tools/extract_memories.py --stdin --output memories.json
```

### Output Format

```json
[
  {
    "content": "Memory text here",
    "category": "architecture_decision",
    "source": "bullet_point",
    "line_number": 178,
    "source_file": "QWEN.md",
    "extracted_at": "2026-03-08T15:30:00"
  }
]
```

### Categories (Auto-Detected)

| Category | Boost | Examples |
|----------|-------|----------|
| `architecture_decision` | 1.2× | "Python uses SkillManager, NOT MCP" |
| `error_prevention` | 1.15× | "Must import AND call render()" |
| `user_preference` | 1.1× | "Prefers dark mode" |
| `implementation_detail` | 1.1× | "Duration captured at THREE levels" |
| `tool_configuration` | 1.0× | "Context7 MCP configured with tools" |
| `project_context` | 1.05× | "Token budget is 6000" |

---

## Tool 2: memory_scorer.py

**Purpose:** Score memories using A-MAC algorithm.

### Usage

```bash
# Score from JSON file
python tools/memory_scorer.py --batch --input memories.json --output report.txt

# Score single memory
python tools/memory_scorer.py --content "Python uses SkillManager, NOT MCP" --category architecture_decision

# Interactive mode
python tools/memory_scorer.py --interactive
```

### Scoring Dimensions

| Dimension | Weight | Question |
|-----------|--------|----------|
| Utility | 0.35 | How useful for future tasks? |
| Novelty | 0.25 | How unique vs existing memories? |
| Recency | 0.15 | How recently accessed? |
| Specificity | 0.15 | How precise/actionable? |
| Position | 0.10 | Where in context window? |

### Decision Thresholds

| Score | Decision | Action |
|-------|----------|--------|
| ≥ 7.0 | AUTO-ADMIT | Keep (high-value) |
| 5.5-6.9 | REVIEW | Consider keeping if space allows |
| < 5.5 | SUMMARIZE/REJECT | Remove or condense |

### Red Flags (Auto-Reject Candidates)

- Contains API keys (security risk)
- Redundant references ("As mentioned earlier...")
- Resolved/superseded information
- Raw tool output (>500 chars)
- Older than 90 days without access

---

## Tool 3: memory_optimizer.py

**Purpose:** Complete workflow - extract, score, and generate optimized file.

### Usage

```bash
# Full optimization with output file
python tools/memory_optimizer.py --input QWEN.md --output QWEN.optimized.md --verbose

# Report only (no file changes)
python tools/memory_optimizer.py --input QWEN.md --report-only --verbose

# Custom minimum score threshold
python tools/memory_optimizer.py --project --min-score 6.0 --output QWEN.optimized.md
```

### Output

1. **Console report** - Summary of keep/review/remove decisions
2. **Optimized markdown** - File with filtered memories
3. **JSON report** - Detailed scoring breakdown (`memory_optimization_report.json`)

---

## Complete Workflow Example

### Step 1: Extract
```bash
cd E:\Projects\rapidwebs-agent
.venv\Scripts\python.exe tools/extract_memories.py --project --output memories.json --verbose
```

### Step 2: Score
```bash
.venv\Scripts\python.exe tools/memory_scorer.py --batch --input memories.json --output scored_report.txt
```

### Step 3: Review Report
```bash
type scored_report.txt
```

### Step 4: Optimize
```bash
.venv\Scripts\python.exe tools/memory_optimizer.py --input QWEN.md --output QWEN.optimized.md --verbose
```

### Step 5: Review Changes
```bash
# Compare original vs optimized
git diff QWEN.md QWEN.optimized.md
```

### Step 6: Apply (if satisfied)
```bash
copy /Y QWEN.optimized.md QWEN.md
```

---

## Scheduled Optimization

### Monthly Cleanup Script

```batch
@echo off
REM monthly_memory_cleanup.bat
cd /d E:\Projects\rapidwebs-agent

echo === Memory Optimization - %DATE% ===
.venv\Scripts\python.exe tools/memory_optimizer.py --project --report-only > reports\memory_report_%DATE:~0,4%%DATE:~4,2%.txt

echo Report saved to reports\
```

### Quarterly Deep Clean

```bash
# Extract and score all memories
python tools/extract_memories.py --project --output all_memories.json
python tools/memory_scorer.py --batch --input all_memories.json --output quarterly_report.txt

# Review items with score < 5.5 AND age > 90 days
# Manually remove from QWEN.md
```

---

## Integration with Qwen Code CLI

### Pre-Commit Hook

Add to `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Check memory optimization before commit

cd "$(dirname "$0")/../../tools"
python memory_optimizer.py --input ../QWEN.md --report-only > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "Warning: Memory optimization recommended"
    echo "Run: python tools/memory_optimizer.py --project --report-only"
fi
```

### CI/CD Pipeline

```yaml
# .github/workflows/memory-optimization.yml
name: Memory Optimization Check

on: [push]

jobs:
  check-memories:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Check memory optimization
        run: |
          python tools/memory_optimizer.py --project --report-only
```

---

## Troubleshooting

### No Memories Found

```bash
# Check file encoding
python -c "print(open('QWEN.md', encoding='utf-8').read()[:500])"

# Verify section header exists
findstr /C:"## Qwen Added Memories" QWEN.md
```

### Encoding Errors on Windows

```bash
# Set UTF-8 encoding
chcp 65001
python tools/memory_scorer.py --input memories.json
```

### Low Scores for Important Memories

```bash
# Override category for higher Type Prior boost
python tools/memory_scorer.py --content "Your memory" --category architecture_decision

# Or adjust min-score threshold
python tools/memory_optimizer.py --min-score 5.0 --output optimized.md
```

---

## Best Practices

1. **Run monthly** - Prevents memory bloat
2. **Review before removing** - Some "low score" memories are contextually important
3. **Keep architecture decisions** - Always high utility
4. **Remove API keys immediately** - Security risk
5. **Summarize, don't delete** - Condense low-score items instead of removing

---

## Files Reference

| File | Purpose |
|------|---------|
| `tools/extract_memories.py` | Memory extraction |
| `tools/memory_scorer.py` | A-MAC scoring |
| `tools/memory_optimizer.py` | Complete workflow |
| `tools/test_memories.json` | Sample input (delete after testing) |
| `tools/memory_optimization_report.json` | Detailed report output |

---

**Version:** 1.0.0  
**Last Updated:** 2026-03-08  
**Based on:** A-MAC Research (arxiv.org/html/2603.04549v1)
