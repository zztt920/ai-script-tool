"""任务管理 API Router。

端点一览：
- GET  /tasks                任务列表（分页+筛选）
- GET  /tasks/{id}           任务状态 + 进度
- GET  /tasks/{id}/script    下载剧本 YAML（支持缓存）
- GET  /tasks/{id}/review    获取质量审核报告
- POST /tasks/{id}/validate  Schema 校验
- POST /tasks/{id}/polish    去 AI 味对话润色
- DELETE /tasks/{id}         删除任务
"""

from fastapi import APIRouter, Query
from pathlib import Path

from api.schemas import (
    TaskStatusResponse, TaskListResponse, TaskProgress,
    ValidationReportResponse, QualityReviewResponse, ReviewDimension,
    PolishRequest, PolishResponse, StyleInfo, StylesResponse,
)
from api.errors import AppError
from adapter.repository import TaskRepository, ScriptRepository
from adapter.ai_client import AIClient
from adapter.cache import cache
from domain.schema_validator import ScriptSchemaValidator
from domain.enums import GenreStyle

router = APIRouter(prefix="/tasks", tags=["Tasks"])

# ── 常量 ──────────────────────────────────────────
_STEP_LABELS = {
    "loading": "加载章节",
    "analyzing": "全局分析（角色/类型）",
    "extracting_scenes": "场景提取",
    "polishing": "对话润色",
    "building": "组装剧本",
    "writing": "输出 YAML",
    "validating": "Schema 校验",
    "reviewing": "AI 质量审核",
    "persisting": "持久化到数据库",
}

# 风格信息表（提供给前端/用户选择）
_STYLES = [
    StyleInfo(value="悬疑", label="悬疑", description="反转钩子、追剧欲望、层层剥开真相",
              act_count=5, act_titles=["谜面", "误导", "追查", "反转", "真相"]),
    StyleInfo(value="甜宠", label="甜宠", description="恋爱甜度、心动瞬间、双向奔赴",
              act_count=4, act_titles=["邂逅", "试探", "考验", "奔赴"]),
    StyleInfo(value="热血", label="热血", description="燃点密集、逆袭爽感、战力突破",
              act_count=4, act_titles=["觉醒", "闯关", "逆袭", "封神"]),
    StyleInfo(value="沙雕", label="沙雕", description="搞笑搞怪、神转折、反差萌",
              act_count=4, act_titles=["离谱开局", "越搞越糟", "神转折", "圆满收场"]),
    StyleInfo(value="都市", label="都市", description="现实题材、职场生态、情感共鸣",
              act_count=4, act_titles=["困局", "挣扎", "抉择", "破局"]),
    StyleInfo(value="古装", label="古装", description="权谋宫斗、古典韵味、身份等级",
              act_count=4, act_titles=["入局", "博弈", "翻覆", "定鼎"]),
    StyleInfo(value="仙侠", label="仙侠", description="修仙体系、宏大世界观、境界突破",
              act_count=5, act_titles=["入门", "筑基", "渡劫", "飞升", "开天"]),
    StyleInfo(value="科幻", label="科幻", description="未来设定、科技反思、人性冲突",
              act_count=4, act_titles=["发现", "探索", "危机", "重生"]),
    StyleInfo(value="惊悚", label="惊悚", description="氛围营造、心理恐惧、逐步崩溃",
              act_count=4, act_titles=["征兆", "升级", "崩溃", "余悸"]),
    StyleInfo(value="自动", label="自动", description="由 AI 自动从原文推断最合适的风格",
              act_count=0, act_titles=["AI 动态分析"]),
]


# ── 任务列表 ──────────────────────────────────────
@router.get("/", response_model=TaskListResponse)
def list_tasks(
    status: str = Query(None, description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    result = TaskRepository.list(status=status, page=page, page_size=page_size)
    items = []
    for t in result["items"]:
        script = ScriptRepository.get_by_task(t["id"])
        items.append(TaskStatusResponse(
            task_id=t["id"], status=t["status"],
            progress=TaskProgress(
                current_step=_STEP_LABELS.get(t.get("current_step", ""), t.get("status", "")),
                total_chapters=t.get("total_chapters", 0),
                processed_chapters=t.get("processed_chapters", 0),
                total_scenes=t.get("total_scenes", 0),
            ),
            script_available=script is not None,
            created_at=t["created_at"], completed_at=t.get("completed_at"),
            error_message=t.get("error_message"),
        ))
    return TaskListResponse(items=items, total=result["total"], page=result["page"], page_size=result["page_size"])


# ── 仪表盘统计 ────────────────────────────────────
@router.get("/stats", response_description="仪表盘统计信息")
def get_stats():
    """获取仪表盘聚合统计数据。"""
    from db.database import get_connection
    with get_connection() as conn:
        total_tasks = conn.execute("SELECT COUNT(*) FROM task").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM task WHERE status='completed'").fetchone()[0]
        processing = conn.execute("SELECT COUNT(*) FROM task WHERE status='processing'").fetchone()[0]
        failed = conn.execute("SELECT COUNT(*) FROM task WHERE status='failed'").fetchone()[0]
        pending = conn.execute("SELECT COUNT(*) FROM task WHERE status='pending'").fetchone()[0]
        total_scenes = conn.execute("SELECT COALESCE(SUM(total_scenes), 0) FROM script").fetchone()[0]
        total_beats = conn.execute("SELECT COALESCE(SUM(total_beats), 0) FROM script").fetchone()[0]
        recent = conn.execute("SELECT COUNT(*) FROM script WHERE created_at >= datetime('now', '-7 days')").fetchone()[0]
    
    return {
        "tasks": {"total": total_tasks, "completed": completed, "processing": processing, "failed": failed, "pending": pending},
        "scripts": {"total_scenes": total_scenes or 0, "total_beats": total_beats or 0, "recent_7d": recent},
    }


# ── 风格列表（必须在 /{task_id} 之前注册）─────────
@router.get("/styles", response_model=StylesResponse, tags=["Meta"])
def list_styles():
    """返回所有可用的风格模板列表及各自的分幕结构。"""
    return StylesResponse(styles=_STYLES, default="自动")


# ── 任务详情 ──────────────────────────────────────
@router.get("/{task_id}", response_model=TaskStatusResponse)
def get_task(task_id: str):
    task = TaskRepository.get(task_id)
    if not task:
        raise AppError(404, "not_found", "任务不存在")
    script = ScriptRepository.get_by_task(task_id)

    # 优先使用 DB 中存储的精确步骤，回退到状态推断
    db_step = task.get("current_step", "")
    if db_step:
        current_step = _STEP_LABELS.get(db_step, db_step)
    else:
        current_step = _STEP_LABELS.get(task.get("status", ""), task.get("status", ""))
        if task["status"] == "processing":
            if task.get("processed_chapters", 0) > 0:
                current_step = _STEP_LABELS["extracting_scenes"]
            elif task.get("total_chapters", 0) > 0:
                current_step = _STEP_LABELS["analyzing"]
            else:
                current_step = _STEP_LABELS["loading"]

    return TaskStatusResponse(
        task_id=task_id,
        status=task["status"],
        progress=TaskProgress(
            current_step=current_step,
            total_chapters=task.get("total_chapters", 0),
            processed_chapters=task.get("processed_chapters", 0),
            total_scenes=task.get("total_scenes", 0),
        ),
        script_available=script is not None,
        created_at=task["created_at"],
        completed_at=task.get("completed_at"),
        error_message=task.get("error_message"),
    )


# ── 下载剧本 ──────────────────────────────────────
@router.get("/{task_id}/script", response_description="剧本 YAML 内容（支持缓存）")
def download_script(task_id: str):
    task = TaskRepository.get(task_id)
    if not task:
        raise AppError(404, "not_found", "任务不存在")
    if task["status"] not in ("completed",):
        raise AppError(409, "conflict", f"任务尚未完成（当前状态: {task['status']}），无法下载剧本")
    script = ScriptRepository.get_by_task(task_id)
    if not script:
        raise AppError(404, "not_found", "剧本不存在")
    
    import yaml
    from fastapi.responses import PlainTextResponse
    
    # 尝试从缓存获取
    cache_key = f"script:content:{task_id}"
    cached_content = cache.get(cache_key)
    
    if cached_content:
        content = cached_content
    else:
        # 从文件读取
        path = script.get("yaml_path", "")
        if not path:
            raise AppError(404, "not_found", "YAML 文件路径不存在")
        p = Path(path)
        if not p.exists():
            raise AppError(404, "not_found", "YAML 文件已被删除")
        
        content = p.read_text(encoding="utf-8")
        
        # 根据任务配置中的语言输出中文 key 名
        import json
        cfg = json.loads(task.get("config", "{}"))
        if cfg.get("language", "zh") == "zh":
            data = yaml.safe_load(content)
            from adapter.yaml_writer import _KEY_MAP_ZH, _translate_keys
            data = _translate_keys(data, _KEY_MAP_ZH)
            from io import StringIO
            buf = StringIO()
            yaml.dump(data, buf, allow_unicode=True, default_flow_style=False,
                      sort_keys=False, indent=2, width=120)
            content = buf.getvalue()
        
        # 缓存结果（24小时）
        cache.set(cache_key, content, expire_seconds=86400)
    
    return PlainTextResponse(content, media_type="text/yaml")


# ── Schema 校验 ───────────────────────────────────
@router.post("/{task_id}/validate", response_model=ValidationReportResponse)
def validate_task_script(task_id: str):
    script = ScriptRepository.get_by_task(task_id)
    if not script:
        raise AppError(404, "not_found", "剧本不存在")
    path = script.get("yaml_path", "")
    if not path:
        raise AppError(404, "not_found", "YAML 文件路径不存在")
    validator = ScriptSchemaValidator()
    report = validator.validate_file(path)
    return ValidationReportResponse(
        task_id=task_id, valid=report.valid,
        errors=report.errors, warnings=report.warnings,
        error_count=len(report.errors), warning_count=len(report.warnings),
    )


# ── 质量审核 ──────────────────────────────────────
@router.get("/{task_id}/review", response_model=QualityReviewResponse)
def get_review(task_id: str):
    """获取已完成任务的 AI 质量审核报告。"""
    script = ScriptRepository.get_by_task(task_id)
    if not script:
        raise AppError(404, "not_found", "剧本不存在")
    report_str = script.get("validation_report", "")
    if not report_str:
        raise AppError(404, "not_found", "审核报告不存在，任务可能未启用 enable_review")
    import json
    try:
        data = json.loads(report_str) if isinstance(report_str, str) else report_str
    except (json.JSONDecodeError, TypeError):
        raise AppError(500, "internal_error", "审核报告数据损坏")
    review = data.get("quality_review", {})
    if not review:
        raise AppError(404, "not_found", "质量审核数据不存在")
    dims = [ReviewDimension(**d) for d in review.get("dimensions", [])]
    return QualityReviewResponse(
        task_id=task_id,
        total_score=review.get("total_score", 0),
        grade=review.get("grade", "N/A"),
        dimensions=dims,
        top_strengths=review.get("top_strengths", []),
        top_issues=review.get("top_issues", []),
        improvement_plan=review.get("improvement_plan", ""),
        ai_trace_level=review.get("ai_trace_level", "?"),
        ai_trace_notes=review.get("ai_trace_notes", ""),
    )


# ── 去 AI 味润色 ──────────────────────────────────
@router.post("/{task_id}/polish", response_model=PolishResponse)
def polish_dialogues(task_id: str, req: PolishRequest | None = None):
    """对已完成剧本的对话执行去 AI 味润色。"""
    if req is None:
        req = PolishRequest()
    import os
    script = ScriptRepository.get_by_task(task_id)
    if not script:
        raise AppError(404, "not_found", "剧本不存在")
    path = script.get("yaml_path", "")
    if not path or not Path(path).exists():
        raise AppError(404, "not_found", "YAML 文件不存在")

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        raise AppError(500, "internal_error", "API Key 未配置")

    import yaml
    with open(path, "r", encoding="utf-8") as f:
        script_data = yaml.safe_load(f)

    # 收集角色信息
    char_map = {}
    for c in script_data.get("characters", []):
        char_map[c["character_id"]] = c

    # 收集待润色对话
    to_polish = []
    target_scenes = set(req.scene_ids) if req.scene_ids else None
    for scene in script_data.get("scenes", []):
        sid = scene.get("scene_id")
        if target_scenes and sid not in target_scenes:
            continue
        for beat in scene.get("beats", []):
            if beat.get("beat_type") == "dialogue" and beat.get("content"):
                # 附加上下文
                beat["_scene_id"] = sid
                to_polish.append(beat)

    if not to_polish:
        return PolishResponse(task_id=task_id, polished_count=0, message="无可润色的对话")

    # 调用质量审核服务的去 AI 味方法
    from service.quality_review_service import QualityReviewService
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    client = AIClient(api_key=api_key, api_base=api_base)
    review_svc = QualityReviewService(client)

    # 批量处理（每批最多 30 条）
    polished = 0
    for batch_start in range(0, len(to_polish), 30):
        batch = to_polish[batch_start:batch_start + 30]
        lines = [f"[{d['character_id']}] {d['content']}" for d in batch]
        prompt = review_svc.anti_ai_polish_prompt(
            lines, list(char_map.keys()))
        result = client.chat(prompt, "去AI味润色")
        if isinstance(result, dict) and "lines" in result:
            for i, new_line in enumerate(result["lines"]):
                if i < len(batch):
                    batch[i]["content"] = new_line
                    polished += 1

    # 写回 YAML
    YAMLWriter = __import__("adapter.yaml_writer", fromlist=["YAMLWriter"]).YAMLWriter
    YAMLWriter.write(script_data, path)

    return PolishResponse(task_id=task_id, polished_count=polished,
                          message=f"已润色 {polished} 条对话")


# ── 删除任务 ──────────────────────────────────────
@router.delete("/{task_id}")
def delete_task(task_id: str):
    task = TaskRepository.get(task_id)
    if not task:
        raise AppError(404, "not_found", "任务不存在")
    TaskRepository.delete(task_id)
    return {"task_id": task_id, "deleted": True}
