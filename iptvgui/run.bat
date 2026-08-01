@echo off
title IPTV Player

cd /d "%~dp0"

echo ========================================
echo   IPTV Player - PySide6 + MPV
echo ========================================
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

python --version

REM Check MPV
if not exist "mpv\libmpv-2.dll" (
    echo.
    echo [WARN] mpv\libmpv-2.dll not found
    echo Download: https://github.com/shinchiro/mpv-winbuild-cmake/releases
    echo.
)

REM Check dependencies
python -c "import PySide6" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting...
echo.

python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Program exited with error
    pause
)
