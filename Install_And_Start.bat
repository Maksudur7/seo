@echo off
title Meta Threads SEO Bot - 1-Click Auto Setup & Launcher
color 0A
echo ============================================================
echo   🧵 Meta Threads Marketing Automation Hub - Setup Launcher
echo ============================================================
echo.

:: Check Python installation
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed on this PC!
    echo.
    echo Please install Python 3.10+ from https://www.python.org/downloads/
    echo IMPORTANT: Make sure to check "Add Python to PATH" during installation!
    echo.
    pause
    exit /b
)

echo [1/3] Checking and installing required packages...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet -r requirements.txt
python -m playwright install chromium

echo.
echo [2/3] Preparing workspace and configuration...
if not exist "data" mkdir "data"
if not exist "data\browser_profiles" mkdir "data\browser_profiles"

echo.
echo [3/3] Launching Meta Threads SEO Bot Software Window...
echo ============================================================
start "" python desktop_app.py

echo.
echo ✅ Setup finished! Threads SEO Bot is now running.
echo You can close this window now.
pause
