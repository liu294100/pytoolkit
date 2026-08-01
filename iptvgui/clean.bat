@echo off
title Clean Python Cache

cd /d "%~dp0"

echo ========================================
echo   Clean Python Cache Files
echo ========================================
echo.

echo Removing __pycache__ directories...
for /d /r %%i in (__pycache__) do (
    if exist "%%i" (
        echo Delete: %%i
        rd /s /q "%%i"
    )
)

echo.
echo Removing .pyc files...
for /r %%i in (*.pyc) do (
    if exist "%%i" (
        echo Delete: %%i
        del /q "%%i"
    )
)

echo.
echo Removing .pyo files...
for /r %%i in (*.pyo) do (
    if exist "%%i" (
        echo Delete: %%i
        del /q "%%i"
    )
)

echo.
echo ========================================
echo   Clean complete!
echo ========================================
echo.
pause
