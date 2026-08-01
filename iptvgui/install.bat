@echo off
title Install IPTV Player Dependencies

cd /d "%~dp0"

echo ========================================
echo   IPTV Player - Install Dependencies
echo ========================================
echo.

REM Check Python
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    echo Please install Python 3.10+
    echo Download: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [1/3] Python version:
python --version
echo.

echo [2/3] Installing Python packages...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo.
echo [3/3] Checking MPV player...

if exist "mpv\libmpv-2.dll" (
    echo [OK] MPV ready: mpv\libmpv-2.dll
) else (
    echo [WARN] MPV library not found
    echo.
    echo Please download MPV dev package:
    echo   1. Visit https://github.com/shinchiro/mpv-winbuild-cmake/releases
    echo   2. Download mpv-dev-x86_64-xxxxxxxx-git-xxxxxx.7z
    echo   3. Extract libmpv-2.dll to %~dp0mpv\
    echo.
    
    if not exist "mpv" mkdir mpv
)

echo.
echo ========================================
echo   Installation complete!
echo ========================================
echo.
echo Run "run.bat" to start the program
echo.
pause
