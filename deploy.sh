#!/usr/bin/env bash
# ── AI 剧本创作工具 — 一键生产部署 ────────────────────
# 用法: bash deploy.sh [up|down|logs|status]
set -e

COMPOSE_FILE="docker-compose.prod.yml"
PROJECT_NAME="script-tool"

# ── 函数 ────────────────────────────────────────
check_env() {
    if [ ! -f ".env" ]; then
        echo "[!] 未找到 .env 文件，从 .env.example 复制..."
        cp .env.example .env
        echo "[!] 请编辑 .env 填入 OPENAI_API_KEY 后重新运行"
        exit 1
    fi
    if grep -q "sk-your-key-here" .env; then
        echo "[!] 检测到默认 API Key，请编辑 .env 填入真实 Key"
        exit 1
    fi
}

gen_ssl() {
    if [ ! -f "nginx/ssl/cert.pem" ]; then
        echo "[1/4] 生成自签名 SSL 证书..."
        bash nginx/ssl/generate.sh
    else
        echo "[1/4] SSL 证书已存在，跳过"
    fi
}

check_prereqs() {
    echo "[*] 检查前置依赖..."
    if ! command -v docker &>/dev/null; then
        echo "[!] Docker 未安装，请先安装 Docker"
        exit 1
    fi
    if ! command -v openssl &>/dev/null; then
        echo "[!] OpenSSL 未安装，请先安装 OpenSSL"
        exit 1
    fi
    echo "    Docker $(docker --version | awk '{print $3}' | tr -d ',')"
    echo "    Docker Compose $(docker compose version 2>/dev/null | awk '{print $NF}')"
}

up() {
    check_prereqs
    check_env
    gen_ssl
    echo "[2/4] 构建镜像..."
    docker compose -f "$COMPOSE_FILE" build --no-cache
    echo "[3/4] 启动服务..."
    docker compose -f "$COMPOSE_FILE" up -d
    echo "[4/4] 等待健康检查..."
    sleep 5
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "========================================"
    echo "  部署完成!"
    echo "========================================"
    echo "  HTTPS:  https://localhost"
    echo "  API文档: https://localhost/docs"
    echo "  Health:  https://localhost/health"
    echo ""
    echo "  查看日志:   bash deploy.sh logs"
    echo "  停止服务:   bash deploy.sh down"
    echo "  查看状态:   bash deploy.sh status"
    echo "========================================"
}

down() {
    echo "停止服务..."
    docker compose -f "$COMPOSE_FILE" down
    echo "已停止"
}

logs() {
    docker compose -f "$COMPOSE_FILE" logs -f --tail=100
}

status() {
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
    echo "--- API 健康检查 ---"
    curl -sk https://localhost/health 2>/dev/null || echo "(API 未就绪)"
}

# ── 主入口 ──────────────────────────────────────
case "${1:-up}" in
    up)     up ;;
    down)   down ;;
    logs)   logs ;;
    status) status ;;
    *)
        echo "用法: bash deploy.sh [up|down|logs|status]"
        exit 1
        ;;
esac
