#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 输出函数
print_header() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}人脸检测环境自动设置脚本${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️ $1${NC}"
}

print_info() {
    echo -e "${BLUE}📝 $1${NC}"
}

# 检查命令是否存在
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# 检查Python版本
check_python_version() {
    if ! command_exists python3; then
        if ! command_exists python; then
            print_error "Python未安装"
            echo "请先安装Python 3.11或3.12"
            echo "Ubuntu/Debian: sudo apt install python3.12"
            echo "CentOS/RHEL: sudo yum install python312"
            echo "macOS: brew install python@3.12"
            exit 1
        else
            PYTHON_CMD="python"
        fi
    else
        PYTHON_CMD="python3"
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | cut -d' ' -f2)
    echo "当前Python版本: $PYTHON_VERSION"
    
    # 检查版本兼容性
    if [[ $PYTHON_VERSION =~ ^3\.(11|12) ]]; then
        print_success "Python版本兼容"
        return 0
    elif [[ $PYTHON_VERSION =~ ^3\.13 ]]; then
        print_warning "Python 3.13检测到，MediaPipe不兼容"
        return 1
    else
        print_warning "未知Python版本，建议使用3.11或3.12"
        return 1
    fi
}

# 设置conda环境
setup_conda_env() {
    print_info "创建conda虚拟环境..."
    echo "环境名称: face_detect"
    echo "Python版本: 3.12"
    
    conda create -n face_detect python=3.12 -y
    if [ $? -ne 0 ]; then
        print_error "conda环境创建失败"
        exit 1
    fi
    
    print_success "conda环境创建成功"
    
    # 激活环境
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate face_detect
    if [ $? -ne 0 ]; then
        print_error "环境激活失败"
        exit 1
    fi
    
    print_success "环境激活成功"
}

# 安装依赖
install_dependencies() {
    print_info "安装项目依赖..."
    
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        print_error "依赖安装失败"
        if [[ $PYTHON_VERSION =~ ^3\.13 ]]; then
            echo "可能是MediaPipe兼容性问题"
            echo "建议使用conda虚拟环境"
        fi
        exit 1
    fi
    
    print_success "依赖安装成功"
}

# 测试安装
test_installation() {
    print_info "测试安装结果..."
    
    $PYTHON_CMD test_gui.py
    if [ $? -ne 0 ]; then
        print_error "测试失败，请检查安装"
        exit 1
    fi
    
    print_success "测试通过"
}

# 显示使用说明
show_usage() {
    echo
    echo -e "${BLUE}========================================${NC}"
    print_success "环境设置完成！"
    echo -e "${BLUE}========================================${NC}"
    echo
    
    # 检查是否使用了conda环境
    if conda info --envs 2>/dev/null | grep -q "face_detect"; then
        print_info "使用说明："
        echo "1. 每次使用前激活环境："
        echo "   conda activate face_detect"
        echo
        echo "2. 运行GUI应用："
        echo "   python face_detect_gui.py"
        echo
        echo "3. 使用完毕后退出环境："
        echo "   conda deactivate"
        echo
        
        echo "🚀 现在可以运行GUI了！"
        read -p "是否立即启动GUI？(y/n): " choice
        if [[ $choice =~ ^[Yy]$ ]]; then
            echo "启动GUI..."
            $PYTHON_CMD face_detect_gui.py
        fi
    else
        print_info "使用说明："
        echo "直接运行GUI应用："
        echo "   $PYTHON_CMD face_detect_gui.py"
        echo
        
        echo "🚀 现在可以运行GUI了！"
        read -p "是否立即启动GUI？(y/n): " choice
        if [[ $choice =~ ^[Yy]$ ]]; then
            echo "启动GUI..."
            $PYTHON_CMD face_detect_gui.py
        fi
    fi
    
    echo
    echo "如有问题，请查看 MediaPipe安装指南.md"
}

# 主函数
main() {
    print_header
    
    # 步骤1：检查Python版本
    echo "[1/5] 检查Python版本..."
    if check_python_version; then
        # Python版本兼容，直接安装
        echo
        echo "[2/5] 跳过conda检查（Python版本兼容）"
        echo
        echo "[3/5] 直接安装依赖..."
        install_dependencies
    else
        # Python版本不兼容，尝试使用conda
        echo
        echo "[2/5] 检查conda可用性..."
        if command_exists conda; then
            print_success "conda可用，将创建虚拟环境"
            echo
            echo "[3/5] 设置conda环境..."
            setup_conda_env
            echo
            echo "[4/5] 安装依赖..."
            install_dependencies
        else
            print_error "conda不可用"
            echo
            echo "建议解决方案："
            echo "1. 安装Python 3.11或3.12"
            echo "2. 安装Anaconda/Miniconda"
            echo "3. 手动创建虚拟环境"
            echo
            read -p "是否继续尝试直接安装？(可能失败) (y/n): " choice
            if [[ $choice =~ ^[Yy]$ ]]; then
                echo
                echo "[3/5] 直接安装依赖..."
                install_dependencies
            else
                exit 1
            fi
        fi
    fi
    
    # 步骤5：测试安装
    echo
    echo "[5/5] 测试安装结果..."
    test_installation
    
    # 显示使用说明
    show_usage
}

# 运行主函数
main "$@"