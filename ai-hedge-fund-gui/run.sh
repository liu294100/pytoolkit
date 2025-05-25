#!/bin/bash

echo "AI Hedge Fund GUI 启动中..."

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "错误: 未检测到Python环境，请安装Python 3.8或更高版本。"
    exit 1
fi

# 检查是否需要安装依赖
if [ ! -d "venv" ]; then
    echo "首次运行，正在创建虚拟环境并安装依赖..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败，请检查网络连接或手动安装依赖。"
        exit 1
    fi
else
    source venv/bin/activate
fi

# 运行应用
echo "启动AI Hedge Fund GUI..."
python3 main.py

# 退出虚拟环境
deactivate

echo "按任意键退出..."
read -n 1