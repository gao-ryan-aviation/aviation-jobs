@echo off
REM ============================================
REM  Aviation Jobs Board - One-click Updater
REM  Kept ASCII-only to avoid Windows codepage
REM  issues. All Chinese UI lives in update.ps1
REM ============================================
cd /d "%~dp0"
if not exist "%~dp0update.ps1" (
    echo ERROR: update.ps1 not found in "%~dp0"
    echo Please keep all files in the same folder.
    pause
    exit /b 1
)
where powershell >nul 2>nul
if errorlevel 1 (
    echo ERROR: PowerShell not available on this computer.
    pause
    exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0update.ps1"
echo.
pause
