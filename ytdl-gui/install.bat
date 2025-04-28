@echo off
setlocal

:: ==========================================================================
:: Configuration Section
:: ==========================================================================

:: --- Python Path ---
:: Set the full path to your python.exe here.
:: Leave empty to use the 'python' command found in the system PATH.
:: Example: set PYTHON_EXE_CONFIG=C:\Users\YourUser\AppData\Local\Programs\Python\Python310\python.exe
set PYTHON_EXE_CONFIG=E:\Program Files\Python\Python313\python.exe

:: --- Proxy URL ---
:: Set your proxy server URL here if needed.
:: Leave empty if you don't need a proxy.
:: Example: set PROXY_URL_CONFIG=http://user:password@proxy.example.com:8080
set PROXY_URL_CONFIG=

:: --- Requirements File ---
:: The name of your requirements file.
set REQUIREMENTS_FILE=requirements.txt

:: ==========================================================================
:: Script Logic (Do not modify below unless you know what you are doing)
:: ==========================================================================
echo.
echo Python Installation Script
echo ==========================
echo Using requirements file: %REQUIREMENTS_FILE%
echo.

REM --- Determine Python Command ---
set PYTHON_CMD=
if "%PYTHON_EXE_CONFIG%"=="" (
    set PYTHON_CMD=python
    echo Using default 'python' from system PATH.
) else (
    if not exist "%PYTHON_EXE_CONFIG%" (
        echo ERROR: Configured Python executable not found at "%PYTHON_EXE_CONFIG%".
        goto :error_exit
    )
    REM Ensure quotes handle spaces in path
    set PYTHON_CMD="%PYTHON_EXE_CONFIG%"
    echo Using configured Python at: %PYTHON_CMD%
)
echo.

REM --- Determine Proxy Argument ---
set PROXY_ARG=
if not "%PROXY_URL_CONFIG%"=="" (
    set PROXY_ARG=--proxy "%PROXY_URL_CONFIG%"
    echo Using configured proxy: %PROXY_URL_CONFIG%
) else (
    echo No proxy configured.
)
echo.

REM --- Check if requirements file exists ---
if not exist "%REQUIREMENTS_FILE%" (
    echo ERROR: Requirements file "%REQUIREMENTS_FILE%" not found in the current directory.
    goto :error_exit
)

:: --- Execute pip install ---
echo Running: %PYTHON_CMD% -m pip install -r "%REQUIREMENTS_FILE%" %PROXY_ARG%
echo ========================================================================
%PYTHON_CMD% -m pip install -r "%REQUIREMENTS_FILE%" %PROXY_ARG%

if errorlevel 1 (
    echo.
    echo ERROR: pip install command failed. Please check the output above.
    goto :error_exit
)

echo.
echo ========================================================================
echo Installation completed successfully.
goto :success_exit

:error_exit
echo Script finished with errors.
pause
exit /b 1

:success_exit
echo Script finished successfully.
pause
exit /b 0

endlocal