@echo off
echo === GitLab Code Search - Build EXE ===
echo.

REM Check if PyInstaller is installed
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Installing PyInstaller...
    pip install --proxy http://127.0.0.1:7890 pyinstaller
)

echo Building executable...
pyinstaller --noconfirm --onedir --windowed ^
    --name "GitLabCodeSearch" ^
    --add-data "rg.exe;." ^
    --add-data "config.json;." ^
    --hidden-import "PySide6.QtCore" ^
    --hidden-import "PySide6.QtGui" ^
    --hidden-import "PySide6.QtWidgets" ^
    --hidden-import "gitlab" ^
    --hidden-import "git" ^
    --hidden-import "pygments" ^
    main.py

if exist "dist\GitLabCodeSearch" (
    echo.
    echo === Build successful ===
    echo Output: dist\GitLabCodeSearch\
    echo Run:    dist\GitLabCodeSearch\GitLabCodeSearch.exe
) else (
    echo.
    echo === Build failed ===
)

pause
