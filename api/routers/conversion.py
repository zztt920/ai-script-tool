"""转换 API Router。"""

import os
import tempfile
import threading
from pathlib import Path
from fastapi import APIRouter, UploadFile, File

from api.schemas import ConvertRequest, ConvertConfig, TaskResponse
from api.errors import AppError
from adapter.repository import TaskRepository
from adapter.ai_client import AIClient
from service.conversion_pipeline import ConversionPipeline
from domain.enums import Language, AdaptationMode, GenreStyle

router = APIRouter(prefix="/convert", tags=["Conversion"])


def _build_config(cfg: ConvertConfig | None = None) -> dict:
    if cfg is None:
        return {"language": "zh", "mode": "detail", "style": None, "enable_review": True}
    return {"model": cfg.model, "temperature": cfg.temperature, "script_type": cfg.script_type,
            "language": cfg.language, "mode": cfg.mode, "style": cfg.style,
            "enable_review": cfg.enable_review}


def _api_key() -> str:
    key = os.getenv("OPENAI_API_KEY", "")
    if not key:
        raise AppError(500, "internal_error", "API Key 未配置，请联系管理员设置 OPENAI_API_KEY")
    return key


def _db_path() -> str:
    return os.getenv("SCRIPT_DB_PATH", "./data/script_tool.db")


def _start_background_task(task_id: str, tmpdir: str, output_path: str,
                           title: str, author: str, kwargs: dict):
    """共用后台任务 runner — 供 convert_text 和 convert_upload 复用。"""
    api_key = _api_key()
    api_base = os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1")
    db_path = _db_path()

    def _run():
        try:
            model = kwargs.get("model", "deepseek-v4-flash")
            client = AIClient(api_key=api_key, api_base=api_base, model=model)
            pipeline = ConversionPipeline(client, task_id=task_id, db_path=db_path)
            lang = Language(kwargs["language"]) if kwargs.get("language") else Language.ZH
            mode = AdaptationMode(kwargs["mode"]) if kwargs.get("mode") else AdaptationMode.DETAIL
            sty = GenreStyle(kwargs["style"]) if kwargs.get("style") and kwargs["style"] != "auto" else None
            enable_review = kwargs.get("enable_review", True)
            pipeline.run(tmpdir, output_path, title=title, author=author,
                         language=lang, mode=mode, style=sty, enable_review=enable_review)
        except Exception as e:
            TaskRepository.update_status(task_id, "failed", error_message=str(e), db_path=db_path)
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)

    threading.Thread(target=_run, daemon=True).start()


@router.post("", response_model=TaskResponse)
def convert_text(req: ConvertRequest):
    cfg = req.config
    task = TaskRepository.create(title=req.title, author=req.author,
                                 config=_build_config(cfg), db_path=_db_path())

    tmpdir = Path(tempfile.mkdtemp(prefix="novel_"))
    for i, ch in enumerate(req.chapters):
        (tmpdir / f"第{i+1}章.txt").write_text(ch.content, encoding="utf-8")
    out_path = str(Path("output") / f"{task['id']}.yaml")

    _start_background_task(
        task["id"], str(tmpdir), out_path,
        req.title, req.author, _build_config(cfg),
    )
    return TaskResponse(task_id=task["id"], status="pending", created_at=task["created_at"])


@router.post("/upload", response_model=TaskResponse)
def convert_upload(
    files: list[UploadFile] = File(..., description="章节文件，支持 .txt / .docx / .pdf（至少 3 个）"),
    title: str = "",
    author: str = "",
    mode: str = "detail",
    style: str = "auto",
    language: str = "zh",
    enable_review: bool = True,
):
    from adapter.document_parser import parse_document, validate_suffix

    if len(files) < 3:
        raise AppError(422, "validation_error", "至少上传 3 个文件")

    for f in files:
        if not validate_suffix(f.filename or ""):
            raise AppError(422, "validation_error",
                           f"不支持的文件格式: {f.filename}，仅接受 .txt / .docx / .pdf")

    task = TaskRepository.create(title=title, author=author, db_path=_db_path())

    tmpdir = Path(tempfile.mkdtemp(prefix="novel_"))
    parsed_count = 0
    for i, f in enumerate(sorted(files, key=lambda x: x.filename or ""), start=1):
        suffix = Path(f.filename or f"ch_{i}").suffix.lower()
        tmp_file = tmpdir / f"orig_{i}{suffix}"
        try:
            content_bytes = f.file.read()
            tmp_file.write_bytes(content_bytes)
            text = parse_document(str(tmp_file))
            chapter_name = f"第{i}章.txt"
            (tmpdir / chapter_name).write_text(text, encoding="utf-8")
            parsed_count += 1
        except (ValueError, UnicodeDecodeError) as e:
            raise AppError(422, "validation_error",
                           f"无法解析文件 {f.filename}: {e}")

    if parsed_count < 3:
        raise AppError(422, "validation_error", f"成功解析的文件不足 3 个（共 {parsed_count} 个）")

    out_path = str(Path("output") / f"{task['id']}.yaml")

    kwargs = {"language": language, "mode": mode, "style": style, "enable_review": enable_review}
    _start_background_task(task["id"], str(tmpdir), out_path, title, author, kwargs)
    return TaskResponse(task_id=task["id"], status="pending", created_at=task["created_at"])
