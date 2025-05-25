@echo off
REM ────────────────────────────────────────────────
REM  Windows .BAT to activate your venv and run bot.py
REM ────────────────────────────────────────────────

REM 1) Change directory to the location of this script
cd /d "%~dp0"

REM 2) Activate the virtual environment
IF EXIST ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
) ELSE IF EXIST "venv\Scripts\activate.bat" (
    call venv\Scripts\activate.bat
) ELSE (
    echo ERROR: No virtualenv found in .venv or venv folder.
    pause
    exit /b 1
)

REM 3) (Optional) Show which python is running
where python

REM 4) Run the bot
python bot.py

REM 5) Keep the window open on exit / crash
echo.
echo Bot has exited. Press any key to close.
pause
