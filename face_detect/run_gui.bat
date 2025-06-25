@echo off
chcp 65001 >nul
echo 启动人脸检测GUI工具...
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python，请先安装Python 3.7或更高版本
    pause
    exit /b 1
)

REM 检查是否存在虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo 激活虚拟环境...
    call venv\Scripts\activate.bat
)

REM 检查依赖是否安装
echo 检查依赖包...
python -c "import cv2, mediapipe, PIL, pydantic" >nul 2>&1
if errorlevel 1 (
    echo 正在安装依赖包...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo 错误: 依赖包安装失败
        pause
        exit /b 1
    )
)

REM 启动GUI应用
echo 启动GUI应用...
python face_detect_gui.py

if errorlevel 1 (
    echo.
    echo 应用程序异常退出
    pause
)