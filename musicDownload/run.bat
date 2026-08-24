@echo off
title Music Downloader Pro

echo ========================================
echo   Music Downloader Pro v2.4
echo ========================================
echo.

:: Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

:: Check dependencies
echo [INFO] Checking dependencies...

python -c "import PyQt5" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyQt5...
    pip install PyQt5 -q
)

python -c "import musicdl" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing musicdl...
    pip install musicdl -q
)

python -c "import requests" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requests...
    pip install requests -q
)

echo [OK] Dependencies ready
echo.
echo [INFO] Starting...
echo.

:: Run
python music_downloader.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with error
    pause
)
