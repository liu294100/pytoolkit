#!/bin/bash

echo "启动人脸检测GUI工具..."
echo ""

# 检查Python是否安装
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到Python，请先安装Python 3.7或更高版本"
    exit 1
fi

# 检查是否存在虚拟环境
if [ -f "venv/bin/activate" ]; then
    echo "激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖是否安装
echo "检查依赖包..."
python3 -c "import cv2, mediapipe, PIL, pydantic" &> /dev/null
if [ $? -ne 0 ]; then
    echo "正在安装依赖包..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖包安装失败"
        exit 1
    fi
fi

# 启动GUI应用
echo "启动GUI应用..."
python3 face_detect_gui.py

if [ $? -ne 0 ]; then
    echo ""
    echo "应用程序异常退出"
    read -p "按回车键继续..."
fi