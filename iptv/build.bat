@echo off
chcp 65001 >nul
echo 正在打包 IPTV Pro...
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo 未找到虚拟环境，正在创建...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

echo.
echo 安装 PyInstaller...
pip install pyinstaller

echo.
echo 开始打包...
pyinstaller --onefile --name iptv-pro --add-data "templates;templates" --add-data "static;static" --add-data "ref;ref" --console app.py

echo.
if exist "dist\iptv-pro.exe" (
    echo ========================================
    echo 打包完成！
    echo 可执行文件位置: dist\iptv-pro.exe
    echo ========================================
) else (
    echo 打包失败，请检查错误信息
)

pause
