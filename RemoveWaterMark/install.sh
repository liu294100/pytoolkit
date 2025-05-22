#!/bin/bash

# ==========================================================================
# 水印去除工具 - 依赖项安装脚本
# ==========================================================================

# 文本颜色定义
RED="\033[0;31m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
BLUE="\033[0;34m"
NC="\033[0m" # No Color

# 错误处理函数
error_exit() {
    echo -e "${RED}[错误] $1${NC}" >&2
    echo ""
    echo "按Enter键退出..."
    read
    exit 1
}

# 标题
echo "========================================================================"
echo "                   水印去除工具 - 依赖项安装"
echo "========================================================================"
echo ""

# 检查Python是否已安装
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
    # 确保是Python 3
    PY_VERSION=$($PYTHON_CMD --version 2>&1)
    if [[ ! $PY_VERSION =~ Python\ 3 ]]; then
        error_exit "检测到 $PY_VERSION，但需要Python 3。请安装Python 3或确保'python3'命令可用。"
    fi
else
    error_exit "未检测到Python。请安装Python 3.6或更高版本。"
fi

echo -e "${GREEN}[信息] 检测到 $($PYTHON_CMD --version 2>&1)${NC}"

# 检查pip是否可用
if ! $PYTHON_CMD -m pip --version &>/dev/null; then
    echo -e "${YELLOW}[警告] 未检测到pip。尝试安装...${NC}"
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        echo "在macOS上，pip应该随Python一起安装。请尝试重新安装Python。"
        error_exit "未找到pip"
    elif [[ "$(uname)" == "Linux" ]]; then
        # Linux
        if command -v apt-get &>/dev/null; then
            # Debian/Ubuntu
            echo -e "${BLUE}使用apt安装pip...${NC}"
            sudo apt-get update && sudo apt-get install -y python3-pip || error_exit "安装pip失败"
        elif command -v dnf &>/dev/null; then
            # Fedora
            echo -e "${BLUE}使用dnf安装pip...${NC}"
            sudo dnf install -y python3-pip || error_exit "安装pip失败"
        elif command -v yum &>/dev/null; then
            # CentOS/RHEL
            echo -e "${BLUE}使用yum安装pip...${NC}"
            sudo yum install -y python3-pip || error_exit "安装pip失败"
        elif command -v pacman &>/dev/null; then
            # Arch Linux
            echo -e "${BLUE}使用pacman安装pip...${NC}"
            sudo pacman -S --noconfirm python-pip || error_exit "安装pip失败"
        else
            error_exit "未找到包管理器，请手动安装pip"
        fi
    else
        error_exit "未知操作系统，请手动安装pip"
    fi
fi

# 检查tkinter是否已安装
echo -e "${BLUE}[信息] 检查tkinter...${NC}"
if ! $PYTHON_CMD -c "import tkinter" &>/dev/null; then
    echo -e "${YELLOW}[警告] 未检测到tkinter。尝试安装...${NC}"
    if [[ "$(uname)" == "Darwin" ]]; then
        # macOS
        echo -e "${YELLOW}在macOS上，tkinter应该随Python一起安装。请尝试重新安装Python。${NC}"
        echo -e "${YELLOW}您可以使用Homebrew安装Python：brew install python${NC}"
    elif [[ "$(uname)" == "Linux" ]]; then
        # Linux
        if command -v apt-get &>/dev/null; then
            # Debian/Ubuntu
            echo -e "${BLUE}使用apt安装tkinter...${NC}"
            sudo apt-get update && sudo apt-get install -y python3-tk || error_exit "安装tkinter失败"
        elif command -v dnf &>/dev/null; then
            # Fedora
            echo -e "${BLUE}使用dnf安装tkinter...${NC}"
            sudo dnf install -y python3-tkinter || error_exit "安装tkinter失败"
        elif command -v yum &>/dev/null; then
            # CentOS/RHEL
            echo -e "${BLUE}使用yum安装tkinter...${NC}"
            sudo yum install -y python3-tkinter || error_exit "安装tkinter失败"
        elif command -v pacman &>/dev/null; then
            # Arch Linux
            echo -e "${BLUE}使用pacman安装tkinter...${NC}"
            sudo pacman -S --noconfirm tk || error_exit "安装tkinter失败"
        else
            echo -e "${YELLOW}未找到包管理器，请手动安装tkinter${NC}"
        fi
    else
        echo -e "${YELLOW}未知操作系统，请手动安装tkinter${NC}"
    fi
fi

# 安装Python依赖项
echo -e "${BLUE}[信息] 正在安装Python依赖项...${NC}"
$PYTHON_CMD -m pip install --upgrade pip || error_exit "更新pip失败"
$PYTHON_CMD -m pip install -r requirements.txt || error_exit "安装依赖项失败"

echo ""
echo -e "${GREEN}[成功] 所有依赖项已成功安装！${NC}"
echo ""
echo "您现在可以通过运行以下命令来启动水印去除工具："
echo -e "${BLUE}$PYTHON_CMD run.py${NC}"
echo ""
echo "按Enter键退出..."
read