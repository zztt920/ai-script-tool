"""认证服务 — 处理用户登录、注册和JWT令牌管理。"""

import os
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional, Dict

from adapter.user_repository import UserRepository
from api.errors import AppError


class AuthService:
    """认证服务类。"""
    
    SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-change-in-production")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    
    @staticmethod
    def hash_password(password: str) -> str:
        """哈希密码。"""
        salt = os.getenv("PASSWORD_SALT", "script-tool-salt")
        return hashlib.sha256((password + salt).encode()).hexdigest()
    
    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """验证密码。"""
        return AuthService.hash_password(password) == hashed_password
    
    @staticmethod
    def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        """创建访问令牌。"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now() + expires_delta
        else:
            expire = datetime.now() + timedelta(minutes=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def create_refresh_token(data: dict) -> str:
        """创建刷新令牌。"""
        expire = datetime.now() + timedelta(days=AuthService.REFRESH_TOKEN_EXPIRE_DAYS)
        data.update({"exp": expire, "token_type": "refresh"})
        encoded_jwt = jwt.encode(data, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM)
        return encoded_jwt
    
    @staticmethod
    def decode_token(token: str) -> Optional[Dict]:
        """解码令牌。"""
        try:
            payload = jwt.decode(token, AuthService.SECRET_KEY, algorithms=[AuthService.ALGORITHM])
            return payload
        except jwt.PyJWTError:
            return None
    
    @staticmethod
    def register(username: str, email: str, password: str, nickname: str = "") -> Dict:
        """用户注册。"""
        # 检查用户名是否已存在
        if UserRepository.exists_username(username):
            raise AppError(409, "conflict", "用户名已存在")
        
        # 检查邮箱是否已存在
        if UserRepository.exists_email(email):
            raise AppError(409, "conflict", "邮箱已被注册")
        
        # 创建用户
        password_hash = AuthService.hash_password(password)
        user_id = UserRepository.create(username, email, password_hash, nickname)
        
        return {"user_id": user_id, "username": username, "email": email}
    
    @staticmethod
    def login(username_or_email: str, password: str) -> Dict:
        """用户登录。"""
        # 尝试按用户名查找
        user = UserRepository.get_by_username(username_or_email)
        
        # 如果没找到，尝试按邮箱查找
        if not user:
            user = UserRepository.get_by_email(username_or_email)
        
        # 用户不存在
        if not user:
            raise AppError(401, "unauthorized", "用户名或密码错误")
        
        # 用户未激活
        if user["status"] != "active":
            raise AppError(403, "forbidden", "用户账号未激活")
        
        # 验证密码
        if not AuthService.verify_password(password, user["password_hash"]):
            raise AppError(401, "unauthorized", "用户名或密码错误")
        
        # 更新最后登录时间
        UserRepository.update(user["id"], last_login_at=datetime.now().isoformat())
        
        # 生成令牌
        access_token = AuthService.create_access_token({"sub": user["id"], "username": user["username"]})
        refresh_token = AuthService.create_refresh_token({"sub": user["id"]})
        
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "email": user["email"],
                "nickname": user.get("nickname", ""),
                "role": user["role"],
            },
        }
    
    @staticmethod
    def refresh_token(refresh_token: str) -> Dict:
        """刷新访问令牌。"""
        payload = AuthService.decode_token(refresh_token)
        
        if not payload or payload.get("token_type") != "refresh":
            raise AppError(401, "unauthorized", "无效的刷新令牌")
        
        user_id = payload.get("sub")
        user = UserRepository.get(user_id)
        
        if not user:
            raise AppError(401, "unauthorized", "用户不存在")
        
        access_token = AuthService.create_access_token({"sub": user["id"], "username": user["username"]})
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
        }
    
    @staticmethod
    def get_current_user(token: str) -> Optional[Dict]:
        """获取当前用户。"""
        payload = AuthService.decode_token(token)
        
        if not payload:
            return None
        
        user_id = payload.get("sub")
        return UserRepository.get(user_id)