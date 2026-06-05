"""API 错误定义 — 独立模块，避免循环导入。"""


class AppError(Exception):
    """业务异常基类 — 由全局异常处理器捕获并转为 JSON 响应。"""

    def __init__(self, status_code: int, error: str, message: str):
        self.status_code = status_code
        self.error = error
        self.message = message
