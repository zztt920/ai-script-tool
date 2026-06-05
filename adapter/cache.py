"""Redis 缓存适配器 — 提供剧本数据缓存和任务状态缓存。"""

import os
import json
from typing import Any, Optional
from adapter.logger import get_logger

_log = get_logger("adapter.cache")


try:
    import redis
    _HAS_REDIS = True
except ImportError:
    _HAS_REDIS = False


class CacheAdapter:
    """Redis 缓存适配器，提供统一的缓存接口。"""
    
    def __init__(self):
        self._client = None
        self._enabled = os.getenv("REDIS_ENABLED", "false").lower() == "true" and _HAS_REDIS
        if self._enabled:
            _log.info("Redis 缓存已启用")
        else:
            _log.info("Redis 缓存未启用（REDIS_ENABLED=false 或 redis 未安装）")
    
    def _get_client(self):
        if not self._client and self._enabled:
            try:
                self._client = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", "6379")),
                    db=int(os.getenv("REDIS_DB", "0")),
                    password=os.getenv("REDIS_PASSWORD", None),
                    decode_responses=True,
                )
                # 测试连接
                self._client.ping()
            except Exception:
                self._client = None
                self._enabled = False
        return self._client
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值。"""
        if not self._enabled:
            return None
        
        client = self._get_client()
        if not client:
            return None
        
        try:
            value = client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception:
            return None
    
    def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """设置缓存值。"""
        if not self._enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.set(key, json.dumps(value), ex=expire_seconds)
            return True
        except Exception:
            return False
    
    def delete(self, key: str) -> bool:
        """删除缓存。"""
        if not self._enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.delete(key)
            return True
        except Exception:
            return False
    
    def exists(self, key: str) -> bool:
        """检查缓存是否存在。"""
        if not self._enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            return client.exists(key) > 0
        except Exception:
            return False
    
    def flush(self) -> bool:
        """清空所有缓存。"""
        if not self._enabled:
            return False
        
        client = self._get_client()
        if not client:
            return False
        
        try:
            client.flushdb()
            return True
        except Exception:
            return False
    
    # ── 业务方法 ──────────────────────────────────────
    
    def get_task_progress(self, task_id: str) -> Optional[dict]:
        """获取任务进度缓存。"""
        return self.get(f"task:progress:{task_id}")
    
    def set_task_progress(self, task_id: str, progress: dict) -> bool:
        """设置任务进度缓存（5分钟过期）。"""
        return self.set(f"task:progress:{task_id}", progress, expire_seconds=300)
    
    def get_script_content(self, task_id: str) -> Optional[str]:
        """获取剧本内容缓存。"""
        return self.get(f"script:content:{task_id}")
    
    def set_script_content(self, task_id: str, content: str) -> bool:
        """设置剧本内容缓存（24小时过期）。"""
        return self.set(f"script:content:{task_id}", content, expire_seconds=86400)
    
    def invalidate_script(self, task_id: str) -> bool:
        """使剧本缓存失效。"""
        return self.delete(f"script:content:{task_id}")
    
    def get_analysis_result(self, task_id: str) -> Optional[dict]:
        """获取分析结果缓存。"""
        return self.get(f"analysis:{task_id}")
    
    def set_analysis_result(self, task_id: str, result: dict) -> bool:
        """设置分析结果缓存（1小时过期）。"""
        return self.set(f"analysis:{task_id}", result, expire_seconds=3600)


# 单例实例
cache = CacheAdapter()