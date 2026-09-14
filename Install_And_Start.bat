@echo off
title Meta Threads SEO Bot - 1-Click Auto Setup & Launcher
color 0A
echo ============================================================
echo   🧵 Meta Threads Marketing Automation Hub - Setup Launcher
echo ============================================================
echo.

set "PYTHON_EXE="

:: 1. Check default 'python' command
python --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=python"
    goto :FOUND
)

:: 2. Check Python Launcher 'py'
py --version >nul 2>&1
if %errorlevel% equ 0 (
    set "PYTHON_EXE=py"
    goto :FOUND
)

:: 3. Check AppData Local folder for current user
if exist "%LocalAppData%\Programs\Python\Python312\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python312\python.exe"
    goto :FOUND
)
if exist "%LocalAppData%\Programs\Python\Python3127\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python3127\python.exe"
    goto :FOUND
)
if exist "%LocalAppData%\Programs\Python\Python311\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python311\python.exe"
    goto :FOUND
)
if exist "%LocalAppData%\Programs\Python\Python310\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python310\python.exe"
    goto :FOUND
)
if exist "%LocalAppData%\Programs\Python\Python39\python.exe" (
    set "PYTHON_EXE=%LocalAppData%\Programs\Python\Python39\python.exe"
    goto :FOUND
)

:: 4. Check Program Files standard installation
if exist "C:\Program Files\Python312\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python312\python.exe"
    goto :FOUND
)
if exist "C:\Program Files\Python311\python.exe" (
    set "PYTHON_EXE=C:\Program Files\Python311\python.exe"
    goto :FOUND
)

echo [ERROR] Python was not found on this PC!
echo Opening Python download page in your web browser...
start https://www.python.org/downloads/
echo.
echo Please install Python and make sure to check:
echo  [x] Add python.exe to PATH
echo.
pause
exit /b 1

:FOUND
echo [1/3] Checking and installing required packages...
"%PYTHON_EXE%" -m pip install --quiet --upgrade pip
"%PYTHON_EXE%" -m pip install --quiet -r requirements.txt
"%PYTHON_EXE%" -m playwright install chromium

echo.
echo [2/3] Preparing workspace and configuration...
if not exist "data" mkdir "data"
if not exist "data\browser_profiles" mkdir "data\browser_profiles"

echo.
echo [3/3] Launching Meta Threads SEO Bot Software Window...
echo ============================================================
start "" "%PYTHON_EXE%" desktop_app.py

echo.
echo ✅ Setup finished! Threads SEO Bot is now running.
echo You can close this window now.
pause
exit /b 0
