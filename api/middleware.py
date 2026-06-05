"""API 中间件 — 请求日志记录与频率控制。"""

import time
import os
from collections import defaultdict
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from adapter.logger import get_logger

_log = get_logger("api.middleware")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """基于 IP 的请求频率限制中间件（滑动窗口）。"""

    def __init__(self, app, max_requests: int = 60, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = defaultdict(list)
        _log.info("限流中间件已启用: %d 请求 / %d 秒", max_requests, window_seconds)

    async def dispatch(self, request: Request, call_next):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()

        # 清理过期记录
        window_start = now - self.window_seconds
        self._clients[client_ip] = [
            ts for ts in self._clients[client_ip] if ts > window_start
        ]

        # 检查是否超限
        if len(self._clients[client_ip]) >= self.max_requests:
            _log.warning("IP %s 请求频率超限", client_ip)
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": f"请求过于频繁，请 {self.window_seconds} 秒后重试",
                    "code": 429,
                },
            )

        # 记录本次请求
        self._clients[client_ip].append(now)

        response = await call_next(request)
        return response


class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志记录中间件 — 记录每个请求的方法、路径和耗时。"""

    async def dispatch(self, request: Request, call_next):
        start = time.time()
        response = await call_next(request)
        elapsed = int((time.time() - start) * 1000)
        _log.info(
            "%s %s → %d (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            elapsed,
        )
        return response