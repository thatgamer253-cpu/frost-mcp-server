@echo off
title ⚡ OVERLORD — Creation Engine GUI
color 0B
cls

echo.
echo  ══════════════════════════════════════════════════════════════
echo    ⚡ ANTIGRAVITY OVERLORD — Creation Engine v3.0
echo  ══════════════════════════════════════════════════════════════
echo.
echo  [SYSTEM] Launching PyQt6 Desktop Console...
echo.

cd /d "%~dp0"
python overlord_gui.py

if %ERRORLEVEL% neq 0 (
    echo.
    echo  [ERROR] Launch failed. Make sure PyQt6 is installed:
    echo          pip install PyQt6
    echo.
    pause
)
