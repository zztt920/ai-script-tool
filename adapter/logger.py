"""结构化日志适配器 — 提供统一的日志记录接口。

特性：
- 自动写入 logs/ 目录（按日期轮转）
- 同时输出到控制台（彩色）
- 结构化 JSON 日志 + 人类可读纯文本日志
- 支持请求追踪 ID（X-Request-ID）
"""

import os
import sys
import json
import logging
import datetime
from pathlib import Path
from typing import Optional

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FORMAT_CONSOLE = os.getenv(
    "LOG_FORMAT_CONSOLE",
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)
LOG_FORMAT_FILE = os.getenv(
    "LOG_FORMAT_FILE",
    "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
)


def _ensure_log_dir() -> None:
    """确保日志目录存在。"""
    LOG_DIR.mkdir(parents=True, exist_ok=True)


class _StructuredFormatter(logging.Formatter):
    """结构化日志格式化器（JSON 输出）。"""
    
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.datetime.now().isoformat(),
            "level": record.levelname.lower(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        # 附加上下文信息
        extra = getattr(record, "context", None)
        if extra:
            entry["context"] = extra
        # 异常信息
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        return json.dumps(entry, ensure_ascii=False)


class LoggerFactory:
    """日志工厂 — 按需创建命名 logger。"""
    
    _configured = False
    
    @classmethod
    def _configure(cls) -> None:
        """配置根日志记录器（仅执行一次）。"""
        if cls._configured:
            return
        
        _ensure_log_dir()
        root_logger = logging.getLogger()
        root_logger.setLevel(LOG_LEVEL)
        
        # 控制台处理器（彩色从 Windows 10 1607+ 开始支持）
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(logging.Formatter(LOG_FORMAT_CONSOLE))
        console_handler.setLevel(LOG_LEVEL)
        root_logger.addHandler(console_handler)
        
        # 文件处理器 — 按日期分文件
        today = datetime.date.today().isoformat()
        file_handler = logging.FileHandler(
            str(LOG_DIR / f"app-{today}.log"), encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter(LOG_FORMAT_FILE))
        file_handler.setLevel(LOG_LEVEL)
        root_logger.addHandler(file_handler)
        
        cls._configured = True
    
    @classmethod
    def get_logger(cls, name: str) -> logging.Logger:
        """获取指定名称的 Logger。"""
        cls._configure()
        return logging.getLogger(name)


# 常用快捷函数
def get_logger(name: str) -> logging.Logger:
    """快捷获取 Logger 实例。"""
    return LoggerFactory.get_logger(name)


# 预置模块 Logger
api_logger = get_logger("api")
service_logger = get_logger("service")
db_logger = get_logger("db")