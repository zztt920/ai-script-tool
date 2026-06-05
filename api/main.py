"""FastAPI 应用入口 — 全局异常处理 + CORS + 生命周期管理 + OpenAPI 文档。"""

import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.openapi.utils import get_openapi
from fastapi.openapi.docs import get_swagger_ui_html, get_redoc_html

from db.database import init_db
from api.routers import conversion, tasks, auth
from api.errors import AppError
from api.middleware import RequestLogMiddleware, RateLimitMiddleware
from adapter.logger import api_logger

# ── 生命周期 ──────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    api_logger.info("正在启动应用...")
    init_db()
    api_logger.info("数据库初始化完成")
    yield
    api_logger.info("应用已关闭")


# ── 中/英 OpenAPI Schema 工厂 ───────────────────────
def _build_openapi(title: str, desc: str) -> dict:
    """构建 OpenAPI schema（标题和描述按语言区分）。"""
    return get_openapi(
        title=title,
        version="1.0.0",
        description=desc,
        routes=app.routes,
    )


_OPENAPI_ZH = None
_OPENAPI_EN = None

_OPENAPI_DESC_ZH = """
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
| `/api/v1/tasks/batch-delete` | POST | 批量删除任务 |
| `/api/v1/tasks/stats` | GET | 仪表盘统计数据 |
| `/api/v1/tasks/search` | GET | 剧本全文搜索 |
| `/api/v1/tasks/styles` | GET | 风格模板列表 |
| `/api/v1/tasks/{task_id}/script` | GET | 下载 YAML 剧本 |
| `/api/v1/tasks/{task_id}/script.json` | GET | 导出 JSON 剧本 |
"""

_OPENAPI_DESC_EN = """
# AI Script Creation Tool API

RESTful API service that automatically converts novel chapters into structured YAML scripts.

## Features

- 📖 **Multi-format Support**: TXT, DOCX, PDF chapter files
- 🤖 **AI-Powered**: Automated script generation via DeepSeek API
- 🌐 **Multilingual**: Chinese/English output, localized YAML keys
- 📊 **Real-time Progress**: Task status polling with live updates
- 📱 **Responsive**: Mobile and desktop support

## Tech Stack

- FastAPI + Python 3.11+
- SQLite Database
- DeepSeek AI API
- YAML Data Format

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your DeepSeek API Key

# Start server
python -m uvicorn api.main:app --reload
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/convert` | POST | Submit novel conversion task |
| `/api/v1/tasks` | GET | List all tasks |
| `/api/v1/tasks/{task_id}` | GET | Get task details |
| `/api/v1/tasks/{task_id}` | DELETE | Delete a task |
| `/api/v1/tasks/batch-delete` | POST | Batch delete tasks |
| `/api/v1/tasks/stats` | GET | Dashboard statistics |
| `/api/v1/tasks/search` | GET | Full-text script search |
| `/api/v1/tasks/styles` | GET | Style template list |
| `/api/v1/tasks/{task_id}/script` | GET | Download YAML script |
| `/api/v1/tasks/{task_id}/script.json` | GET | Export JSON script |
"""


def openapi_zh():
    global _OPENAPI_ZH
    if _OPENAPI_ZH is None:
        _OPENAPI_ZH = _build_openapi("AI 剧本创作工具 API", _OPENAPI_DESC_ZH)
    return _OPENAPI_ZH


def openapi_en():
    global _OPENAPI_EN
    if _OPENAPI_EN is None:
        _OPENAPI_EN = _build_openapi("AI Script Creation Tool API", _OPENAPI_DESC_EN)
    return _OPENAPI_EN


# ── 中英双语言切换 Swagger UI HTML 模板 ──────────────
_LANG_SWITCHER_JS = """
<script>
(function() {
  var bar = document.createElement('div');
  bar.style.cssText = 'position:fixed;top:12px;right:20px;z-index:9999;display:flex;gap:6px;';
  var current = window.location.pathname.endsWith('/docs/en') ? 'en' : 'zh';
  var langs = [
    {code:'zh',label:'中文',href:'/docs',active:current==='zh'},
    {code:'en',label:'English',href:'/docs/en',active:current==='en'}
  ];
  langs.forEach(function(l) {
    var btn = document.createElement('a');
    btn.href = l.href;
    btn.textContent = l.label;
    var isActive = l.active;
    btn.style.cssText = 'padding:4px 12px;border-radius:4px;font-size:13px;font-family:-apple-system,sans-serif;text-decoration:none;' +
      (isActive
        ? 'background:#1b1b1b;color:#fff;font-weight:600;'
        : 'background:#f0f0f0;color:#555;');
    btn.onmouseenter = function() { if (!isActive) { btn.style.background='#e0e0e0'; } };
    btn.onmouseleave = function() { if (!isActive) { btn.style.background='#f0f0f0'; } };
    bar.appendChild(btn);
  });
  document.body.appendChild(bar);
})();
</script>
"""


def _swagger_html(openapi_url: str, title: str) -> str:
    """返回注入语言切换按钮的 Swagger UI HTML。"""
    html = get_swagger_ui_html(
        openapi_url=openapi_url,
        title=title,
        swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui-bundle.js",
        swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@5/swagger-ui.css",
    )
    return HTMLResponse(html.body.decode("utf-8").replace("</body>", _LANG_SWITCHER_JS + "</body>"))


# ── 应用实例 ──────────────────────────────────────
app = FastAPI(
    title="AI 剧本创作工具 API",
    version="1.0.0",
    description="将小说章节转换为结构化 YAML 剧本的 RESTful API",
    lifespan=lifespan,
    docs_url=None,     # 手动提供，支持中英双语
    redoc_url=None,
    openapi_url="/api/v1/openapi.json",
)

app.openapi = openapi_zh  # 默认中文


# ── 自定义 Swagger UI 页面（中英双语）─────────────────
@app.get("/docs", include_in_schema=False)
async def swagger_zh():
    return _swagger_html("/api/v1/openapi.json", "AI 剧本创作工具 API — 中文")


@app.get("/docs/en", include_in_schema=False)
async def swagger_en():
    return _swagger_html("/api/v1/openapi.en.json", "AI Script Creation Tool API — English")


@app.get("/redoc", include_in_schema=False)
async def redoc_zh():
    html = get_redoc_html(
        openapi_url="/api/v1/openapi.json",
        title="AI 剧本创作工具 API",
        redoc_js_url="https://cdn.jsdelivr.net/npm/redoc@next/bundles/redoc.standalone.js",
    )
    return HTMLResponse(html.body.decode("utf-8"))


@app.get("/api/v1/openapi.en.json", include_in_schema=False)
async def get_openapi_en():
    return JSONResponse(openapi_en())

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
    api_logger.warning("应用异常 [%s]: %s", exc.error, exc.message)
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.error, "message": exc.message, "code": exc.status_code},
    )


@app.exception_handler(ValueError)
async def value_error_handler(_request: Request, exc: ValueError):
    api_logger.warning("参数校验失败: %s", exc)
    return JSONResponse(
        status_code=422,
        content={"error": "validation_error", "message": str(exc), "code": 422},
    )


@app.exception_handler(FileNotFoundError)
async def not_found_handler(_request: Request, exc: FileNotFoundError):
    api_logger.warning("文件未找到: %s", exc)
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
