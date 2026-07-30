@echo off
chcp 65001 >nul
echo Building IPTV Pro...
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo Virtual environment not found, creating...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo Installing PyInstaller...
pip install pyinstaller

echo.
echo Starting build...
pyinstaller --onefile --name iptv-pro --add-data "templates;templates" --add-data "static;static" --add-data "ref;ref" --console app.py

echo.
if exist "dist\iptv-pro.exe" (
    echo ========================================
    echo Build completed!
    echo Output: dist\iptv-pro.exe
    echo ========================================
) else (
    echo Build failed, please check error messages
)

pause
