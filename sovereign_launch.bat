@echo off
TITLE Sovereign Launch — Overlord V2
echo ═══════════════════════════════════════════════════════════════
echo   SOVEREIGN LAUNCH: Deploying Local CORTEX and Hub
echo ═══════════════════════════════════════════════════════════════
echo.

:: Check for Ollama
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo [!] Ollama not found in PATH. Please install it from https://ollama.com
    pause
    exit /b
)

:: Set environment flags
set OVERLORD_FORCE_LOCAL=1
set OVERLORD_OFFLINE_MODE=0

:: Run the sovereign initialization script
python creation_engine/sovereign/launch.py

if %errorlevel% neq 0 (
    echo.
    echo [!] Sovereign initialization failed.
    pause
)
