#!/bin/bash

# RDP Tool Docker 启动脚本
# 用于快速启动不同的服务组合

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    echo "RDP Tool Docker 部署脚本"
    echo ""
    echo "用法: $0 [选项] [服务模式]"
    echo ""
    echo "服务模式:"
    echo "  server-only     - 仅启动RDP服务端"
    echo "  full            - 启动完整服务 (服务端 + 代理)"
    echo "  with-clients    - 启动服务端和示例客户端"
    echo "  with-monitoring - 启动服务端和监控服务"
    echo "  all             - 启动所有服务"
    echo ""
    echo "选项:"
    echo "  -h, --help      - 显示此帮助信息"
    echo "  -d, --detach    - 后台运行"
    echo "  -b, --build     - 重新构建镜像"
    echo "  -c, --clean     - 清理并重新开始"
    echo "  --logs          - 显示日志"
    echo "  --stop          - 停止所有服务"
    echo "  --status        - 显示服务状态"
    echo ""
    echo "示例:"
    echo "  $0 server-only              # 仅启动服务端"
    echo "  $0 full -d                  # 后台启动完整服务"
    echo "  $0 with-clients --build     # 重新构建并启动客户端"
    echo "  $0 --stop                   # 停止所有服务"
}

# 检查Docker和docker-compose
check_dependencies() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker 未安装或不在PATH中"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "docker-compose 未安装或不在PATH中"
        exit 1
    fi
}

# 创建必要的目录
setup_directories() {
    print_info "创建必要的目录..."
    mkdir -p logs data monitoring
    
    # 设置权限
    chmod 755 logs data
    
    print_success "目录创建完成"
}

# 生成监控配置
generate_monitoring_config() {
    if [ ! -f "monitoring/prometheus.yml" ]; then
        print_info "生成Prometheus配置..."
        mkdir -p monitoring
        cat > monitoring/prometheus.yml << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'rdp-server'
    static_configs:
      - targets: ['rdp-server:8888']
    metrics_path: '/api/metrics'
    scrape_interval: 30s
    
  - job_name: 'rdp-proxy'
    static_configs:
      - targets: ['rdp-proxy:9090']
    metrics_path: '/metrics'
    scrape_interval: 30s
EOF
        print_success "Prometheus配置生成完成"
    fi
}

# 构建镜像
build_images() {
    print_info "构建Docker镜像..."
    docker-compose build
    print_success "镜像构建完成"
}

# 启动服务
start_services() {
    local mode=$1
    local detach_flag=$2
    
    setup_directories
    
    case $mode in
        "server-only")
            print_info "启动RDP服务端..."
            docker-compose up $detach_flag rdp-server
            ;;
        "full")
            print_info "启动完整服务 (服务端 + 代理)..."
            docker-compose --profile proxy up $detach_flag rdp-server rdp-proxy
            ;;
        "with-clients")
            print_info "启动服务端和示例客户端..."
            docker-compose --profile target-client --profile controller-client up $detach_flag
            ;;
        "with-monitoring")
            generate_monitoring_config
            print_info "启动服务端和监控服务..."
            docker-compose --profile monitoring up $detach_flag rdp-server rdp-monitor
            ;;
        "all")
            generate_monitoring_config
            print_info "启动所有服务..."
            docker-compose --profile proxy --profile target-client --profile controller-client --profile cache --profile monitoring up $detach_flag
            ;;
        *)
            print_error "未知的服务模式: $mode"
            show_help
            exit 1
            ;;
    esac
}

# 停止服务
stop_services() {
    print_info "停止所有服务..."
    docker-compose down
    print_success "所有服务已停止"
}

# 显示服务状态
show_status() {
    print_info "服务状态:"
    docker-compose ps
    
    echo ""
    print_info "服务健康检查:"
    docker-compose exec rdp-server curl -f http://localhost:8888/api/status 2>/dev/null && print_success "RDP服务端: 健康" || print_warning "RDP服务端: 不健康"
}

# 显示日志
show_logs() {
    print_info "显示服务日志..."
    docker-compose logs -f
}

# 清理环境
clean_environment() {
    print_warning "清理Docker环境..."
    docker-compose down -v --remove-orphans
    docker system prune -f
    print_success "环境清理完成"
}

# 主函数
main() {
    check_dependencies
    
    local mode=""
    local detach_flag=""
    local build_flag=false
    local clean_flag=false
    
    # 解析参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -d|--detach)
                detach_flag="-d"
                shift
                ;;
            -b|--build)
                build_flag=true
                shift
                ;;
            -c|--clean)
                clean_flag=true
                shift
                ;;
            --logs)
                show_logs
                exit 0
                ;;
            --stop)
                stop_services
                exit 0
                ;;
            --status)
                show_status
                exit 0
                ;;
            server-only|full|with-clients|with-monitoring|all)
                mode=$1
                shift
                ;;
            *)
                print_error "未知参数: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # 如果没有指定模式，默认为server-only
    if [ -z "$mode" ]; then
        mode="server-only"
    fi
    
    # 执行清理
    if [ "$clean_flag" = true ]; then
        clean_environment
    fi
    
    # 构建镜像
    if [ "$build_flag" = true ]; then
        build_images
    fi
    
    # 启动服务
    start_services "$mode" "$detach_flag"
    
    if [ -n "$detach_flag" ]; then
        print_success "服务已在后台启动"
        print_info "使用 '$0 --status' 查看状态"
        print_info "使用 '$0 --logs' 查看日志"
        print_info "使用 '$0 --stop' 停止服务"
    fi
}

# 运行主函数
main "$@"