@echo off
REM Unified Pre-Commit Hook for Prompt Optimization
REM 
REM Combines memory optimization (A-MAC scoring) and prompt compression.
REM Three modes controlled by config/env var:
REM   1. report   - Generate report only (no changes)
REM   2. optimize - Apply optimizations and update files
REM   3. save     - Save to optimized-prompts folder
REM
REM Configuration:
REM   - Environment: QWEN_OPT_MODE=report|optimize|save
REM   - Config file: .qwen/optimizer-config.json
REM   - Command line: --mode report|optimize|save
REM
REM Safety Features:
REM   - Creates .bak backups (optimize mode)
REM   - Non-breaking optimizations only
REM   - Detailed logging
REM   - Can disable with SKIP_PROMPT_OPT=1
REM
REM Author: RapidWebs Agent
REM Version: 2.0.0
REM Date: 2026-03-08

setlocal enabledelayedexpansion

REM Check if disabled
if defined SKIP_PROMPT_OPT (
    echo [INFO] Optimization skipped (SKIP_PROMPT_OPT=1)
    exit /b 0
)

echo ================================================================
echo  Unified Prompt Optimization
echo ================================================================
echo.

REM Check Python
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else if defined PYTHON (
    set "PYTHON=python"
) else (
    echo [ERROR] Python not found
    exit /b 1
)

REM Check optimizer script
if not exist "tools\prompt_optimizer.py" (
    echo [ERROR] Optimizer not found
    exit /b 1
)

REM Find QWEN.md files
set "QWEN_FILES="
for /f "delims=" %%i in ('git diff --cached --name-only --diff-filter^=ACM ^| findstr /i "QWEN.md"') do (
    set "QWEN_FILES=!QWEN_FILES! %%i"
)

if "%QWEN_FILES%"=="" (
    echo No QWEN.md files staged.
    echo.
    exit /b 0
)

REM Get mode from env or default to report
set "MODE=%QWEN_OPT_MODE%"
if "!MODE!"=="" set "MODE=report"

echo Mode: !MODE!
echo Files: %QWEN_FILES%
echo.

set "LOG_FILE=%TEMP%\prompt_opt_%DATE:~0,4%%DATE:~4,2%%DATE:~6,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG_FILE=!LOG_FILE: =0!"

set "SUCCESS_COUNT=0"

for %%f in (%QWEN_FILES%) do (
    if exist "%%f" (
        echo.
        echo Processing: %%f
        echo ----------------------------------------
        
        REM Run optimizer
        %PYTHON% tools\prompt_optimizer.py --input "%%f" --mode !MODE! > "%TEMP%\opt_output.txt" 2>&1
        
        REM Show report
        type "%TEMP%\opt_output.txt"
        
        REM Log
        echo. >> "!LOG_FILE!"
        echo File: %%f >> "!LOG_FILE!"
        echo Date: %DATE% %TIME% >> "!LOG_FILE!"
        type "%TEMP%\opt_output.txt" >> "!LOG_FILE!"
        echo. >> "!LOG_FILE!"
        
        REM Check success
        findstr /C:"SUCCESS" "%TEMP%\opt_output.txt" >nul
        if !errorlevel! equ 0 (
            echo.
            echo [OK] Optimization successful
            set /a SUCCESS_COUNT+=1
            
            REM Add optimized file to staging (for optimize mode)
            if "!MODE!"=="optimize" (
                git add "%%f"
            )
        ) else (
            echo.
            echo [WARNING] Check output for issues
        )
    )
)

echo.
echo ================================================================
echo Processed !SUCCESS_COUNT! file^(s^)
echo Log: !LOG_FILE!
echo.
echo Mode: !MODE!
if "!MODE!"=="report" (
    echo Action: Report generated only (no files changed)
) else if "!MODE!"=="optimize" (
    echo Action: Files optimized and added to staging
) else if "!MODE!"=="save" (
    echo Action: Optimized files saved to optimized-prompts/
)
echo.
echo To change mode: set QWEN_OPT_MODE=report^|optimize^|save
echo To disable: set SKIP_PROMPT_OPT=1
echo ================================================================
echo.

del "%TEMP%\opt_output.txt" >nul 2>&1

exit /b 0
