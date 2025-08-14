@echo off
REM ════════════════════════════════════════════════════════════
REM  Quick launcher for Discord Review Dashboard
REM ════════════════════════════════════════════════════════════

title Discord Review Dashboard

cd /d "%~dp0"

REM Activate virtual environment if available
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found, using global Python...
)

echo.
echo ════════════════════════════════════════════════════════════
echo                Discord Review Dashboard
echo ════════════════════════════════════════════════════════════
echo.
echo Starting web dashboard...
echo Dashboard will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop the server.
echo Close this window to stop the dashboard.
echo.

cd web_dashboard
python run_dashboard.py

echo.
echo Dashboard stopped. Press any key to close.
pause