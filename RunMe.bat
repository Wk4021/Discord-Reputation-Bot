@echo off
REM ────────────────────────────────────────────────
REM  run_bot.bat – activate venv if it exists, else use global Python
REM ────────────────────────────────────────────────

REM 1) Change to the directory of this script
cd /d "%~dp0"

REM 2) If a virtualenv activation script exists, call it
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found, running global python.
)

REM 3) Run the bot
echo Starting bot...
python bot.py

REM 4) Keep the window open on exit
echo.
echo Bot has exited. Press any key to close this window.
pause
