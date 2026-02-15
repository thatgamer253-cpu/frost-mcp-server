@echo off
title 🚀 OVERLORD COMMAND CENTER — One Program Launcher
color 0B
cls

echo.
echo  ══════════════════════════════════════════════════════════════════
echo    🚀 ANTIGRAVITY OVERLORD — COMMAND CENTER
echo  ══════════════════════════════════════════════════════════════════
echo.
echo  [SYSTEM] Engaging high-tier multi-agent neural infrastructure...
echo  [SYSTEM] Loading Premium Electron Interface...
echo.

:: Check for node_modules
if not exist "node_modules" (
    echo  [WARN] node_modules not found. Installing dependencies...
    npm install
)

:: Launch Electron app
start "" npx electron .

echo  [SUCCESS] Command Center active. Monitoring fleet...
echo  [INFO] Close this window only if the Command Center has crashed.
echo.
pause
