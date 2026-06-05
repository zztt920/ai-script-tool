#!/usr/bin/env bash
# AI 剧本创作工具 — 一键启动脚本
set -e

echo "========================================"
echo "  AI 剧本创作工具 — 环境初始化"
echo "========================================"

# 1. 创建虚拟环境（如不存在）
if [ ! -d "venv" ]; then
    echo "[1/3] 创建 Python 虚拟环境..."
    python3 -m venv venv
fi

# 2. 安装依赖
echo "[2/3] 安装依赖..."
source venv/bin/activate 2>/dev/null || source venv/Scripts/activate 2>/dev/null
pip install -q -r requirements.txt

# 3. 检查环境变量
if [ -f ".env" ]; then
    echo "[3/3] 加载 .env 配置..."
    export $(grep -v '^#' .env | xargs)
else
    echo "[3/3] 未找到 .env，使用默认配置。请确保 OPENAI_API_KEY 已设置。"
fi

echo ""
echo "启动方式:"
echo "  Web API:  python -m api.main"
echo "  CLI:      python -m cli.main -i ./chapters -o ./output/script.yaml --dry-run"
echo "  校验器:   python script_validator.py ./output/script.yaml"
echo ""
