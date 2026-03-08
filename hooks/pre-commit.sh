#!/bin/bash
# Unified Pre-Commit Hook for Prompt Optimization (Unix/Bash)
# 
# Combines memory optimization (A-MAC scoring) and prompt compression.
# Three modes controlled by config/env var:
#   1. report   - Generate report only (no changes)
#   2. optimize - Apply optimizations and update files
#   3. save     - Save to optimized-prompts folder
#
# Configuration:
#   - Environment: QWEN_OPT_MODE=report|optimize|save
#   - Config file: .qwen/optimizer-config.json
#   - Command line: --mode report|optimize|save
#
# Safety Features:
#   - Creates .bak backups (optimize mode)
#   - Non-breaking optimizations only
#   - Detailed logging
#   - Can disable with SKIP_PROMPT_OPT=1

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Check if disabled
if [ "$SKIP_PROMPT_OPT" = "1" ]; then
    echo -e "${YELLOW}[INFO] Optimization skipped (SKIP_PROMPT_OPT=1)${NC}"
    exit 0
fi

echo "================================================================"
echo " Unified Prompt Optimization"
echo "================================================================"
echo ""

# Check Python
if [ -f ".venv/bin/python" ]; then
    PYTHON=".venv/bin/python"
elif [ -f ".venv/Scripts/python.exe" ]; then
    PYTHON=".venv/Scripts/python.exe"
elif command -v python &> /dev/null; then
    PYTHON="python"
else
    echo -e "${RED}[ERROR] Python not found${NC}"
    exit 1
fi

# Check optimizer
if [ ! -f "tools/prompt_optimizer.py" ]; then
    echo -e "${RED}[ERROR] Optimizer not found${NC}"
    exit 1
fi

# Find QWEN.md files
QWEN_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -i "QWEN.md" || true)

if [ -z "$QWEN_FILES" ]; then
    echo "No QWEN.md files staged."
    echo ""
    exit 0
fi

# Get mode
MODE="${QWEN_OPT_MODE:-report}"

echo "Mode: $MODE"
echo "Files: $QWEN_FILES"
echo ""

LOG_FILE="/tmp/prompt_opt_$(date +%Y%m%d_%H%M%S).log"
SUCCESS_COUNT=0

for file in $QWEN_FILES; do
    if [ -f "$file" ]; then
        echo ""
        echo "Processing: $file"
        echo "----------------------------------------"
        
        # Run optimizer
        OUTPUT=$($PYTHON tools/prompt_optimizer.py --input "$file" --mode "$MODE" 2>&1)
        
        # Show report
        echo "$OUTPUT"
        
        # Log
        echo "" >> "$LOG_FILE"
        echo "File: $file" >> "$LOG_FILE"
        echo "Date: $(date)" >> "$LOG_FILE"
        echo "$OUTPUT" >> "$LOG_FILE"
        echo "" >> "$LOG_FILE"
        
        # Check success
        if echo "$OUTPUT" | grep -q "SUCCESS"; then
            echo ""
            echo -e "${GREEN}[OK]${NC} Optimization successful"
            SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
            
            # Add to staging for optimize mode
            if [ "$MODE" = "optimize" ]; then
                git add "$file"
            fi
        else
            echo ""
            echo -e "${YELLOW}[WARNING]${NC} Check output for issues"
        fi
    fi
done

echo ""
echo "================================================================"
echo -e "Processed ${GREEN}$SUCCESS_COUNT${NC} file(s)"
echo "Log: $LOG_FILE"
echo ""
echo "Mode: $MODE"
case $MODE in
    report)
        echo "Action: Report generated only (no files changed)"
        ;;
    optimize)
        echo "Action: Files optimized and added to staging"
        ;;
    save)
        echo "Action: Optimized files saved to optimized-prompts/"
        ;;
esac
echo ""
echo "To change mode: export QWEN_OPT_MODE=report|optimize|save"
echo "To disable: export SKIP_PROMPT_OPT=1"
echo "================================================================"
echo ""

exit 0
