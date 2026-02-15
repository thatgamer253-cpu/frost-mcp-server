@echo off
title PROJECT FROST // FINAL AUTHORIZATION
cd /d "%~dp0"

echo ===========================================
echo   AUTHORIZING YOUR 10-AGENT SWARM ❄️🚀
echo ===========================================
echo.
echo [1/2] Clearing Conflicting Processes...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM chrome.exe /T >nul 2>&1

echo [2/2] Opening the Authorization Tunnel...
echo.
echo [!] WHAT TO DO:
echo 1. Log in to Upwork and LinkedIn in the window that opens.
echo 2. Once you reach your Dashboard, CLOSE the browser window.
echo 3. The 10 agents will immediately take over from here.
echo.

set "USER_DATA=%CD%\browser_session"
if not exist "%USER_DATA%" mkdir "%USER_DATA%"

:: Launch REAL Chrome (No automation flags)
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --user-data-dir="%USER_DATA%" --no-first-run "https://www.upwork.com/ab/account-security/login" "https://www.linkedin.com/checkpoint/lg/login"

echo.
echo ===========================================
echo   AFTER CLOSING THE BROWSER, THE SWARM IS READY.
echo ===========================================
pause
