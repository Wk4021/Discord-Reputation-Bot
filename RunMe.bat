@echo off
REM ═══════════════════════════════════════════════════════════
REM  Discord Reputation Bot - Startup Script
REM ═══════════════════════════════════════════════════════════

title Discord Reputation Bot

REM 1) Change to the directory of this script
cd /d "%~dp0"

REM 2) Check for command line arguments (for hidden entry points)
if "%1"=="bot_only" goto :bot_only
if "%1"=="dashboard_only" goto :dashboard_only

REM 3) Show main menu
goto :menu

:install_requirements
echo.
echo ═══════════════════════════════════════════════════════════
echo                Installing Requirements
echo ═══════════════════════════════════════════════════════════
echo.

REM Check for virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found. Consider creating one with: python -m venv .venv
    echo Using global Python installation...
)

echo Installing/updating requirements...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo.
echo Requirements installation completed!
echo.
pause
goto :menu

:run_bot
echo.
echo ═══════════════════════════════════════════════════════════
echo                Starting Discord Bot
echo ═══════════════════════════════════════════════════════════
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found, running global python.
)

echo Starting Discord bot...
echo Bot will handle reviews, forums, and user interactions.
echo.
python bot.py

echo.
echo Discord bot has exited. Press any key to close this window.
pause
goto :exit

:run_dashboard
echo.
echo ═══════════════════════════════════════════════════════════
echo                Starting Web Dashboard
echo ═══════════════════════════════════════════════════════════
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found, running global python.
)

echo Starting web dashboard...
echo Dashboard will be available at: http://localhost:5000
echo Press Ctrl+C to stop the dashboard server.
echo.
cd web_dashboard
python run_dashboard.py
cd ..

echo.
echo Web dashboard has stopped. Press any key to close this window.
pause
goto :exit

:run_both
echo.
echo ═══════════════════════════════════════════════════════════
echo             Starting Both Bot and Dashboard
echo ═══════════════════════════════════════════════════════════
echo.

echo Starting Discord bot in new window...
start "Discord Bot" /min "%~dp0\RunMe.bat" bot_only

timeout /t 3 /nobreak >nul

echo Starting web dashboard in new window...
start "Web Dashboard" /min "%~dp0\RunMe.bat" dashboard_only

echo.
echo Both services are starting in separate windows:
echo   • Discord Bot: Check the "Discord Bot" window
echo   • Web Dashboard: Check the "Web Dashboard" window
echo   • Dashboard URL: http://localhost:5000
echo.
echo This window can be closed. The services are running independently.
echo.
pause
goto :exit

REM Hidden entry points for running individual services
:bot_only
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"
python bot.py
pause
goto :exit

:dashboard_only
if exist ".venv\Scripts\activate.bat" call ".venv\Scripts\activate.bat"  
if exist "venv\Scripts\activate.bat" call "venv\Scripts\activate.bat"
cd web_dashboard
python run_dashboard.py
pause
goto :exit

:menu
REM 2) Display banner
echo ═══════════════════════════════════════════════════════════
echo              Discord Reputation Bot V3.0-beta
echo ═══════════════════════════════════════════════════════════
echo.
echo Choose what to run:
echo   [1] Discord Bot (Main bot functionality)
echo   [2] Web Dashboard (User interface at http://localhost:5000)
echo   [3] Both (Bot + Dashboard in separate windows)
echo   [4] Bot + Integrated Dashboard (Recommended)
echo   [5] Install/Update Requirements
echo   [0] Exit
echo.
set /p choice="Enter your choice (0-5): "

REM 3) Handle user choice
if "%choice%"=="0" goto :exit
if "%choice%"=="1" goto :run_bot
if "%choice%"=="2" goto :run_dashboard
if "%choice%"=="3" goto :run_both
if "%choice%"=="4" goto :run_integrated
if "%choice%"=="5" goto :install_requirements

echo Invalid choice. Please enter 0, 1, 2, 3, 4, or 5.
echo.
goto :menu

:run_integrated
echo.
echo ═══════════════════════════════════════════════════════════
echo           Starting Bot with Integrated Dashboard
echo ═══════════════════════════════════════════════════════════
echo.

REM Activate virtual environment
if exist ".venv\Scripts\activate.bat" (
    echo Activating .venv...
    call ".venv\Scripts\activate.bat"
) else if exist "venv\Scripts\activate.bat" (
    echo Activating venv...
    call "venv\Scripts\activate.bat"
) else (
    echo No virtualenv found, running global python.
)

echo Starting integrated bot with web dashboard...
echo Discord bot will handle reviews, forums, and user interactions.
echo Web dashboard will be available at: http://localhost:5000
echo.
echo Press Ctrl+C to stop both services.
echo.
python bot.py

echo.
echo Services have stopped. Press any key to close this window.
pause
goto :exit

:exit
echo.
echo Goodbye!
timeout /t 2 /nobreak >nul
