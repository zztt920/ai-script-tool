import os
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")


def _has_static() -> bool:
    return os.path.isdir(os.path.join(STATIC_DIR, "css"))


def setup_ui(app: FastAPI):
    """挂载静态文件 + 添加 SPA 中间件。"""
    if not _has_static():
        return

    app.mount("/static", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    @app.get("/", response_class=HTMLResponse)
    async def index():
        path = os.path.join(STATIC_DIR, "index.html")
        with open(path, "r", encoding="utf-8") as f:
            return HTMLResponse(f.read())

    # 使用中间件处理 SPA fallback（在路由匹配之后）
    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        response = await call_next(request)
        # 如果路由返回 404，且不是 API/静态路径，返回 SPA index.html
        if response.status_code == 404:
            path = request.url.path
            if not path.startswith("/api/") and not path.startswith("/static/"):
                index_path = os.path.join(STATIC_DIR, "index.html")
                if os.path.exists(index_path):
                    with open(index_path, "r", encoding="utf-8") as f:
                        return HTMLResponse(f.read())
        return response
