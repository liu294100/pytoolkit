@echo off
setlocal
cd /d "%~dp0"

rem ==========================================================
rem  Build youtube_downloader_pro.py into a single exe
rem  Output: dist_pro\YouTubeDownloaderPro.exe
rem ==========================================================
set SCRIPT=youtube_downloader_pro.py
set NAME=YouTubeDownloaderPro

echo [1/3] Checking dependencies...
python -m pip install -q pyinstaller customtkinter yt-dlp pillow
if errorlevel 1 goto :error

echo [2/3] Generating icon...
if not exist youtube_pro.ico python make_icon_pro.py
if errorlevel 1 goto :error

echo [3/3] Running PyInstaller...
python -m PyInstaller --noconfirm --clean --onefile --windowed --name "%NAME%" --icon "%~dp0youtube_pro.ico" --add-data "%~dp0youtube_pro.ico;." --collect-data customtkinter --collect-submodules yt_dlp --distpath "%~dp0dist_pro" --workpath "%~dp0build_pro" --specpath "%~dp0build_pro" "%~dp0%SCRIPT%"
if errorlevel 1 goto :error

echo.
echo Done: %~dp0dist_pro\%NAME%.exe
echo Note: ffmpeg must be installed and on PATH for merging / subtitle conversion.
pause
exit /b 0

:error
echo Build failed, see output above.
pause
exit /b 1
