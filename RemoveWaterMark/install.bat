@echo off
echo ======================================================================
echo                   水印去除工具 - 依赖项安装
echo ======================================================================
echo.

REM 检查Python是否已安装
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [错误] 未检测到Python。请安装Python 3.6或更高版本。
    echo 您可以从 https://www.python.org/downloads/ 下载Python。
    echo.
    pause
    exit /b 1
)

echo [信息] 检测到Python，开始安装依赖项...
echo.

REM 安装依赖项
echo [信息] 正在安装所需的Python库...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [错误] 安装依赖项时出错。请检查上面的错误信息。
    pause
    exit /b 1
)

echo.
echo [成功] 所有依赖项已成功安装！
echo.
echo 您现在可以通过运行 run.py 来启动水印去除工具。
echo.
echo 按任意键退出...
pause > nul