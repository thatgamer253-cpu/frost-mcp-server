@echo off
echo ==========================================
echo Building Overlord V2 (Chat Launcher)...
echo ==========================================

pyinstaller --noconfirm --noconsole --onefile --icon=assets/icon.ico --name="Overlord V2" creator_v2.py

if exist "dist\Overlord V2.exe" (
    echo.
    echo Build Successful!
    echo Copying to Desktop...
    copy /Y "dist\Overlord V2.exe" "%USERPROFILE%\Desktop\Overlord V2.exe"
    echo.
    echo ==========================================
    echo NOW: Drag "Overlord V2.exe" from your Desktop to your Taskbar to Pin it!
    echo ==========================================
) else (
    echo Build Failed! Check output.
)
pause
