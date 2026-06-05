"""FastAPI 应用入口 — 全局异常处理 + CORS + 生命周期管理 + OpenAPI 文档。"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from db.database import init_db
from api.routers import conversion, tasks, auth
from api.errors import AppError
from api.middleware import RequestLogMiddleware, RateLimitMiddleware

# ── 生命周期 ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


# ── 自定义 OpenAPI 配置 ──────────────────────────────
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="AI 剧本创作工具 API",
        version="1.0.0",
        description="""
# AI 剧本创作工具 API

将小说章节自动转换为结构化 YAML 剧本的 RESTful API 服务。

## 功能特性

- 📖 **多格式支持**：支持 TXT、DOCX、PDF 格式的小说章节
- 🤖 **AI 驱动**：基于 DeepSeek API 自动生成剧本
- 🌐 **多语言**：支持中文/英文输出，YAML Key 全中文化
- 📊 **实时进度**：任务进度实时更新，状态轮询支持
- 📱 **响应式**：支持移动端和桌面端

## 技术栈

- FastAPI + Python 3.11+
- SQLite 数据库
- DeepSeek AI API
- YAML 数据格式

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 设置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 DeepSeek API Key

# 启动服务
python -m uvicorn api.main:app --reload
```

## API 端点

| 端点 | 方法 | 描述 |
|------|------|------|
| `/api/v1/convert` | POST | 提交小说转换任务 |
| `/api/v1/tasks` | GET | 获取任务列表 |
| `/api/v1/tasks/{task_id}` | GET | 获取任务详情 |
| `/api/v1/tasks/{task_id}` | DELETE | 删除任务 |
| `/api/v1/tasks/{task_id}/script` | GET | 获取剧本内容 |
| `/api/v1/tasks/{task_id}/download` | GET | 下载剧本文件 |

## 访问文档

- Swagger UI: `/docs`
- ReDoc: `/redoc`
        """,
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


# ── 应用实例 ──────────────────────────────────────
app = FastAPI(
    title="AI 剧本创作工具 API",
    version="1.0.0",
    description="将小说章节转换为结构化 YAML 剧本的 RESTful API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.openapi = custom_openapi

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 请求限流（60 次/分钟）
app.add_middleware(
    RateLimitMiddleware,
    max_requests=int(os.getenv("RATE_LIMIT_MAX", "60")),
    window_seconds=int(os.getenv("RATE_LIMIT_WINDOW", "60")),
)

# 请求日志记录
app.add_middleware(RequestLogMiddleware)

app.include_router(conversion.router, prefix="/api/v1")
app.include_router(tasks.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")

# ── Web UI ───────────────────────────────────────
from api.ui import setup_ui
setup_ui(app)

# ── 全局异常处理器 ────────────────────────────────
@app.exception_handler(AppError)
async def app_error_handler(_request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message, "code": exc.status_code},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": str(exc), "code": 422},
    )


@app.exception_handler(FileNotFoundError)
async def not_found_handler(_request: Request, exc: FileNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"error": "not_found", "message": str(exc), "code": 404},
    )


# ── 健康检查 ──────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("api.main:app", host=host, port=port, reload=True)
