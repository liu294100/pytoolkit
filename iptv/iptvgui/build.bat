@echo off
setlocal

echo ========================================
echo   IPTV Player - Build Script
echo ========================================
echo.

cd /d "%~dp0"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found, please install Python 3.10+
    pause
    exit /b 1
)

REM Check PyInstaller
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing PyInstaller...
    pip install pyinstaller
)

REM Clean old build
echo [INFO] Cleaning old build files...
if exist "build" rmdir /s /q build
if exist "dist" rmdir /s /q dist

REM Build using spec file
echo [INFO] Building IPTV Player...
echo [INFO] This may take a few minutes...
echo.

pyinstaller iptv_player.spec --noconfirm --clean

if errorlevel 1 (
    echo.
    echo [ERROR] Build failed!
    echo.
    echo Try running with console to see errors:
    echo   pyinstaller iptv_player.spec --noconfirm --clean
    pause
    exit /b 1
)

REM Create cache directory
echo [INFO] Creating cache directory...
mkdir "dist\IPTV Player\cache" 2>nul

REM Check output
if not exist "dist\IPTV Player\IPTV Player.exe" (
    echo [ERROR] Build output not found!
    pause
    exit /b 1
)

echo.
echo ========================================
echo   Build completed!
echo   Output: dist\IPTV Player\
echo ========================================
echo.
echo Files:
dir /b "dist\IPTV Player\*.exe" 2>nul
echo.

REM Ask to open folder
set /p OPEN_FOLDER="Open output folder? [Y/n]: "
if /i not "%OPEN_FOLDER%"=="n" (
    explorer "dist\IPTV Player"
)

pause
