@echo off
echo 启动图片转PDF工具...
echo.

python image_to_pdf_gui.py

if %errorlevel% neq 0 (
    echo.
    echo 程序运行出错，请确保已安装所需依赖
    echo 运行 install.bat 安装依赖包
    pause
)