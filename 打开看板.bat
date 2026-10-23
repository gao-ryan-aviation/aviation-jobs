@echo off
REM Open dashboard only (no re-crawl). ASCII-only file.
cd /d "%~dp0"
if not exist "docs\index.html" (
    echo ERROR: docs\index.html not found. Run updater first.
    pause
    exit /b 1
)
start "" "docs\index.html"
