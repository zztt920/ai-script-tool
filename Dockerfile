# ── 构建阶段 ──────────────────────────────────────────
FROM python:3.11-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libc6-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# ── 运行阶段 ──────────────────────────────────────────
FROM python:3.11-slim

# 创建非 root 用户
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# 从 builder 复制依赖
COPY --from=builder /root/.local /home/appuser/.local

# 复制应用代码
COPY . .

# 创建运行时目录并授权
RUN mkdir -p /app/output /app/data /app/checkpoints && \
    chown -R appuser:appuser /app

ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV SCRIPT_DB_PATH=/app/data/script_tool.db

# 切换到非 root 用户
USER appuser

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
