#!/bin/bash
# 一键重启前后端服务脚本
# 用法: ./scripts/restart.sh [backend|frontend|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PID_DIR="$PROJECT_DIR/.pids"
LOG_DIR="$PROJECT_DIR/logs"

# 创建目录
mkdir -p "$PID_DIR" "$LOG_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 停止服务
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止 $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            # 等待进程结束
            for i in $(seq 1 10); do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 0.5
            done
            # 强制杀死
            if kill -0 "$pid" 2>/dev/null; then
                log_warn "强制停止 $name..."
                kill -9 "$pid" 2>/dev/null || true
            fi
            log_info "$name 已停止"
        else
            log_warn "$name 进程不存在 (PID: $pid)"
        fi
        rm -f "$pid_file"
    else
        # 尝试通过端口查找进程
        local port=""
        if [ "$name" = "backend" ]; then port=8000; fi
        if [ "$name" = "frontend" ]; then port=3000; fi
        if [ -n "$port" ]; then
            local pids=$(lsof -ti:$port 2>/dev/null || true)
            if [ -n "$pids" ]; then
                log_info "通过端口 $port 停止 $name..."
                echo "$pids" | xargs kill 2>/dev/null || true
                log_info "$name 已停止"
            else
                log_warn "$name 未在运行"
            fi
        fi
    fi
}

# 启动后端
start_backend() {
    log_info "启动后端服务..."

    # 检查PostgreSQL
    if ! pg_isready -h localhost -p 5432 2>/dev/null; then
        log_warn "PostgreSQL未运行，尝试启动..."
        service postgresql start 2>/dev/null || {
            log_error "无法启动PostgreSQL，请手动启动"
            return 1
        }
        sleep 2
    fi

    # 激活虚拟环境
    if [ -d "$BACKEND_DIR/venv" ]; then
        source "$BACKEND_DIR/venv/bin/activate"
    fi

    # 设置环境变量
    export SQLITE_DB_PATH="$PROJECT_DIR/data/geomods_2.0.db"
    export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
    export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    export POSTGRES_DB="${POSTGRES_DB:-param_experiment}"
    export POSTGRES_USER="${POSTGRES_USER:-postgres}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
    export DEEPSEEK_API_KEY="${DEEPSEEK_API_KEY:-sk-0906d3c9ae584c96bf42c85e2ae87ef8}"

    cd "$BACKEND_DIR"
    nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload > "$LOG_DIR/backend.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_DIR/backend.pid"
    cd "$PROJECT_DIR"

    # 等待后端启动
    for i in $(seq 1 30); do
        if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
            log_info "后端服务已启动 (PID: $pid, http://localhost:8000)"
            return 0
        fi
        sleep 1
    done
    log_error "后端服务启动超时，请查看日志: $LOG_DIR/backend.log"
    return 1
}

# 启动前端
start_frontend() {
    log_info "启动前端服务..."

    cd "$FRONTEND_DIR"

    # 检查依赖
    if [ ! -d "node_modules" ]; then
        log_info "安装前端依赖..."
        npm install
    fi

    nohup npm run dev -- --host 0.0.0.0 --port 3000 > "$LOG_DIR/frontend.log" 2>&1 &
    local pid=$!
    echo "$pid" > "$PID_DIR/frontend.pid"
    cd "$PROJECT_DIR"

    # 等待前端启动
    for i in $(seq 1 30); do
        if curl -s http://localhost:3000 > /dev/null 2>&1; then
            log_info "前端服务已启动 (PID: $pid, http://localhost:3000)"
            return 0
        fi
        sleep 1
    done
    log_error "前端服务启动超时，请查看日志: $LOG_DIR/frontend.log"
    return 1
}

# 查看状态
show_status() {
    echo ""
    echo "=== 服务状态 ==="

    # 后端
    if curl -s http://localhost:8000/api/health > /dev/null 2>&1; then
        log_info "后端: 运行中 (http://localhost:8000)"
    else
        log_warn "后端: 未运行"
    fi

    # 前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_info "前端: 运行中 (http://localhost:3000)"
    else
        log_warn "前端: 未运行"
    fi

    echo ""
}

# 主逻辑
TARGET="${1:-all}"

case "$TARGET" in
    backend)
        stop_service "backend"
        start_backend
        ;;
    frontend)
        stop_service "frontend"
        start_frontend
        ;;
    all)
        stop_service "backend"
        stop_service "frontend"
        start_backend
        start_frontend
        ;;
    stop)
        stop_service "backend"
        stop_service "frontend"
        log_info "所有服务已停止"
        ;;
    status)
        show_status
        ;;
    *)
        echo "用法: $0 [backend|frontend|all|stop|status]"
        echo "  backend   - 重启后端服务"
        echo "  frontend  - 重启前端服务"
        echo "  all       - 重启所有服务（默认）"
        echo "  stop      - 停止所有服务"
        echo "  status    - 查看服务状态"
        exit 1
        ;;
esac

if [ "$TARGET" != "stop" ] && [ "$TARGET" != "status" ]; then
    show_status
fi
