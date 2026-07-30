@echo off
echo Building IPTV Pro...
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
