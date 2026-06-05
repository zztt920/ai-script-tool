"""转换流水线 — 编排完整的 小说→剧本 转换流程。

增强项：
- 语言选择（中文/英文）
- 三种改编模式（fast/detail/hybrid）
- 10 种风格模板感知
- 新增 质量审核 步骤（参考 Scriptify）
"""

import json
import hashlib
import logging
from pathlib import Path
from typing import Optional, Callable

from adapter.ai_client       import AIClient
from adapter.chapter_loader  import ChapterLoader, ChapterData
from adapter.yaml_writer     import YAMLWriter
from adapter.repository      import TaskRepository, ScriptRepository

from service.analysis_service         import AnalysisService
from service.scene_extraction_service  import SceneExtractionService
from service.dialogue_polish_service   import DialoguePolishService
from service.script_builder_service    import ScriptBuilderService
from service.quality_review_service    import QualityReviewService

from domain.enums import Language, AdaptationMode, GenreStyle

log = logging.getLogger("service.pipeline")


class CheckpointManager:
    """断点管理器，支持中断后恢复。"""

    def __init__(self, checkpoint_dir: str, task_hash: str):
        self.dir = Path(checkpoint_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / f"{task_hash}.json"

    def save(self, key: str, data):
        current = self._load_all()
        current[key] = data
        self.file.write_text(json.dumps(current, ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self, key: str):
        return self._load_all().get(key)

    def _load_all(self) -> dict:
        return json.loads(self.file.read_text(encoding="utf-8")) if self.file.exists() else {}


class ConversionPipeline:
    """完整的 小说→剧本 转换流水线（同步模式）。

    新增参数：
    - language: 输出语言，默认中文
    - mode: 改编模式，默认精细模式
    - style: 风格模板，默认自动推断
    - enable_review: 是否启用量化质量审核，默认 True
    """

    def __init__(self, ai_client: AIClient, checkpoint_dir: str = "./checkpoints",
                 task_id: str = None, db_path: str = None,
                 progress_callback: Callable[[str, dict], None] = None):
        self.ai = ai_client
        self.checkpoint_dir = checkpoint_dir
        self.task_id = task_id
        self.db_path = db_path
        self.progress_callback = progress_callback

        self.analysis_service = AnalysisService(ai_client)
        self.scene_service    = SceneExtractionService(ai_client)
        self.dialogue_service = DialoguePolishService(ai_client)
        self.builder          = ScriptBuilderService(ai_client.model)
        self.review_service   = QualityReviewService(ai_client)

        self.checkpoint: Optional[CheckpointManager] = None

    def run(self, input_dir: str, output_path: str, title: str = "", author: str = "",
            language: Language = Language.ZH,
            mode: AdaptationMode = AdaptationMode.DETAIL,
            style: GenreStyle | None = None,
            enable_review: bool = True) -> str:
        """执行完整转换流水线，返回输出文件路径。"""

        self._language = language
        self._mode = mode
        self._style = style
        self._enable_review = enable_review

        chapters = self._load(input_dir, title, author)

        task_hash = hashlib.md5("".join(c.content[:200] for c in chapters).encode()).hexdigest()[:12]
        self.checkpoint = CheckpointManager(self.checkpoint_dir, task_hash)

        overview    = self._analyze(chapters, title, author)
        all_scenes  = self._extract_scenes(chapters, overview.get("characters", []))
        all_scenes  = self._polish(all_scenes, overview.get("characters", []))
        script      = self._build(chapters, overview, all_scenes)
        self._validate(script)
        result_path = self._write(script, output_path)
        if enable_review:
            self._review(script)
        self._persist(script, result_path)
        return result_path

    def _report(self, step: str, data: dict = None):
        if self.progress_callback:
            self.progress_callback(step, data or {})
        if not self.task_id:
            return
        data = data or {}
        fields = {k: v for k, v in data.items() if k in (
            "total_scenes", "processed_chapters", "total_chapters", "ai_calls")}
        fields["current_step"] = step
        TaskRepository.update_status(self.task_id, "processing",
                                     db_path=self.db_path, **fields)

    def _load(self, input_dir: str, title: str, author: str) -> list[ChapterData]:
        log.info("=" * 50)
        log.info("第 1 步：加载小说章节")
        log.info("=" * 50)
        self._report("loading")
        loader = ChapterLoader(input_dir)
        chapters = loader.load()
        if self.task_id:
            TaskRepository.save_chapters(self.task_id, chapters, self.db_path)
            TaskRepository.update_status(self.task_id, "processing",
                                         total_chapters=len(chapters),
                                         processed_chapters=0,
                                         db_path=self.db_path)
        return chapters

    def _analyze(self, chapters: list[ChapterData], title: str, author: str) -> dict:
        log.info("=" * 50)
        log.info("第 2 步：全局分析（角色、类型、梗概） [语言: %s | 模式: %s | 风格: %s]",
                 self._language.value, self._mode.value, self._style.value if self._style else "自动")
        log.info("=" * 50)
        self._report("analyzing")

        overview = self.checkpoint.load("overview")
        if overview:
            log.info("从断点恢复全局分析结果。")
            return overview

        overview = self.analysis_service.analyze(
            chapters, language=self._language, mode=self._mode, style=self._style)
        if title:
            overview["original_novel"] = title
            overview.setdefault("script_title", f"{title}（改编剧本）")
        if author:
            overview["original_author"] = author
        # 记录运行时参数
        overview["_language"] = self._language.value
        overview["_mode"] = self._mode.value
        overview["_style"] = self._style.value if self._style else "auto"

        self.checkpoint.save("overview", overview)
        log.info("全局分析完成：%d 个角色，类型：%s",
                 len(overview.get("characters", [])), overview.get("genre", []))
        return overview

    def _extract_scenes(self, chapters: list[ChapterData], characters: list[dict]) -> list[dict]:
        log.info("=" * 50)
        log.info("第 3 步：逐章场景提取")
        log.info("=" * 50)
        all_scenes = self.checkpoint.load("all_scenes") or []
        processed = {s.get("_chapter_index", 0) for s in all_scenes}

        for ch in chapters:
            if ch.index in processed:
                continue
            self._report("extracting_scenes", {"chapter": ch.index})
            log.info("处理第 %d 章《%s》...", ch.index, ch.title)
            try:
                scenes = self.scene_service.extract(
                    ch, characters, mode=self._mode, style=self._style, language=self._language)
                for s in scenes:
                    s["_chapter_index"] = ch.index
                all_scenes.extend(scenes)
                self.checkpoint.save("all_scenes", all_scenes)
                if self.task_id:
                    TaskRepository.update_status(self.task_id, "processing",
                                                 processed_chapters=len(processed | {ch.index}),
                                                 total_scenes=len(all_scenes),
                                                 db_path=self.db_path)
            except (KeyError, ValueError, RuntimeError) as e:
                log.error("第 %d 章处理失败: %s", ch.index, str(e))
        log.info("共提取 %d 个场景", len(all_scenes))
        return all_scenes

    def _polish(self, scenes: list[dict], characters: list[dict]) -> list[dict]:
        if len(scenes) > 30:
            log.info("场景较多（%d），跳过对话润色。", len(scenes))
            return scenes
        log.info("=" * 50)
        log.info("第 4 步：对话润色（去 AI 味）")
        log.info("=" * 50)
        self._report("polishing")
        char_map = {c["character_id"]: c for c in characters}
        all_dialogues = []
        for scene in scenes:
            for beat in scene.get("beats", []):
                if beat.get("beat_type") == "dialogue" and beat.get("content"):
                    all_dialogues.append(beat)
        if all_dialogues:
            self.dialogue_service.polish(all_dialogues, char_map, language=self._language)
            self.checkpoint.save("all_scenes", scenes)
            log.info("已润色 %d 条对话", len(all_dialogues))
        return scenes

    def _build(self, chapters: list[ChapterData], overview: dict, scenes: list[dict]):
        log.info("=" * 50)
        log.info("第 5 步：组装结构化剧本")
        log.info("=" * 50)
        self._report("building")
        script = self.builder.build(chapters, overview, scenes, language=self._language)
        return script

    def _write(self, script, output_path: str) -> str:
        log.info("=" * 50)
        log.info("第 6 步：输出 YAML 文件")
        log.info("=" * 50)
        self._report("writing")
        # 内部始终存英文 key 名，下载时按语言翻译 key
        return YAMLWriter.write(script.to_dict(), output_path)

    def _validate(self, script):
        log.info("=" * 50)
        log.info("第 7 步：Schema 校验")
        log.info("=" * 50)
        self._report("validating")
        from domain.schema_validator import ScriptSchemaValidator
        validator = ScriptSchemaValidator()
        report = validator.validate_dict(script.to_dict())
        report.print()
        if not report.valid:
            log.warning("输出文件存在 Schema 不符合项，请检查后手动修正。")

    def _review(self, script):
        """第 8 步：AI 质量审核（新增 — 参考 Scriptify 6 维度检查）。"""
        log.info("=" * 50)
        log.info("第 8 步：AI 质量审核")
        log.info("=" * 50)
        self._report("reviewing")
        try:
            review = self.review_service.review(
                script.to_dict(), mode=self._mode, style=self._style,
                language=self._language)
            score = review.get("total_score", "?")
            grade = review.get("grade", "?")
            issues = review.get("top_issues", [])
            strength = review.get("top_strengths", [])
            ai_trace = review.get("ai_trace_level", "?")

            log.info("质量评分：%s/60 (等级: %s)", score, grade)
            log.info("AI 痕迹等级：%s", ai_trace)
            if strength:
                log.info("亮点：%s", " | ".join(strength[:3]))
            if issues:
                log.warning("改进项：%s", " | ".join(issues[:3]))

            # 持久化审核报告
            if self.task_id:
                script_record = ScriptRepository.get_by_task(self.task_id, self.db_path)
                if script_record:
                    ScriptRepository.save_validation(
                        script_record["id"], {"quality_review": review}, self.db_path)
                self.checkpoint.save("quality_review", review)

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            log.warning("质量审核失败（非致命错误）：%s", e)

    def _persist(self, script, yaml_path: str):
        """持久化到数据库。"""
        if not self.task_id:
            return
        from db.database import init_db
        init_db()
        log.info("=" * 50)
        log.info("第 9 步：持久化到数据库")
        log.info("=" * 50)
        self._report("persisting")
        script_dict = script.to_dict()
        result = ScriptRepository.create(self.task_id, script_dict, yaml_path, self.db_path)
        # 读取 task 获得 total_chapters，确保进度显示 3/3 而非 0/3
        task = TaskRepository.get(self.task_id, self.db_path)
        TaskRepository.update_status(self.task_id, "completed",
                                     total_scenes=result["total_scenes"],
                                     ai_calls=self.ai.call_count,
                                     processed_chapters=task.get("total_chapters", result["total_scenes"]),
                                     db_path=self.db_path)
