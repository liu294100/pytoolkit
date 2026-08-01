@echo off
setlocal

echo ========================================
echo   MPV Library Downloader
echo ========================================
echo.

cd /d "%~dp0"

REM Run the script in mpv directory
if exist "mpv\download_mpv.bat" (
    call "mpv\download_mpv.bat"
) else (
    echo [ERROR] mpv\download_mpv.bat not found
    echo.
    echo Please download manually from:
    echo https://github.com/shinchiro/mpv-winbuild-cmake/releases/download/20260610/mpv-dev-x86_64-v3-20260610-git-304426c.7z
    echo.
    echo Extract libmpv-2.dll to mpv\ directory
    pause
)
