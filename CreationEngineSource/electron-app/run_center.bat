@echo off
REM ══════════════════════════════════════════════════════════
REM  OVERLORD — Electron Command Center Launcher
REM ══════════════════════════════════════════════════════════

echo.
echo Launching Command Center...

REM CRITICAL: Unset ELECTRON_RUN_AS_NODE so Electron acts as an app, not Node.
set ELECTRON_RUN_AS_NODE=

REM Launch using the local Electron binary
start "" "node_modules\electron\dist\electron.exe" . --no-sandbox
