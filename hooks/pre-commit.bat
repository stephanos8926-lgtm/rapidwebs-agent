@echo off
REM Git Pre-Commit Hook for Memory Optimization Check (Windows Batch Version)
REM 
REM This hook checks if memory optimization is recommended for QWEN.md files
REM before allowing commits. It's a warning-only hook (doesn't block commits).
REM
REM Installation: This file should be at .git/hooks/pre-commit
REM
REM Author: RapidWebs Agent
REM Version: 1.0.0
REM Date: 2026-03-08

setlocal enabledelayedexpansion

echo ==================================================
echo  Memory Optimization Check
echo ==================================================
echo.

REM Find QWEN.md files that are staged for commit
set "QWEN_FILES="
for /f "delims=" %%i in ('git diff --cached --name-only --diff-filter^=ACM ^| findstr /i "QWEN.md"') do (
    set "QWEN_FILES=!QWEN_FILES! %%i"
)

if "%QWEN_FILES%"=="" (
    echo No QWEN.md files staged for commit.
    echo.
    exit /b 0
)

REM Check if Python virtual environment exists
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else if defined PYTHON (
    set "PYTHON=python"
) else (
    echo [WARNING] Python not found, skipping memory check
    exit /b 0
)

REM Check if memory optimizer script exists
if not exist "tools\memory_optimizer.py" (
    echo [WARNING] Memory optimizer not found, skipping check
    exit /b 0
)

set "WARNING_COUNT=0"

for %%f in (%QWEN_FILES%) do (
    if exist "%%f" (
        echo.
        echo Checking: %%f
        echo ----------------------------------------
        
        REM Run memory optimization check (report only)
        set "OUTPUT_FILE=%TEMP%\memory_check_output.txt"
        %PYTHON% tools\memory_optimizer.py --input "%%f" --report-only > "!OUTPUT_FILE!" 2>&1
        
        REM Display the report
        type "!OUTPUT_FILE!" | findstr /C:"Total memories" /C:"Keep" /C:"Remove" /C:"Average" /C:"MEMORIES TO" /C:"MEMORIES TO REMOVE"
        
        REM Check if there are items to remove
        findstr /C:"MEMORIES TO REMOVE:" "!OUTPUT_FILE!" >nul
        if !errorlevel! equ 0 (
            echo.
            echo [WARNING] Some memories recommended for removal
            echo    Run: %PYTHON% tools/memory_optimizer.py --input %%f --output %%~nf.optimized.md
            echo.
            set /a WARNING_COUNT+=1
        ) else (
            echo [OK] Memory optimization looks good
        )
        
        REM Cleanup temp file
        del "!OUTPUT_FILE!" >nul 2>&1
    )
)

echo.
echo ==================================================

if !WARNING_COUNT! GTR 0 (
    echo [WARNING] !WARNING_COUNT! file^(s^) could benefit from memory optimization
    echo.
    echo To optimize, run:
    for %%f in (%QWEN_FILES%) do (
        echo   %PYTHON% tools/memory_optimizer.py --input %%f --output %%~nf.optimized.md
    )
    echo.
    echo Proceeding with commit anyway ^(warning only^)...
    echo ==================================================
    exit /b 0
)

echo All QWEN.md files are optimized.
echo ==================================================
exit /b 0
