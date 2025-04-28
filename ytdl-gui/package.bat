@echo off
setlocal

:: ==========================================================================
:: Configuration Section
:: ==========================================================================

:: --- Python Script to Package ---
:: The main Python script you want to turn into an executable.
set PYTHON_SCRIPT=run.py

:: --- Output Executable Name ---
:: The desired name for the final .exe file (without the .exe extension).
set OUTPUT_NAME=YoutubeDownloader          

:: --- Path to PyInstaller ---
:: The full path to your pyinstaller.exe. Ensure this is correct for your system.
set PYINSTALLER_EXE="E:\Program Files\Python\Python313\Scripts\pyinstaller.exe"
:: Alternative: If pyinstaller is in your system PATH, you could use:
:: set PYINSTALLER_EXE=pyinstaller.exe

:: --- PyInstaller Options ---
:: Add any other options you need here.
:: --onefile: Bundle everything into a single executable.
:: --windowed: Create a GUI application (no console window). Use --console for console apps.
:: You can add others like --icon="path/to/icon.ico"
:: set PYINSTALLER_OPTIONS=--onefile --windowed
set PYINSTALLER_OPTIONS=--onefile --windowed

:: ==========================================================================
:: Script Logic (Do not modify below unless you know what you are doing)
:: ==========================================================================
echo.
echo PyInstaller Packaging Script
echo ============================

REM --- Pre-checks ---
if not exist %PYINSTALLER_EXE% (
    echo ERROR: PyInstaller executable not found at the specified path:
    echo %PYINSTALLER_EXE%
    echo Please check the PYINSTALLER_EXE variable in this script.
    goto :error_exit
)

if not exist "%PYTHON_SCRIPT%" (
    echo ERROR: Python script "%PYTHON_SCRIPT%" not found in the current directory.
    echo Please make sure the script exists and run this batch file from the same directory.
    goto :error_exit
)

echo Packaging Script: %PYTHON_SCRIPT%
echo Output Name:      %OUTPUT_NAME%.exe
echo Using PyInstaller: %PYINSTALLER_EXE%
echo Options:          %PYINSTALLER_OPTIONS%
echo.

REM --- Optional: Add Python and Scripts directory to PATH temporarily ---
REM --- This can sometimes help PyInstaller find modules correctly ---
echo Adding Python environment to PATH temporarily...
for %%i in (%PYINSTALLER_EXE%) do set PYINSTALLER_DIR=%%~dpi
for %%i in ("%PYINSTALLER_DIR%..") do set PYTHON_DIR=%%~fi
set PATH=%PYTHON_DIR%;%PYINSTALLER_DIR%;%PATH%
echo   Python Dir: %PYTHON_DIR%
echo   Scripts Dir: %PYINSTALLER_DIR%
echo.


:: --- Execute PyInstaller ---
echo Running PyInstaller...
echo Command: %PYINSTALLER_EXE% %PYINSTALLER_OPTIONS% --name "%OUTPUT_NAME%" "%PYTHON_SCRIPT%"
echo ========================================================================

%PYINSTALLER_EXE% %PYINSTALLER_OPTIONS% --name "%OUTPUT_NAME%" "%PYTHON_SCRIPT%"

if errorlevel 1 (
    echo.
    echo ERROR: PyInstaller failed. See output above for details.
    goto :error_exit
)

echo.
echo ========================================================================
echo PyInstaller completed successfully.
echo Your executable should be in the 'dist' sub-directory:
echo   dist\%OUTPUT_NAME%.exe
echo Other build files are in the 'build' directory and '%OUTPUT_NAME%.spec'.
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