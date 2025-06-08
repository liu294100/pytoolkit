@echo off
echo ========================================
echo TradingAgents GUI Launcher
echo ========================================
echo.

:: Check if virtual environment exists
if exist "tradingagents_env\Scripts\activate.bat" (
    echo Activating virtual environment...
    call tradingagents_env\Scripts\activate.bat
    echo Virtual environment activated.
    echo.
)

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    echo Please run install.bat first or install Python manually
    pause
    exit /b 1
)

:: Check if main.py exists
if not exist "main.py" (
    echo ERROR: main.py not found in current directory
    echo Please make sure you're running this script from the TradingAgentsGUI folder
    pause
    exit /b 1
)

:: Display startup information
echo Starting TradingAgents GUI...
echo.
echo Tips:
echo - Make sure you have your API keys ready
echo - OpenAI API key for LLM functionality
echo - FinnHub API key for market data
echo - You can also run without API keys using mock data
echo.
echo Press Ctrl+C to stop the application
echo.

:: Run the application
python main.py

:: Check exit code
if errorlevel 1 (
    echo.
    echo ERROR: Application exited with an error
    echo Check the error messages above for details
    echo.
    echo Common issues:
    echo - Missing dependencies: run install.bat
    echo - Invalid API keys: check your keys in the GUI
    echo - Network issues: check your internet connection
    echo.
) else (
    echo.
    echo Application closed successfully.
)

pause