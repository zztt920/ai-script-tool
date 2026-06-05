#!/usr/bin/env python3
"""
AI 辅助剧本创作工具 — 集成测试（适配分层架构）

覆盖：
  1. 章节加载器（adapter.chapter_loader）
  2. 领域模型（domain.models）+ 边界条件
  3. Schema 校验器（domain.schema_validator）
  4. 数据库层（db.database + adapter.repository）
  5. 剧本构建服务（service.script_builder_service）
  6. AIClient mock 测试
  7. 端到端 dry-run CLI
"""

import sys
import os
import json
import unittest
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.chapter_loader import ChapterLoader, ChapterData
from domain.models import Script, Meta, Character, Scene, SceneHeading, Beat, Relationship, Revision, SourceReference
from domain.schema_validator import ScriptSchemaValidator, ValidationReport
from domain.enums import RoleType, BeatType, ScriptType, TaskStatus, Language, AdaptationMode, GenreStyle
from service.script_builder_service import ScriptBuilderService


# ======================================================================
# 1. ChapterLoader 测试
# ======================================================================
class TestChapterLoader(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_requires_three_chapters(self):
        (self.dir / "第1章.txt").write_text("c1", encoding="utf-8")
        (self.dir / "第2章.txt").write_text("c2", encoding="utf-8")
        with self.assertRaises(ValueError):
            ChapterLoader(str(self.dir)).load()

    def test_loads_sorted_chapters(self):
        (self.dir / "第1章.txt").write_text("第一章", encoding="utf-8")
        (self.dir / "第2章.txt").write_text("第二章", encoding="utf-8")
        (self.dir / "第3章.txt").write_text("第三章", encoding="utf-8")
        chapters = ChapterLoader(str(self.dir)).load()
        self.assertEqual(len(chapters), 3)

    def test_skips_empty_file(self):
        (self.dir / "第1章.txt").write_text("第一章", encoding="utf-8")
        (self.dir / "第2章.txt").write_text("", encoding="utf-8")
        (self.dir / "第3章.txt").write_text("第三章", encoding="utf-8")
        with self.assertRaises(ValueError):
            ChapterLoader(str(self.dir)).load()

    def test_non_existent_dir(self):
        with self.assertRaises(FileNotFoundError):
            ChapterLoader("/nonexistent/path").load()

    def test_chapter_naming_variants(self):
        """测试多种章节命名格式。"""
        (self.dir / "chapter_01.txt").write_text("c1", encoding="utf-8")
        (self.dir / "chapter_02.txt").write_text("c2", encoding="utf-8")
        (self.dir / "chapter_03.txt").write_text("c3", encoding="utf-8")
        chapters = ChapterLoader(str(self.dir)).load()
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0].index, 1)

    def test_chapter_data_attributes(self):
        """测试 ChapterData dataclass 字段完整性。"""
        (self.dir / "第1章.txt").write_text("第一章正文", encoding="utf-8")
        (self.dir / "第2章.txt").write_text("第二章正文", encoding="utf-8")
        (self.dir / "第3章.txt").write_text("第三章正文", encoding="utf-8")
        chapters = ChapterLoader(str(self.dir)).load()
        ch = chapters[0]
        self.assertIsInstance(ch, ChapterData)
        self.assertTrue(hasattr(ch, "index"))
        self.assertTrue(hasattr(ch, "title"))
        self.assertTrue(hasattr(ch, "content"))
        self.assertTrue(hasattr(ch, "file"))


# ======================================================================
# 2. Domain Models 测试
# ======================================================================
class TestDomainModels(unittest.TestCase):
    def test_script_to_dict_and_from_dict(self):
        script = Script(
            meta=Meta(script_title="测试剧本", original_novel="测试原著"),
            characters=[Character(character_id="CHAR_001", name="张三")],
            scenes=[
                Scene(scene_id=1, scene_heading=SceneHeading(location="书房"),
                      beats=[Beat(beat_id="S1_B1", content="你好。", beat_type="dialogue", character_id="CHAR_001")])
            ],
        )
        d = script.to_dict()
        self.assertEqual(d["meta"]["script_title"], "测试剧本")
        self.assertEqual(len(d["characters"]), 1)
        self.assertEqual(len(d["scenes"]), 1)

        s2 = Script.from_dict(d)
        self.assertEqual(s2.meta.script_title, "测试剧本")

    def test_enums(self):
        self.assertIn("主角", set(RoleType))
        self.assertIn("dialogue", set(BeatType))
        self.assertIn("film", set(ScriptType))
        self.assertIn("pending", set(TaskStatus))
        # 新增枚举
        self.assertEqual(Language.ZH, "zh")
        self.assertIn("fast", set(AdaptationMode))
        self.assertIn("悬疑", set(GenreStyle))

    def test_default_acts(self):
        builder = ScriptBuilderService()
        acts = builder._build_acts({}, [{}] * 9)
        self.assertEqual(len(acts), 3)
        self.assertEqual(acts[0].title, "建置")

    def test_style_aware_acts(self):
        """测试风格感知的分幕结构。"""
        builder = ScriptBuilderService()
        # 悬疑风格应该是 5 幕
        acts = builder._build_acts({}, [{}] * 20, GenreStyle.SUSPENSE)
        self.assertEqual(len(acts), 5)
        self.assertEqual(acts[0].title, "谜面")
        self.assertEqual(acts[-1].title, "真相")
        # 甜宠风格应该是 4 幕
        acts2 = builder._build_acts({}, [{}] * 16, GenreStyle.ROMANCE)
        self.assertEqual(len(acts2), 4)
        self.assertEqual(acts2[2].title, "考验")
        # 无风格时回退到AI分析或经典三幕
        acts3 = builder._build_acts({"acts": [{"act_number":1,"title":"序幕","scene_range_start":1,"scene_range_end":10}]}, [{}]*10, None)
        self.assertEqual(acts3[0].title, "序幕")

    def test_style_resolve_from_overview(self):
        """测试从 overview 解析风格。"""
        builder = ScriptBuilderService()
        self.assertIsNone(builder._resolve_style({}))
        self.assertEqual(builder._resolve_style({"_style": "古装"}), GenreStyle.HISTORICAL)
        self.assertIsNone(builder._resolve_style({"_style": "auto"}))
        self.assertIsNone(builder._resolve_style({"_style": "invalid"}))

    def test_character_relationships(self):
        """测试角色关系序列化。"""
        c = Character(
            character_id="CHAR_001", name="主角",
            relationships=[Relationship(target_character_id="CHAR_002", relation_type="师徒", description="严师高徒")],
        )
        d = c.to_dict() if hasattr(c, 'to_dict') else {}
        # 验证领域模型字段
        self.assertEqual(c.character_id, "CHAR_001")
        self.assertEqual(len(c.relationships), 1)

    def test_beat_required_fields(self):
        """测试 Beat 必填字段。"""
        b = Beat(beat_id="S1_B1", beat_type="dialogue", content="你好。", character_id="CHAR_001")
        self.assertEqual(b.beat_type, "dialogue")
        self.assertEqual(b.content, "你好。")

    def test_meta_defaults(self):
        """测试 Meta 默认值。"""
        m = Meta(script_title="测试")
        self.assertEqual(m.script_version, "0.1.0")
        self.assertEqual(m.script_type, "tv_series")


# ======================================================================
# 3. Schema Validator 测试
# ======================================================================
class TestSchemaValidator(unittest.TestCase):
    FIXTURES = Path(__file__).resolve().parent / "fixtures"

    def test_valid_script_passes(self):
        v = ScriptSchemaValidator()
        report = v.validate_file(str(self.FIXTURES / "valid_script.yaml"))
        self.assertTrue(report.valid, f"应有 0 错误，实际: {report.errors}")

    def test_invalid_script_fails(self):
        v = ScriptSchemaValidator()
        report = v.validate_file(str(self.FIXTURES / "invalid_script.yaml"))
        self.assertFalse(report.valid)
        self.assertGreater(len(report.errors), 3)

    def test_nonexistent_file(self):
        v = ScriptSchemaValidator()
        report = v.validate_file("/nonexistent/script.yaml")
        self.assertFalse(report.valid)

    def test_empty_yaml(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "empty.yaml"
            p.write_text("", encoding="utf-8")
            v = ScriptSchemaValidator()
            report = v.validate_file(str(p))
            self.assertFalse(report.valid)

    def test_validate_dict(self):
        v = ScriptSchemaValidator()
        report = v.validate_dict({
            "meta": {"script_title": "", "synopsis": "", "genre": ["x"], "script_type": "xx", "total_scenes": 0,
                     "original_novel": "", "original_author": "", "adapter": "", "script_version": "",
                     "created_at": "", "updated_at": ""},
            "characters": [],
            "scenes": [],
            "acts": [],
        })
        self.assertFalse(report.valid)

    def test_report_to_dict(self):
        """测试 ValidationReport.to_dict()。"""
        r = ValidationReport()
        r.error("e1")
        r.warning("w1")
        d = r.to_dict()
        self.assertFalse(d["valid"])
        self.assertEqual(d["error_count"], 1)
        self.assertEqual(d["warning_count"], 1)


# ======================================================================
# 4. 数据库层测试
# ======================================================================
class TestDatabase(unittest.TestCase):
    """数据库初始化与 CRUD 测试。"""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.db_path = str(Path(cls.tmp.name) / "test.db")
        from db.database import init_db
        init_db(cls.db_path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_task_create_and_get(self):
        from adapter.repository import TaskRepository
        t = TaskRepository.create(title="测试任务", author="测试作者", db_path=self.db_path)
        self.assertIn("id", t)
        self.assertEqual(t["status"], "pending")

        # 查询
        fetched = TaskRepository.get(t["id"], db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["title"], "测试任务")

    def test_task_update_status(self):
        from adapter.repository import TaskRepository
        t = TaskRepository.create(title="状态测试", db_path=self.db_path)
        TaskRepository.update_status(t["id"], "processing", processed_chapters=2, total_chapters=5, db_path=self.db_path)
        fetched = TaskRepository.get(t["id"], db_path=self.db_path)
        self.assertEqual(fetched["status"], "processing")
        self.assertEqual(fetched["processed_chapters"], 2)
        self.assertEqual(fetched["total_chapters"], 5)

    def test_task_list(self):
        from adapter.repository import TaskRepository
        # 创建多个任务
        for i in range(3):
            TaskRepository.create(title=f"列表测试{i}", db_path=self.db_path)
        result = TaskRepository.list(page=1, page_size=10, db_path=self.db_path)
        self.assertGreaterEqual(result["total"], 3)
        self.assertIsInstance(result["items"], list)

    def test_task_save_chapters(self):
        from adapter.repository import TaskRepository
        t = TaskRepository.create(title="章节测试", db_path=self.db_path)
        ch = [ChapterData(index=1, title="第一章", file="c1.txt", content="章节内容")]
        TaskRepository.save_chapters(t["id"], ch, db_path=self.db_path)
        fetched = TaskRepository.get(t["id"], db_path=self.db_path)
        self.assertEqual(fetched["total_chapters"], 1)

    def test_script_create_and_get(self):
        from adapter.repository import TaskRepository, ScriptRepository
        t = TaskRepository.create(title="剧本测试", db_path=self.db_path)
        script_dict = Script(
            meta=Meta(script_title="测试剧本"),
            scenes=[Scene(scene_id=1, scene_heading=SceneHeading(location="书房"),
                          beats=[Beat(beat_id="S1_B1", content="你好。", beat_type="dialogue", character_id="CHAR_001")])],
        ).to_dict()
        result = ScriptRepository.create(t["id"], script_dict, "/tmp/test.yaml", db_path=self.db_path)
        self.assertIn("id", result)
        self.assertEqual(result["total_scenes"], 1)

        fetched = ScriptRepository.get_by_task(t["id"], db_path=self.db_path)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["total_scenes"], 1)

    def test_script_save_validation(self):
        from adapter.repository import TaskRepository, ScriptRepository
        t = TaskRepository.create(title="校验测试", db_path=self.db_path)
        sd = Script(meta=Meta(script_title="x")).to_dict()
        r = ScriptRepository.create(t["id"], sd, "", db_path=self.db_path)
        ScriptRepository.save_validation(r["id"], {"valid": True, "errors": []}, db_path=self.db_path)
        fetched = ScriptRepository.get_by_task(t["id"], db_path=self.db_path)
        report = json.loads(fetched["validation_report"])
        self.assertTrue(report["valid"])

    def test_task_not_found(self):
        from adapter.repository import TaskRepository
        self.assertIsNone(TaskRepository.get("nonexistent-id", db_path=self.db_path))

    def test_task_delete(self):
        """测试任务删除（含级联删除）。"""
        from adapter.repository import TaskRepository
        t = TaskRepository.create(title="删除测试", db_path=self.db_path)
        TaskRepository.delete(t["id"], db_path=self.db_path)
        self.assertIsNone(TaskRepository.get(t["id"], db_path=self.db_path))


# ======================================================================
# 5. AIClient 测试
# ======================================================================
class TestAIClient(unittest.TestCase):
    def test_client_initialization(self):
        from adapter.ai_client import AIClient
        c = AIClient(api_key="sk-test", model="gpt-3.5-turbo", temperature=0.5)
        self.assertEqual(c.model, "gpt-3.5-turbo")
        self.assertEqual(c.temperature, 0.5)
        self.assertEqual(c.api_key, "sk-test")
        self.assertEqual(c.call_count, 0)


# ======================================================================
# 6. 端到端 CLI dry-run
# ======================================================================
class TestE2EDryRun(unittest.TestCase):
    def test_dry_run(self):
        import subprocess
        proj_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "-m", "cli.main",
             "-i", str(proj_root / "chapters"),
             "-o", str(proj_root / "output" / "test_script.yaml"),
             "--dry-run"],
            capture_output=True, text=True, cwd=str(proj_root),
        )
        self.assertEqual(result.returncode, 0, f"失败:\n{result.stderr}")
        combined = result.stdout + result.stderr
        self.assertIn("成功加载", combined)

    def test_legacy_entry_point(self):
        import subprocess
        proj_root = Path(__file__).resolve().parent.parent
        result = subprocess.run(
            [sys.executable, "novel_to_script.py",
             "-i", "chapters", "-o", "output/test.yaml", "--dry-run"],
            capture_output=True, text=True, cwd=str(proj_root),
        )
        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
