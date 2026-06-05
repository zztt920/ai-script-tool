"""API Pydantic Schemas — 请求/响应模型。"""

from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from domain.enums import ScriptType, TaskStatus


class ChapterInput(BaseModel):
    title: str = Field(..., min_length=1, description="章节标题")
    content: str = Field(..., min_length=1, description="章节正文")


class ConvertRequest(BaseModel):
    chapters: list[ChapterInput] = Field(..., min_length=3, description="至少 3 个章节")
    title: str = Field(default="", description="原著小说标题")
    author: str = Field(default="", description="原著作者")
    config: Optional[ConvertConfig] = None


class ConvertConfig(BaseModel):
    model: str = Field(default="deepseek-v4-flash", description="AI 模型名称")
    temperature: float = Field(default=0.3, ge=0, le=1)
    script_type: str = Field(default="tv_series")
    language: str = Field(default="zh", description="输出语言：zh(中文)/en(英文)")
    mode: str = Field(default="detail", description="改编模式：fast/detail/hybrid")
    style: Optional[str] = Field(default=None, description="风格模板：悬疑/甜宠/热血/沙雕/都市/古装/仙侠/科幻/惊悚/自动")
    enable_review: bool = Field(default=True, description="是否启用 AI 质量审核")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    created_at: str
    estimated_duration: str = "未知"


class TaskProgress(BaseModel):
    current_step: str = ""
    total_chapters: int = 0
    processed_chapters: int = 0
    total_scenes: int = 0


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    progress: TaskProgress = Field(default_factory=TaskProgress)
    script_available: bool = False
    created_at: str = ""
    completed_at: Optional[str] = None
    error_message: Optional[str] = None


class TaskListResponse(BaseModel):
    items: list[TaskStatusResponse]
    total: int
    page: int
    page_size: int


class ValidationReportResponse(BaseModel):
    task_id: str
    valid: bool
    errors: list[str]
    warnings: list[str]
    error_count: int
    warning_count: int


class ErrorResponse(BaseModel):
    error: str
    message: str
    code: int


# ── 质量审核 ──────────────────────────────────────
class ReviewDimension(BaseModel):
    name: str
    score: int
    comment: str
    priority: str = "中"


class QualityReviewResponse(BaseModel):
    task_id: str
    total_score: int = 0
    grade: str = "N/A"
    dimensions: list[ReviewDimension] = Field(default_factory=list)
    top_strengths: list[str] = Field(default_factory=list)
    top_issues: list[str] = Field(default_factory=list)
    improvement_plan: str = ""
    ai_trace_level: str = "?"
    ai_trace_notes: str = ""


class PolishRequest(BaseModel):
    """去 AI 味润色请求。"""
    scene_ids: list[int] | None = Field(default=None, description="指定场景 ID 列表，默认润色全部")


class PolishResponse(BaseModel):
    task_id: str
    polished_count: int
    message: str


class StyleInfo(BaseModel):
    value: str
    label: str
    description: str
    act_count: int
    act_titles: list[str]


class StylesResponse(BaseModel):
    styles: list[StyleInfo]
    default: str = "自动"


# ── 认证相关模型 ──────────────────────────────────

class RegisterRequest(BaseModel):
    """用户注册请求。"""
    username: str = Field(..., min_length=3, max_length=32, description="用户名")
    email: str = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=64, description="密码")
    nickname: Optional[str] = Field(default="", description="昵称")
    
    @field_validator('email')
    def validate_email(cls, v):
        if '@' not in v:
            raise ValueError('无效的邮箱地址')
        return v


class RegisterResponse(BaseModel):
    """用户注册响应。"""
    user_id: str
    username: str
    email: str


class LoginRequest(BaseModel):
    """用户登录请求。"""
    username_or_email: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class LoginResponse(BaseModel):
    """用户登录响应。"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: dict


class RefreshRequest(BaseModel):
    """刷新令牌请求。"""
    refresh_token: str = Field(..., description="刷新令牌")


class RefreshResponse(BaseModel):
    """刷新令牌响应。"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息响应。"""
    id: str
    username: str
    email: str
    nickname: str
    role: str
    status: str
    created_at: str
    last_login_at: Optional[str]


# ── 批量操作模型 ──────────────────────────────────

class BatchDeleteRequest(BaseModel):
    """批量删除任务请求。"""
    task_ids: list[str] = Field(..., min_length=1, max_length=100, description="待删除的任务 ID 列表")


class BatchDeleteResponse(BaseModel):
    """批量删除任务响应。"""
    deleted_count: int
    errors: list[str] = Field(default_factory=list)
