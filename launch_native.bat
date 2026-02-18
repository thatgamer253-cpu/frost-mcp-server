@echo off
setlocal
echo =========================================================
echo  LAUNCHING OVERLORD (NATIVE PYTHON MODE)
echo =========================================================

cd /d "%~dp0"

echo [..] Checking for Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [!!] ERROR: Python not found in PATH.
    echo      Please install Python 3.10+ and add to PATH.
    pause
    exit /b 1
)

echo [..] Installing dependencies? (Skipping for speed, run install_reqs.bat if needed)

echo [..] Launching Sovereign Unified...
python sovereign_unified.py

if %errorlevel% neq 0 (
    echo.
    echo [!!] CRASH DETECTED.
    echo      See above for error details.
    pause
)
