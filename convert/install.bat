@echo off
echo 正在安装图片转PDF工具的依赖包...
echo.

pip install -r requirements.txt

if %errorlevel% equ 0 (
    echo.
    echo 安装完成！
    echo 现在可以运行 run.bat 启动程序
) else (
    echo.
    echo 安装失败，请检查网络连接或Python环境
)

pause