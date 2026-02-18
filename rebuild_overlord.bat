@echo off
echo ======================================================
echo   OVERLORD — Rebuilding Release Build
echo ======================================================
echo.

pip install pyinstaller --quiet

echo [1/2] Cleaning previous builds...
if exist "build" rd /s /q "build"
if exist "dist\OverlordCreator.exe" del "dist\OverlordCreator.exe"

echo [2/2] Running PyInstaller with OverlordCreator.spec...
pyinstaller OverlordCreator.spec --noconfirm --clean

echo.
echo ======================================================
if exist "dist\OverlordCreator.exe" (
    echo   BUILD SUCCESSFUL
    echo   Location: dist\OverlordCreator.exe
) else (
    echo   BUILD FAILED
    echo   Check errors above.
)
echo ======================================================
echo.
pause
