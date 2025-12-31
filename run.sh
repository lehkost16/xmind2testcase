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
    echo "  prod      - 启动生产服务器"
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
