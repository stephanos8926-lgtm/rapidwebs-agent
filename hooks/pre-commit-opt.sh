#!/bin/bash
# Git Pre-Commit Hook for Auto Prompt Optimization (Unix/Bash Version)
# 
# This hook AUTOMATICALLY optimizes and compresses QWEN.md files
# before commits. It creates backup files and applies safe optimizations.
#
# Safety Features:
# - Creates .bak backup files before any changes
# - Only applies non-breaking optimizations
# - Logs all changes made
# - Can be disabled with SKIP_PROMPT_OPT=1
#
# Installation:
#   cp hooks/pre-commit-opt.sh .git/hooks/pre-commit
#   chmod +x .git/hooks/pre-commit
#
# Author: RapidWebs Agent
# Version: 1.0.0
# Date: 2026-03-08

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if optimization is disabled
if [ "$SKIP_PROMPT_OPT" = "1" ]; then
    echo -e "${YELLOW}[INFO] Prompt optimization skipped (SKIP_PROMPT_OPT=1)${NC}"
    exit 0
fi

echo "=================================================="
echo " Auto Prompt Optimization"
echo "=================================================="
echo ""

# Check if Python exists
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}[ERROR] Python not found, cannot optimize${NC}"
    exit 1
fi

# Check if compressor script exists
if [ ! -f "tools/prompt_compressor.py" ]; then
    echo -e "${RED}[ERROR] Prompt compressor not found${NC}"
    exit 1
fi

# Find QWEN.md files that are staged for commit
QWEN_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -i "QWEN.md" || true)

if [ -z "$QWEN_FILES" ]; then
    echo "No QWEN.md files staged for commit."
    echo ""
    exit 0
fi

OPTIMIZED_COUNT=0
LOG_FILE="/tmp/prompt_opt_$(date +%Y%m%d_%H%M%S).log"

echo "Log file: $LOG_FILE"
echo ""

for file in $QWEN_FILES; do
    if [ -f "$file" ]; then
        echo ""
        echo "Optimizing: $file"
        echo "----------------------------------------"
        
        # Create backup
        BACKUP="${file}.bak"
        cp "$file" "$BACKUP"
        echo "  Backup created: $BACKUP"
        
        # Run compressor
        OUTPUT=$($PYTHON tools/prompt_compressor.py --input "$file" --output "$file" 2>&1)
        
        # Show compression stats
        echo "$OUTPUT" | grep -E "Line reduction|Char reduction"
        
        # Log the optimization
        echo "" >> "$LOG_FILE"
        echo "File: $file" >> "$LOG_FILE"
        echo "Date: $(date)" >> "$LOG_FILE"
        echo "$OUTPUT" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        # Verify file is still valid markdown (basic check)
        if ! grep -q "^#" "$file"; then
            echo -e "${RED}[ERROR] Optimization may have corrupted file! Restoring backup...${NC}"
            cp "$BACKUP" "$file"
            exit 1
        fi
        
        echo -e "  ${GREEN}[OK]${NC} Optimization applied successfully"
        echo ""
        
        # Add optimized file to staging
        git add "$file"
        
        OPTIMIZED_COUNT=$((OPTIMIZED_COUNT + 1))
    fi
done

echo ""
echo "=================================================="
echo -e "Optimized ${GREEN}$OPTIMIZED_COUNT${NC} file(s)"
echo "Log saved to: $LOG_FILE"
echo ""
echo "To disable: export SKIP_PROMPT_OPT=1"
echo "=================================================="
echo ""

exit 0
