@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Face Detection Environment Setup
echo ========================================
echo.

echo [1/4] Checking Python version...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please install Python 3.11 or 3.12
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Current Python version: %PYTHON_VERSION%

echo.
echo [2/4] Checking conda availability...
conda --version >nul 2>&1
if errorlevel 1 (
    echo Conda not available, trying direct install
    goto direct_install
) else (
    echo Conda available, creating virtual environment
    goto conda_install
)

:conda_install
echo.
echo [3/4] Creating conda environment...
conda create -n face_detect python=3.12 -y
if errorlevel 1 (
    echo Conda environment creation failed, trying direct install
    goto direct_install
)

echo Activating conda environment...
call conda activate face_detect
if errorlevel 1 (
    echo Environment activation failed
    pause
    exit /b 1
)

echo Installing dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed
    pause
    exit /b 1
)

goto test_install

:direct_install
echo.
echo [3/4] Installing dependencies directly...
pip install -r requirements.txt
if errorlevel 1 (
    echo Dependency installation failed - MediaPipe compatibility issue
    echo Please use Python 3.11 or 3.12
    pause
    exit /b 1
)

:test_install
echo.
echo [4/4] Testing installation...
python test_gui.py
if errorlevel 1 (
    echo Test failed
    pause
    exit /b 1
)

echo.
echo ========================================
echo Environment setup completed!
echo ========================================
echo.
echo Usage:
echo 1. Run full GUI: python face_detect_gui.py
echo 2. Run lite GUI: python face_detect_gui_lite.py
echo.
set /p choice="Start GUI now? (y/n): "
if /i "%choice%"=="y" (
    python face_detect_gui.py
)

echo.
echo For issues, check MediaPipe installation guide
pause