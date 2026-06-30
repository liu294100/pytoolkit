@echo off
:: UWP Network Loopback Manager Launcher
:: Automatically requests administrator privileges to run

:: Check for administrator privileges
net session >nul 2>&1

:: If not running as administrator, relaunch via PowerShell with elevation
if %errorLevel% neq 0 (
    echo Requesting administrator privileges...
    powershell -Command "Start-Process python -ArgumentList 'uwp_loopback_manager.py' -Verb RunAs -WorkingDirectory '%~dp0'"
    exit /b
)

:: Already running as administrator, execute directly
cd /d "%~dp0"
python uwp_loopback_managerV2.py
pause
