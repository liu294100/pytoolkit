#!/bin/bash

cd "$(dirname "$0")"

echo "================================"
echo "  IPTV Player - PyQt6 + VLC"
echo "================================"
echo

# 检查虚拟环境
if [ -f ".venv/bin/python" ]; then
    echo "使用虚拟环境: .venv"
    PYTHON=".venv/bin/python"
elif [ -f "venv/bin/python" ]; then
    echo "使用虚拟环境: venv"
    PYTHON="venv/bin/python"
else
    echo "使用系统 Python"
    PYTHON="python3"
fi

# 检查 Python 版本
if ! $PYTHON --version &> /dev/null; then
    echo "[错误] 未找到 Python，请安装 Python 3.10+"
    exit 1
fi

$PYTHON --version

# 检查依赖
if ! $PYTHON -c "import PyQt6" 2>/dev/null; then
    echo "[提示] 正在安装依赖..."
    $PYTHON -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "[错误] 依赖安装失败"
        exit 1
    fi
fi

# 检查 VLC
if ! $PYTHON -c "import vlc" 2>/dev/null; then
    echo
    echo "[警告] 未检测到 python-vlc 或 VLC 播放器"
    echo "请确保已安装:"
    echo "  macOS:  brew install vlc && pip install python-vlc"
    echo "  Ubuntu: sudo apt install vlc && pip install python-vlc"
    echo "  Fedora: sudo dnf install vlc && pip install python-vlc"
    echo
fi

echo
echo "启动 IPTV Player..."
echo

$PYTHON main.py
