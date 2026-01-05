#!/usr/bin/env bash
# XMind2TestCase 快速启动脚本

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查依赖
check_dependencies() {
    print_info "检查依赖..."
    
    if ! command -v uv &> /dev/null; then
        print_error "uv 未安装，请先安装 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未安装"
        exit 1
    fi
    
    print_success "依赖检查通过"
}

# 初始化项目
init_project() {
    print_info "初始化项目..."
    
    # 创建必要的目录
    mkdir -p uploads logs backups
    
    # 同步依赖
    print_info "同步依赖包..."
    uv sync
    
    # 初始化数据库
    if [ ! -f "data.db3" ]; then
        print_info "初始化数据库..."
        sqlite3 data.db3 < schema.sql
        print_success "数据库已初始化"
    else
        print_warning "数据库已存在，跳过初始化"
    fi
    
    print_success "项目初始化完成"
}

# 启动开发服务器
start_dev() {
    print_info "启动开发服务器..."
    print_info "访问地址: http://localhost:8000"
    print_info "API 文档: http://localhost:8000/docs"
    print_info "按 Ctrl+C 停止服务器"
    echo ""
    uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
}

# 启动生产服务器
start_prod() {
    print_info "启动生产服务器..."
    uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
}

# 运行测试
run_tests() {
    print_info "运行测试..."
    uv run pytest tests/ -v
}

# 数据库管理
manage_db() {
    print_info "启动数据库管理工具..."
    uv run python manage_db.py
}

# PID 文件路径
PID_FILE="running.pid"
LOG_FILE="running.log"

# 后台启动
start_background() {
    if [ -f "$PID_FILE" ]; then
        if ps -p $(cat "$PID_FILE") > /dev/null; then
            print_error "服务已在运行中 (PID: $(cat $PID_FILE))"
            exit 1
        else
            rm "$PID_FILE"
        fi
    fi
    
    print_info "正在后台启动服务 (Production Mode)..."
    nohup uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    
    # Wait a moment to check if it crashed immediately
    sleep 2
    if ps -p $(cat "$PID_FILE") > /dev/null; then
        print_success "服务启动成功! (PID: $(cat $PID_FILE))"
        print_info "日志文件: $LOG_FILE"
    else
        print_error "服务启动失败，请查看日志: $LOG_FILE"
        cat "$LOG_FILE"
        rm "$PID_FILE"
        exit 1
    fi
}

# 停止服务
stop_server() {
    if [ ! -f "$PID_FILE" ]; then
        print_warning "未找到运行中的服务 (PID文件不存在)"
        return
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null; then
        print_info "正在停止服务 (PID: $PID)..."
        kill "$PID"
        
        # Wait for process to exit
        for i in {1..10}; do
            if ! ps -p "$PID" > /dev/null; then
                break
            fi
            sleep 0.5
        done
        
        if ps -p "$PID" > /dev/null; then
            print_warning "服务未响应，强制关闭..."
            kill -9 "$PID"
        fi
        
        rm "$PID_FILE"
        print_success "服务已停止"
    else
        print_warning "PID文件存在但进程未运行，清理PID文件"
        rm "$PID_FILE"
    fi
}

# 重启服务
restart_server() {
    stop_server
    sleep 1
    start_background
}

# 查看状态
check_status() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null; then
            print_success "服务正在运行 (PID: $PID)"
            print_info "监听端口: 8000"
            return
        else
            print_error "服务未运行 (PID文件存在但进程丢失)"
            exit 1
        fi
    else
        print_warning "服务未运行"
        exit 0
    fi
}

# 清理项目
clean_project() {
    print_warning "清理项目缓存和临时文件..."
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    find . -type f -name "*.pyo" -delete 2>/dev/null || true
    find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
    print_success "清理完成"
}

# 显示帮助信息
show_help() {
    echo ""
    echo "🛠️  XMind2TestCase 管理脚本"
    echo ""
    echo "用法: ./run.sh [命令]"
    echo ""
    echo "命令:"
    echo "  init      - 初始化项目（首次运行）"
    echo "  dev       - 启动开发服务器（默认）"
    echo "  prod      - 启动生产服务器（前台）"
    echo "  start     - 后台启动服务"
    echo "  stop      - 停止后台服务"
    echo "  restart   - 重启后台服务"
    echo "  status    - 查看服务状态"
    echo "  test      - 运行测试"
    echo "  db        - 数据库管理工具"
    echo "  clean     - 清理缓存文件"
    echo "  help      - 显示此帮助信息"
    echo ""
}

# 主逻辑
main() {
    check_dependencies
    
    case "${1:-dev}" in
        init)
            init_project
            ;;
        dev)
            start_dev
            ;;
        prod)
            start_prod
            ;;
        start)
            start_background
            ;;
        stop)
            stop_server
            ;;
        restart)
            restart_server
            ;;
        status)
            check_status
            ;;
        test)
            run_tests
            ;;
        db)
            manage_db
            ;;
        clean)
            clean_project
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知命令: $1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
