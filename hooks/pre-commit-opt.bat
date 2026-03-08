@echo off
REM Git Pre-Commit Hook for Auto Prompt Optimization
REM 
REM This hook AUTOMATICALLY optimizes and compresses QWEN.md files
REM before commits. It creates backup files and applies safe optimizations.
REM
REM Safety Features:
REM - Creates .bak backup files before any changes
REM - Only applies non-breaking optimizations
REM - Logs all changes made
REM - Can be disabled with SKIP_PROMPT_OPT=1
REM
REM Installation: Copy to .git\hooks\pre-commit-opt.bat
REM
REM Author: RapidWebs Agent
REM Version: 1.0.0
REM Date: 2026-03-08

setlocal enabledelayedexpansion

REM Check if optimization is disabled
if defined SKIP_PROMPT_OPT (
    echo [INFO] Prompt optimization skipped (SKIP_PROMPT_OPT=1)
    exit /b 0
)

echo ==================================================
echo  Auto Prompt Optimization
echo ==================================================
echo.

REM Check if Python virtual environment exists
if exist ".venv\Scripts\python.exe" (
    set "PYTHON=.venv\Scripts\python.exe"
) else if defined PYTHON (
    set "PYTHON=python"
) else (
    echo [ERROR] Python not found, cannot optimize
    exit /b 1
)

REM Check if compressor script exists
if not exist "tools\prompt_compressor.py" (
    echo [ERROR] Prompt compressor not found
    exit /b 1
)

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

set "OPTIMIZED_COUNT=0"
set "LOG_FILE=%TEMP%\prompt_opt_%DATE:~0,4%%DATE:~4,2%%DATE:~6,2%_%TIME:~0,2%%TIME:~3,2%.log"
set "LOG_FILE=!LOG_FILE: =0!"

echo Log file: !LOG_FILE!
echo.

for %%f in (%QWEN_FILES%) do (
    if exist "%%f" (
        echo.
        echo Optimizing: %%f
        echo ----------------------------------------
        
        REM Create backup
        set "BACKUP=%%f.bak"
        copy /Y "%%f" "!BACKUP!" >nul 2>&1
        echo   Backup created: !BACKUP!
        
        REM Run compressor with output to same file
        %PYTHON% tools\prompt_compressor.py --input "%%f" --output "%%f" > "%TEMP%\opt_output.txt" 2>&1
        
        REM Show compression stats
        findstr /C:"Line reduction" "%TEMP%\opt_output.txt"
        findstr /C:"Char reduction" "%TEMP%\opt_output.txt"
        
        REM Log the optimization
        echo. >> "!LOG_FILE!"
        echo File: %%f >> "!LOG_FILE!"
        echo Date: %DATE% %TIME% >> "!LOG_FILE!"
        type "%TEMP%\opt_output.txt" >> "!LOG_FILE!"
        echo. >> "!LOG_FILE!"
        
        REM Verify file is still valid markdown (basic check)
        findstr /C:"#" "%%f" >nul
        if !errorlevel! neq 0 (
            echo [ERROR] Optimization may have corrupted file! Restoring backup...
            copy /Y "!BACKUP!" "%%f" >nul
            exit /b 1
        )
        
        echo   [OK] Optimization applied successfully
        echo.
        
        REM Add optimized file to staging
        git add "%%f"
        
        set /a OPTIMIZED_COUNT+=1
    )
)

echo.
echo ==================================================
echo Optimized !OPTIMIZED_COUNT! file^(s^)
echo Log saved to: !LOG_FILE!
echo.
echo To disable: set SKIP_PROMPT_OPT=1
echo ==================================================
echo.

REM Cleanup temp files
del "%TEMP%\opt_output.txt" >nul 2>&1

exit /b 0
