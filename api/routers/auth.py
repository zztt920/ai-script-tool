"""认证 API Router。

端点一览：
- POST /auth/register    用户注册
- POST /auth/login       用户登录
- POST /auth/refresh     刷新令牌
- GET  /auth/me          获取当前用户信息
"""

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from api.schemas import (
    RegisterRequest, RegisterResponse,
    LoginRequest, LoginResponse,
    RefreshRequest, RefreshResponse,
    UserResponse,
)
from service.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@router.post("/register", response_model=RegisterResponse, summary="用户注册")
def register(request: RegisterRequest):
    """
    用户注册接口。
    
    请求体：
    - username: 用户名（3-32字符）
    - email: 邮箱地址
    - password: 密码（6-64字符）
    - nickname: 昵称（可选）
    """
    result = AuthService.register(
        username=request.username,
        email=request.email,
        password=request.password,
        nickname=request.nickname or "",
    )
    return result


@router.post("/login", response_model=LoginResponse, summary="用户登录")
def login(request: LoginRequest):
    """
    用户登录接口。
    
    请求体：
    - username_or_email: 用户名或邮箱
    - password: 密码
    """
    result = AuthService.login(
        username_or_email=request.username_or_email,
        password=request.password,
    )
    return result


@router.post("/login/form", response_model=LoginResponse, summary="用户登录（表单格式）")
def login_form(form_data: OAuth2PasswordRequestForm = Depends()):
    """
    用户登录接口（OAuth2 表单格式）。
    
    用于 Swagger UI 测试。
    """
    result = AuthService.login(
        username_or_email=form_data.username,
        password=form_data.password,
    )
    return result


@router.post("/refresh", response_model=RefreshResponse, summary="刷新访问令牌")
def refresh(request: RefreshRequest):
    """
    刷新访问令牌接口。
    
    请求体：
    - refresh_token: 刷新令牌
    """
    result = AuthService.refresh_token(refresh_token=request.refresh_token)
    return result


@router.get("/me", response_model=UserResponse, summary="获取当前用户信息")
def get_current_user(token: str = Depends(oauth2_scheme)):
    """
    获取当前登录用户信息。
    
    需要在请求头中携带 Authorization: Bearer <access_token>
    """
    user = AuthService.get_current_user(token)
    if not user:
        from api.errors import AppError
        raise AppError(401, "unauthorized", "未登录或令牌无效")
    
    return {
        "id": user["id"],
        "username": user["username"],
        "email": user["email"],
        "nickname": user.get("nickname", ""),
        "role": user["role"],
        "status": user["status"],
        "created_at": user["created_at"],
        "last_login_at": user.get("last_login_at"),
    }