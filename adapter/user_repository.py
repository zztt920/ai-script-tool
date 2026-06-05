"""用户数据访问层。"""

import uuid
from typing import Optional, Dict
from db.database import get_connection


class UserRepository:
    """用户数据访问接口。"""
    
    @staticmethod
    def create(username: str, email: str, password_hash: str, nickname: str = "") -> str:
        """创建用户。"""
        user_id = str(uuid.uuid4())
        with get_connection() as conn:
            conn.execute(
                """
                INSERT INTO user (id, username, email, password_hash, nickname, role, status)
                VALUES (?, ?, ?, ?, ?, 'user', 'active')
                """,
                (user_id, username, email, password_hash, nickname),
            )
        return user_id
    
    @staticmethod
    def get(user_id: str) -> Optional[Dict]:
        """根据ID获取用户。"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user WHERE id = ?", (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_username(username: str) -> Optional[Dict]:
        """根据用户名获取用户。"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user WHERE username = ?", (username,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def get_by_email(email: str) -> Optional[Dict]:
        """根据邮箱获取用户。"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT * FROM user WHERE email = ?", (email,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    @staticmethod
    def update(user_id: str, **kwargs) -> bool:
        """更新用户信息。"""
        if not kwargs:
            return False
        
        fields = []
        values = []
        for key, value in kwargs.items():
            if key in ("username", "email", "password_hash", "nickname", "avatar_url", "role", "status", "last_login_at"):
                fields.append(f"{key} = ?")
                values.append(value)
        
        if not fields:
            return False
        
        values.append(user_id)
        
        with get_connection() as conn:
            conn.execute(
                f"UPDATE user SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
        return True
    
    @staticmethod
    def delete(user_id: str) -> bool:
        """删除用户。"""
        with get_connection() as conn:
            conn.execute("DELETE FROM user WHERE id = ?", (user_id,))
        return True
    
    @staticmethod
    def exists_username(username: str) -> bool:
        """检查用户名是否存在。"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM user WHERE username = ?", (username,))
            return cursor.fetchone() is not None
    
    @staticmethod
    def exists_email(email: str) -> bool:
        """检查邮箱是否存在。"""
        with get_connection() as conn:
            cursor = conn.execute("SELECT 1 FROM user WHERE email = ?", (email,))
            return cursor.fetchone() is not None