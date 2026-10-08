@echo off
REM ===========================================================
REM  Discord Reputation Bot - Startup Script
REM ===========================================================

title Discord Reputation Bot
REM Show emoji and other UTF-8 output from the bot correctly
chcp 65001 >nul

REM Run from the folder this script lives in
cd /d "%~dp0"
set /a empty_inputs=0

:menu
echo ===========================================================
echo                  Discord Reputation Bot
echo ===========================================================
echo.
echo   [1] Start the bot
echo   [2] Install/Update requirements
echo   [0] Exit
echo.
set "choice="
set /p "choice=Enter your choice (0-2): "
REM Stop if input keeps coming back empty (e.g. the input stream was closed)
if defined choice goto :got_choice
set /a empty_inputs+=1
if %empty_inputs% GEQ 3 goto :eof
goto :menu

:got_choice
set /a empty_inputs=0
REM Strip quotes so unusual input can't break the comparisons below
set "choice=%choice:"=%"

if "%choice%"=="1" goto :run_bot
if "%choice%"=="2" goto :install_requirements
if "%choice%"=="0" goto :eof

echo Invalid choice. Please enter 0, 1 or 2.
echo.
goto :menu

:install_requirements
echo.
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment in .venv ...
    py -3 -m venv .venv 2>nul || python -m venv .venv
    if errorlevel 1 (
        echo Could not create a virtual environment. Is Python 3.11+ installed and on PATH?
        echo.
        goto :menu
    )
)
echo Installing/updating requirements...
".venv\Scripts\python.exe" -m pip install --upgrade pip
".venv\Scripts\python.exe" -m pip install -r requirements.txt
echo.
echo Requirements installation completed!
echo.
goto :menu

:run_bot
if not exist ".venv\Scripts\python.exe" (
    echo No virtual environment found. Choose [2] first to install the requirements.
    echo.
    goto :menu
)
echo.
echo Starting Discord bot... Press Ctrl+C to stop.
echo.
".venv\Scripts\python.exe" bot.py
echo.
echo Discord bot has exited.
pause
