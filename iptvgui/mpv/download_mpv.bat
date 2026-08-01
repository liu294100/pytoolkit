@echo off
setlocal enabledelayedexpansion

echo ========================================
echo   MPV Library Downloader
echo ========================================
echo.

cd /d "%~dp0"

REM Check if already exists
if exist "libmpv-2.dll" (
    echo [INFO] libmpv-2.dll already exists.
    set /p OVERWRITE="Download again? [y/N]: "
    if /i not "!OVERWRITE!"=="y" (
        echo Skipped.
        pause
        exit /b 0
    )
)

REM Try Python first
python --version >nul 2>&1
if not errorlevel 1 (
    echo [INFO] Using Python to download...
    python download_mpv.py
    if not errorlevel 1 (
        pause
        exit /b 0
    )
)

REM Try PowerShell
echo [INFO] Using PowerShell to download...

set "MPV_URL=https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z"
set "ARCHIVE=mpv-dev.7z"

echo [INFO] Downloading mpv-dev...
echo        URL: %MPV_URL%
powershell -Command "Invoke-WebRequest -Uri '%MPV_URL%' -OutFile '%ARCHIVE%' -UseBasicParsing"

if not exist "%ARCHIVE%" (
    echo [ERROR] Download failed!
    echo.
    echo Please download manually from:
    echo %MPV_URL%
    pause
    exit /b 1
)

echo [INFO] Extracting libmpv-2.dll...

REM Try 7-Zip
if exist "C:\Program Files\7-Zip\7z.exe" (
    "C:\Program Files\7-Zip\7z.exe" e "%ARCHIVE%" libmpv-2.dll -y
    goto :cleanup
)

REM Try py7zr
pip show py7zr >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing py7zr...
    pip install py7zr -q
)

python -c "import py7zr; z=py7zr.SevenZipFile('%ARCHIVE%','r'); z.extract(targets=['libmpv-2.dll']); z.close()"

:cleanup
if exist "%ARCHIVE%" del "%ARCHIVE%"

if exist "libmpv-2.dll" (
    echo.
    echo ========================================
    echo   Download completed!
    echo   File: libmpv-2.dll
    echo ========================================
) else (
    echo.
    echo [ERROR] Extraction failed!
    echo Please download manually from:
    echo https://github.com/shinchiro/mpv-winbuild-cmake/releases
)

pause
