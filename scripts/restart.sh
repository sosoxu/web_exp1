#!/bin/bash
# 一键重启前后端服务脚本
# 用法: ./scripts/restart.sh [backend|frontend|all|stop|status|check]

set -e

# 环境检查中某些命令可能返回非零，不触发set -e
set +e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
PID_DIR="$PROJECT_DIR/.pids"
LOG_DIR="$PROJECT_DIR/logs"
ENV_FILE="$BACKEND_DIR/.env"

# 创建目录
mkdir -p "$PID_DIR" "$LOG_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_check() { echo -e "${BLUE}[CHECK]${NC} $1"; }

# ============================================================
# 环境检查函数
# ============================================================

CHECK_PASS=0
CHECK_FAIL=0
CHECK_WARN=0

check_item() {
    local name=$1
    local status=$2  # pass/fail/warn
    local detail=$3

    case "$status" in
        pass)
            echo -e "  ${GREEN}✓${NC} $name: $detail"
            CHECK_PASS=$((CHECK_PASS + 1))
            ;;
        fail)
            echo -e "  ${RED}✗${NC} $name: $detail"
            CHECK_FAIL=$((CHECK_FAIL + 1))
            ;;
        warn)
            echo -e "  ${YELLOW}!${NC} $name: $detail"
            CHECK_WARN=$((CHECK_WARN + 1))
            ;;
    esac
}

# 检查命令是否存在
check_command() {
    local cmd=$1
    if command -v "$cmd" &>/dev/null; then
        local path=$(command -v "$cmd")
        check_item "命令 $cmd" "pass" "已安装 ($path)"
        return 0
    else
        check_item "命令 $cmd" "fail" "未安装，请先安装 $cmd"
        return 1
    fi
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local name=$2
    local pids=$(lsof -ti:$port 2>/dev/null || true)
    if [ -n "$pids" ]; then
        check_item "端口 $port ($name)" "warn" "已被占用 (PID: $(echo $pids | tr '\n' ' '))"
        return 1
    else
        check_item "端口 $port ($name)" "pass" "空闲"
        return 0
    fi
}

# 检查服务是否已运行
check_service_running() {
    local name=$1
    local url=$2
    local response=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo "000")
    if [ "$response" != "000" ]; then
        check_item "服务 $name" "warn" "已在运行 (HTTP $response, $url)"
        return 1
    else
        check_item "服务 $name" "pass" "未运行，可以启动"
        return 0
    fi
}

# 检查PostgreSQL
check_postgresql() {
    log_check "检查 PostgreSQL..."

    # 检查 pg_isready 命令
    if ! command -v pg_isready &>/dev/null; then
        check_item "pg_isready" "fail" "未找到，PostgreSQL 可能未安装"
        return 1
    fi

    # 检查 PostgreSQL 是否运行
    if pg_isready -h localhost -p 5432 &>/dev/null; then
        check_item "PostgreSQL 服务" "pass" "运行中 (localhost:5432)"
    else
        check_item "PostgreSQL 服务" "fail" "未运行"
        # 尝试启动
        log_info "尝试启动 PostgreSQL..."
        if pg_ctlcluster 16 main start 2>/dev/null; then
            sleep 2
            if pg_isready -h localhost -p 5432 &>/dev/null; then
                check_item "PostgreSQL 启动" "pass" "启动成功"
            else
                check_item "PostgreSQL 启动" "fail" "启动失败"
                return 1
            fi
        else
            check_item "PostgreSQL 启动" "fail" "无法自动启动，请手动运行: pg_ctlcluster 16 main start"
            return 1
        fi
    fi

    # 检查数据库是否存在
    local db_exists=$(su - postgres -c "psql -lqt" 2>/dev/null | grep -c "param_experiment" || echo "0")
    if [ "$db_exists" -ge 1 ]; then
        check_item "数据库 param_experiment" "pass" "已存在"
    else
        check_item "数据库 param_experiment" "warn" "不存在，后端首次启动时会自动创建"
    fi

    return 0
}

# 检查SQLite数据库
check_sqlite() {
    log_check "检查 SQLite 数据库..."

    local db_path="$PROJECT_DIR/data/geomods_2.0.db"
    if [ -f "$db_path" ]; then
        local size=$(du -h "$db_path" | cut -f1)
        check_item "SQLite 数据库" "pass" "存在 ($size, $db_path)"
    else
        check_item "SQLite 数据库" "fail" "不存在 ($db_path)"
        return 1
    fi
}

# 检查LLM配置
check_llm() {
    log_check "检查 LLM 配置..."

    local api_key=""

    # 从环境变量读取
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        api_key="$DEEPSEEK_API_KEY"
        check_item "DEEPSEEK_API_KEY (环境变量)" "pass" "已设置 (${api_key:0:8}...)"
    # 从 .env 文件读取
    elif [ -f "$ENV_FILE" ]; then
        api_key=$(grep "^DEEPSEEK_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- || true)
        if [ -n "$api_key" ]; then
            check_item "DEEPSEEK_API_KEY (.env)" "pass" "已设置 (${api_key:0:8}...)"
        else
            check_item "DEEPSEEK_API_KEY (.env)" "fail" "未设置，LLM解析功能不可用"
        fi
    else
        check_item "DEEPSEEK_API_KEY" "fail" "未设置，LLM解析功能不可用。请在 $ENV_FILE 中设置 DEEPSEEK_API_KEY"
    fi

    # 测试LLM连通性（仅在后端运行时）
    if curl -s http://localhost:8000/api/health &>/dev/null; then
        local test_result=$(curl -s -X POST http://localhost:8000/api/llm/parse-params \
            -H "Content-Type: application/json" \
            -d '{"params":[{"module_name":"test","param_name":"p","type_val":"SINGLE","vtype":"Int"}],"description":"取1"}' 2>/dev/null || echo "")
        if echo "$test_result" | grep -q "parsed"; then
            check_item "LLM 连通性" "pass" "DeepSeek API 可正常调用"
        elif echo "$test_result" | grep -q "未配置"; then
            check_item "LLM 连通性" "fail" "API Key 未配置"
        elif echo "$test_result" | grep -q "无效"; then
            check_item "LLM 连通性" "fail" "API Key 无效"
        elif [ -n "$test_result" ]; then
            check_item "LLM 连通性" "warn" "返回异常: $(echo $test_result | head -c 100)"
        else
            check_item "LLM 连通性" "warn" "无法测试（后端刚启动，可能尚未就绪）"
        fi
    else
        check_item "LLM 连通性" "warn" "后端未运行，跳过连通性测试"
    fi
}

# 检查Python虚拟环境
check_python() {
    log_check "检查 Python 环境..."

    if [ -d "$BACKEND_DIR/venv" ]; then
        local py_version=$("$BACKEND_DIR/venv/bin/python" --version 2>&1 || echo "未知")
        check_item "Python 虚拟环境" "pass" "$py_version ($BACKEND_DIR/venv)"

        # 检查关键依赖
        local missing_deps=""
        for pkg in fastapi uvicorn sqlalchemy asyncpg httpx; do
            if ! "$BACKEND_DIR/venv/bin/python" -c "import $pkg" 2>/dev/null; then
                missing_deps="$missing_deps $pkg"
            fi
        done
        if [ -z "$missing_deps" ]; then
            check_item "Python 依赖" "pass" "关键包已安装"
        else
            check_item "Python 依赖" "fail" "缺少:$missing_deps，请运行: pip install -r requirements.txt"
        fi
    else
        check_item "Python 虚拟环境" "fail" "不存在，请运行: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    fi
}

# 检查Node.js环境
check_node() {
    log_check "检查 Node.js 环境..."

    if command -v node &>/dev/null; then
        local node_version=$(node --version 2>&1)
        check_item "Node.js" "pass" "$node_version"
    else
        check_item "Node.js" "fail" "未安装"
    fi

    if [ -d "$FRONTEND_DIR/node_modules" ]; then
        check_item "前端依赖" "pass" "已安装 (node_modules)"
    else
        check_item "前端依赖" "warn" "未安装，启动时会自动运行 npm install"
    fi
}

# 检查配置文件
check_config() {
    log_check "检查配置文件..."

    if [ -f "$ENV_FILE" ]; then
        check_item ".env 文件" "pass" "存在 ($ENV_FILE)"
    else
        check_item ".env 文件" "warn" "不存在，将使用默认配置"
    fi

    if [ -f "$PROJECT_DIR/data/geomods_2.0.db" ]; then
        check_item "SQLite 数据文件" "pass" "存在"
    else
        check_item "SQLite 数据文件" "fail" "不存在 ($PROJECT_DIR/data/geomods_2.0.db)"
    fi
}

# 综合环境检查
run_all_checks() {
    echo ""
    echo "========================================"
    echo "       环境检查"
    echo "========================================"
    echo ""

    CHECK_PASS=0
    CHECK_FAIL=0
    CHECK_WARN=0

    # 1. 基础命令检查
    log_check "检查基础命令..."
    check_command "python3"
    check_command "node"
    check_command "curl"
    check_command "lsof"
    echo ""

    # 2. Python 环境
    check_python
    echo ""

    # 3. Node.js 环境
    check_node
    echo ""

    # 4. 数据库检查
    check_sqlite
    check_postgresql
    echo ""

    # 5. 配置文件
    check_config
    echo ""

    # 6. LLM 配置
    check_llm
    echo ""

    # 7. 端口和服务状态
    log_check "检查端口和服务状态..."
    check_port 8000 "后端"
    check_port 3000 "前端"
    check_service_running "后端" "http://localhost:8000/api/health"
    check_service_running "前端" "http://localhost:3000"
    echo ""

    # 汇总
    echo "========================================"
    echo -e "  检查结果: ${GREEN}通过 $CHECK_PASS${NC}  ${YELLOW}警告 $CHECK_WARN${NC}  ${RED}失败 $CHECK_FAIL${NC}"
    echo "========================================"
    echo ""

    if [ $CHECK_FAIL -gt 0 ]; then
        log_error "存在 $CHECK_FAIL 项检查失败，请修复后再启动服务"
        return 1
    elif [ $CHECK_WARN -gt 0 ]; then
        log_warn "存在 $CHECK_WARN 项警告，服务可能部分功能不可用"
        return 0
    else
        log_info "所有检查通过，可以启动服务"
        return 0
    fi
}

# ============================================================
# 服务管理函数
# ============================================================

# 停止服务
stop_service() {
    local name=$1
    local pid_file="$PID_DIR/${name}.pid"

    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            log_info "停止 $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            for i in $(seq 1 10); do
                if ! kill -0 "$pid" 2>/dev/null; then
                    break
                fi
                sleep 0.5
            done
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
        pg_ctlcluster 16 main start 2>/dev/null || service postgresql start 2>/dev/null || {
            log_error "无法启动PostgreSQL，请手动启动"
            return 1
        }
        sleep 2
        if ! pg_isready -h localhost -p 5432 2>/dev/null; then
            log_error "PostgreSQL启动失败"
            return 1
        fi
    fi

    # 激活虚拟环境
    if [ -d "$BACKEND_DIR/venv" ]; then
        source "$BACKEND_DIR/venv/bin/activate"
    else
        log_error "Python虚拟环境不存在，请先运行: cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
        return 1
    fi

    # 设置环境变量
    export SQLITE_DB_PATH="$PROJECT_DIR/data/geomods_2.0.db"
    export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
    export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
    export POSTGRES_DB="${POSTGRES_DB:-param_experiment}"
    export POSTGRES_USER="${POSTGRES_USER:-postgres}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"

    # 从.env读取DEEPSEEK_API_KEY
    if [ -z "$DEEPSEEK_API_KEY" ] && [ -f "$ENV_FILE" ]; then
        export DEEPSEEK_API_KEY=$(grep "^DEEPSEEK_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- || true)
    fi

    if [ -z "$DEEPSEEK_API_KEY" ]; then
        log_warn "DEEPSEEK_API_KEY 未设置，LLM解析功能不可用"
    else
        log_info "DEEPSEEK_API_KEY 已设置 (${DEEPSEEK_API_KEY:0:8}...)"
    fi

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

    nohup npx vite --host 0.0.0.0 --port 3000 > "$LOG_DIR/frontend.log" 2>&1 &
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
        local health=$(curl -s http://localhost:8000/api/health 2>/dev/null)
        log_info "后端: 运行中 (http://localhost:8000) - $health"
    else
        log_warn "后端: 未运行"
    fi

    # 前端
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        log_info "前端: 运行中 (http://localhost:3000)"
    else
        log_warn "前端: 未运行"
    fi

    # PostgreSQL
    if command -v pg_isready &>/dev/null && pg_isready -h localhost -p 5432 &>/dev/null; then
        log_info "PostgreSQL: 运行中 (localhost:5432)"
    else
        log_warn "PostgreSQL: 未运行"
    fi

    # LLM
    if [ -n "$DEEPSEEK_API_KEY" ]; then
        log_info "DEEPSEEK_API_KEY: 已设置 (${DEEPSEEK_API_KEY:0:8}...)"
    elif [ -f "$ENV_FILE" ]; then
        local key=$(grep "^DEEPSEEK_API_KEY=" "$ENV_FILE" 2>/dev/null | cut -d'=' -f2- || true)
        if [ -n "$key" ]; then
            log_info "DEEPSEEK_API_KEY: 已配置 (.env, ${key:0:8}...)"
        else
            log_warn "DEEPSEEK_API_KEY: 未配置，LLM功能不可用"
        fi
    else
        log_warn "DEEPSEEK_API_KEY: 未配置，LLM功能不可用"
    fi

    echo ""
}

# ============================================================
# 主逻辑
# ============================================================

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
    check)
        run_all_checks
        ;;
    *)
        echo "用法: $0 [backend|frontend|all|stop|status|check]"
        echo "  backend   - 重启后端服务"
        echo "  frontend  - 重启前端服务"
        echo "  all       - 重启所有服务（默认）"
        echo "  stop      - 停止所有服务"
        echo "  status    - 查看服务状态"
        echo "  check     - 环境检查（数据库、LLM、依赖等）"
        exit 1
        ;;
esac

if [ "$TARGET" != "stop" ] && [ "$TARGET" != "status" ] && [ "$TARGET" != "check" ]; then
    show_status
fi
