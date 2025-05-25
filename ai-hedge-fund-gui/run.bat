@echo off
echo AI Hedge Fund GUI 启动中...

:: 检查Python环境
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo 错误: 未检测到Python环境，请安装Python 3.8或更高版本。
    pause
    exit /b 1
)

:: 检查是否需要安装依赖
if not exist venv (
    echo 首次运行，正在创建虚拟环境并安装依赖...
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo 错误: 依赖安装失败，请检查网络连接或手动安装依赖。
        pause
        exit /b 1
    )
) else (
    call venv\Scripts\activate.bat
)

:: 运行应用
echo 启动AI Hedge Fund GUI...
python main.py

:: 退出虚拟环境
call venv\Scripts\deactivate.bat

pause