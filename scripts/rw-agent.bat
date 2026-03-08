@echo off
REM RapidWebs Agent Launcher for Windows
REM 
REM Usage:
REM   rw-agent              - Interactive mode
REM   rw-agent "task"       - Run single task
REM   rw-agent --stats      - Show statistics
REM   rw-agent --help       - Show help

setlocal enabledelayedexpansion

REM Get the directory where this script is located
set "SCRIPT_DIR=%~dp0"
set "PROJECT_ROOT=%SCRIPT_DIR%.."

REM Check if uv is available
where uv >nul 2>nul
if %errorlevel% neq 0 (
    echo Error: uv is not installed or not in PATH.
    echo.
    echo Install uv from: https://docs.astral.sh/uv/getting-started/installation/
    echo.
    echo Or use: python scripts\rw-agent.py %*
    exit /b 1
)

REM Check if virtual environment exists
if not exist "%PROJECT_ROOT%\.venv" (
    echo Error: Virtual environment not found.
    echo.
    echo Run setup first:
    echo   cd %PROJECT_ROOT%
    echo   python scripts\setup.py
    echo.
    echo Or use: python scripts\rw-agent.py %*
    exit /b 1
)

REM Run rw-agent using uv
uv run rw-agent %*
