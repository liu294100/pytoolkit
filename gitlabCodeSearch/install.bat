@echo off
echo === GitLab Code Search - Install Dependencies ===
echo.

REM Install Python dependencies via proxy
echo Installing Python packages (via proxy)...
pip install --proxy http://127.0.0.1:7890 -r requirements.txt

REM Download ripgrep if not present
if not exist "rg.exe" (
    echo.
    echo Downloading ripgrep...
    powershell -Command "$ProgressPreference='SilentlyContinue'; Invoke-WebRequest -Proxy 'http://127.0.0.1:7890' -Uri 'https://github.com/BurntSushi/ripgrep/releases/download/14.1.1/ripgrep-14.1.1-x86_64-pc-windows-msvc.zip' -OutFile '%TEMP%\rg.zip'; Expand-Archive -Path '%TEMP%\rg.zip' -DestinationPath '%TEMP%\rg_extract' -Force; Copy-Item '%TEMP%\rg_extract\ripgrep-14.1.1-x86_64-pc-windows-msvc\rg.exe' 'rg.exe'"
    if exist "rg.exe" (
        echo ripgrep downloaded successfully.
    ) else (
        echo [WARNING] Failed to download ripgrep. Please download manually from:
        echo https://github.com/BurntSushi/ripgrep/releases
        echo Place rg.exe in this directory.
    )
) else (
    echo ripgrep already exists, skipping download.
)

echo.
echo === Installation complete ===
pause
