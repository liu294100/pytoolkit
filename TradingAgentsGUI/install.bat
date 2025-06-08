@echo off
echo ========================================
echo TradingAgents GUI Installation Script
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo Python found:
python --version
echo.

:: Check Python version
for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Python version: %PYTHON_VERSION%
echo.

:: Create virtual environment (optional)
set /p CREATE_VENV="Do you want to create a virtual environment? (y/n): "
if /i "%CREATE_VENV%"=="y" (
    echo Creating virtual environment...
    python -m venv tradingagents_env
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    
    echo Activating virtual environment...
    call tradingagents_env\Scripts\activate.bat
    if errorlevel 1 (
        echo ERROR: Failed to activate virtual environment
        pause
        exit /b 1
    )
    echo Virtual environment activated.
    echo.
)

:: Upgrade pip
echo Upgrading pip...
python -m pip install --upgrade pip
if errorlevel 1 (
    echo WARNING: Failed to upgrade pip, continuing...
)
echo.

:: Install requirements
echo Installing required packages...
if exist requirements.txt (
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo ERROR: Failed to install requirements
        pause
        exit /b 1
    )
) else (
    echo requirements.txt not found, installing basic packages...
    python -m pip install requests numpy pandas matplotlib seaborn
    if errorlevel 1 (
        echo ERROR: Failed to install basic packages
        pause
        exit /b 1
    )
)

echo.
echo ========================================
echo Installation completed successfully!
echo ========================================
echo.
echo To run the application:
if /i "%CREATE_VENV%"=="y" (
    echo 1. Activate the virtual environment:
    echo    tradingagents_env\Scripts\activate.bat
    echo 2. Run the application:
    echo    python main.py
) else (
    echo    python main.py
)
echo.
echo To get started:
echo 1. Get your API keys:
echo    - OpenAI API: https://platform.openai.com/api-keys
echo    - FinnHub API: https://finnhub.io/
echo 2. Enter the API keys in the GUI when prompted
echo 3. Select a stock symbol and start trading analysis
echo.
echo For more information, see README.md
echo.
pause