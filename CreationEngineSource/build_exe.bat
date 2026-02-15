@echo off
REM ══════════════════════════════════════════════════════════
REM  OVERLORD — Build standalone .exe
REM  Run this script from the Creator directory.
REM ══════════════════════════════════════════════════════════

echo.
echo ======================================================
echo   OVERLORD — Building Standalone .exe
echo ======================================================
echo.

REM 1. Install dependencies
echo [1/3] Installing dependencies...
pip install customtkinter openai pyinstaller --quiet

REM 2. Build the .exe
echo [2/3] Running PyInstaller...
pyinstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name "Overlord" ^
    --icon NONE ^
    --collect-all customtkinter ^
    --hidden-import customtkinter ^
    command_center.py

REM 3. Done
echo.
echo [3/3] Build complete!
echo.
echo ======================================================
echo   Your .exe is at:  dist\Overlord.exe
echo ======================================================
echo.
echo   You can move Overlord.exe anywhere and double-click
echo   to launch — no Python installation required.
echo.
pause
