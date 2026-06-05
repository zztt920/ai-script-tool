"""domain 层 — Schema 校验器（纯领域逻辑，不依赖 adapter/service/cli）。"""

import sys
import re
import argparse
import logging
from pathlib import Path

import yaml

from domain.enums import (
    VALID_ROLE_TYPES, VALID_GENDERS, VALID_SCRIPT_TYPES,
    VALID_IE, VALID_TIMES, VALID_SCENE_FUNCTIONS,
    VALID_BEAT_TYPES, VALID_TRANSITIONS,
)

log = logging.getLogger("domain.validator")
ISO8601_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

# ── 中→英 key 映射表（用于校验中文 YAML 输出） ──────
_CN_TO_EN = {
    # 顶层
    "元信息": "meta", "角色列表": "characters",
    "分幕结构": "acts", "场景列表": "scenes",
    # meta 层
    "剧本标题": "script_title", "原著名称": "original_novel",
    "原著作者": "original_author", "改编工具": "adapter",
    "剧本版本": "script_version", "创建时间": "created_at",
    "更新时间": "updated_at", "类型标签": "genre",
    "剧本类型": "script_type", "场景总数": "total_scenes",
    "总集数": "total_episodes", "故事梗概": "synopsis",
    "主题关键词": "theme_keywords", "改编说明": "adaptation_notes",
    # 角色层
    "角色": "characters", "角色ID": "character_id", "姓名": "name",
    "角色类型": "role_type", "性别": "gender", "年龄段": "age_range",
    "性格特征": "personality_traits", "背景故事": "background",
    "核心动机": "motivation", "角色弧光": "arc_summary",
    "语言风格": "speech_style", "隐藏秘密": "secrets",
    "角色关系": "relationships", "关系类型": "relation_type",
    "关联角色ID": "target_character_id", "冲突等级": "conflict_level",
    "关系弧线": "relationship_arc", "首次出场场景": "first_appearance_scene",
    # 场景层
    "场景编号": "scene_id", "场景标题": "scene_heading",
    "内外景": "interior_exterior", "地点": "location",
    "时间": "time", "时代背景": "time_period",
    "场景概要": "summary", "场景功能": "scene_function",
    "情感基调": "emotional_tone", "紧张度": "tension_level",
    "出场角色": "characters_present", "道具": "props",
    "节拍": "beats", "转场": "transition", "预计时长": "estimated_duration",
    "备注": "notes",
    # 节拍层
    "节拍编号": "beat_id", "节拍类型": "beat_type",
    "内容": "content", "潜台词": "subtext",
    "情绪": "emotion", "动作指示": "parenthetical",
    "时长提示": "duration_hint", "镜头提示": "camera_hint",
    # 幕层
    "幕序号": "act_number", "幕标题": "title",
    "叙事功能": "narrative_function",
    "场景范围": "scene_range",
    "起始场景": "start", "结束场景": "end",
    "关键转折": "key_turning_points",
    # 其他
    "说话角色": "character_id", "描述": "description",
    "重要度": "importance", "职业": "occupation",
    "外貌特征": "physical_description",
    "修改场景": "changed_scenes",
    "导出信息": "export_info", "文件版本": "file_version",
    "校验状态": "validation_status",
}


def _normalize_keys(obj):
    """将中文字段名递归转换为英文字段名（原地修改）。"""
    if isinstance(obj, dict):
        # 先收集需要重命名的 key
        rename = {}
        for k in list(obj.keys()):
            if k in _CN_TO_EN:
                rename[k] = _CN_TO_EN[k]
        for cn_k, en_k in rename.items():
            obj[en_k] = obj.pop(cn_k)
        # 递归处理值
        for v in obj.values():
            _normalize_keys(v)
    elif isinstance(obj, list):
        for item in obj:
            _normalize_keys(item)
    return obj


def _is_chinese_keys(script: dict) -> bool:
    """检测顶层是否使用中文 key。"""
    return any(k in script for k in ("元信息", "角色列表", "分幕结构", "场景列表"))


class ValidationReport:
    """收集校验问题和统计信息。"""

    def __init__(self):
        self.errors: list[str]   = []
        self.warnings: list[str] = []
        self._ok = True

    def error(self, msg: str):
        self.errors.append(msg)
        self._ok = False

    def warning(self, msg: str):
        self.warnings.append(msg)

    @property
    def valid(self) -> bool:
        return self._ok and len(self.errors) == 0

    def print(self):
        print()
        for e in self.errors:
            print(f"  [ERROR]   {e}")
        for w in self.warnings:
            print(f"  [WARN]    {w}")
        status = "通过" if self.valid else "失败"
        print(f"\n  校验结果: {status}  ({len(self.errors)} 错误, {len(self.warnings)} 警告)")

    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
        }


class ScriptSchemaValidator:
    """对剧本 YAML 进行结构化校验（与 CLI 无关的纯验证器）。"""

    def __init__(self, strict: bool = False):
        self.strict = strict
        self.report = ValidationReport()

    def validate_file(self, yaml_path: str) -> ValidationReport:
        path = Path(yaml_path)
        if not path.exists():
            self.report.error(f"文件不存在: {yaml_path}")
            return self.report
        try:
            with open(path, "r", encoding="utf-8") as f:
                script = yaml.safe_load(f)
        except yaml.YAMLError as e:
            self.report.error(f"YAML 解析失败: {e}")
            return self.report
        if not isinstance(script, dict):
            self.report.error("根节点必须是一个字典。")
            return self.report
        # 中文 key 自动转换为英文 key（兼容中文输出模式）
        if _is_chinese_keys(script):
            _normalize_keys(script)
        self._validate(script)
        return self.report

    def validate_dict(self, script: dict) -> ValidationReport:
        """直接校验字典（用于内存中校验）。"""
        if not isinstance(script, dict):
            self.report.error("根节点必须是一个字典。")
            return self.report
        if _is_chinese_keys(script):
            _normalize_keys(script)
        self._validate(script)
        return self.report

    def _validate(self, s: dict):
        for key in ("meta", "characters", "acts", "scenes"):
            if key not in s:
                self.report.error(f"缺少顶层必填字段: {key}")
        self._validate_meta(s.get("meta", {}))
        self._validate_characters(s.get("characters", []))
        self._validate_scenes(s.get("scenes", []))
        self._validate_acts(s.get("acts", []), s.get("scenes", []))
        self._validate_characters_scenes_consistency(s)
        self._validate_revisions(s.get("revisions"))

    def _validate_meta(self, meta: dict):
        if not isinstance(meta, dict):
            self.report.error("meta 必须是一个字典。")
            return
        required = ["script_title", "original_novel", "original_author", "adapter",
                    "script_version", "created_at", "updated_at", "genre",
                    "script_type", "total_scenes", "synopsis"]
        for field in required:
            if field not in meta:
                self.report.error(f"meta.{field} 是必填字段。")
        st = meta.get("script_type", "")
        if st and st not in VALID_SCRIPT_TYPES:
            self.report.error(f"meta.script_type 非法值 '{st}'，允许: {VALID_SCRIPT_TYPES}")
        genre = meta.get("genre", [])
        if not isinstance(genre, list) or len(genre) == 0:
            self.report.error("meta.genre 必须是非空列表。")
        if st == "tv_series" and "total_episodes" not in meta:
            self.report.error("电视剧类型必须提供 meta.total_episodes。")

    def _validate_characters(self, chars: list):
        if not isinstance(chars, list):
            self.report.error("characters 必须是一个数组。")
            return
        if len(chars) == 0:
            self.report.error("characters 不能为空。")
            return
        ids = set()
        for c in chars:
            if not isinstance(c, dict):
                continue
            cid = c.get("character_id", "")
            cname = c.get("name", cid)
            if not isinstance(cid, str) or not cid:
                self.report.error(f"角色缺少 character_id")
                continue
            if cid in ids:
                self.report.error(f"角色 ID 重复: {cid}")
            ids.add(cid)
            if not isinstance(c.get("name"), str) or not c.get("name"):
                self.report.error(f"{cid}.name 是必填字段。")
            # AI 生产数据经常缺字段 — 仅 warn
            for field in ("personality_traits", "background", "motivation", "arc_summary"):
                if field not in c:
                    self.report.warning(f"{cname}.{field} 缺失（AI 未生成）")
            rt = c.get("role_type", "")
            if rt and rt not in VALID_ROLE_TYPES:
                self.report.warning(f"{cname}.role_type 非法值 '{rt}'")
        self._char_ids = ids

    def _validate_scenes(self, scenes: list):
        if not isinstance(scenes, list) or len(scenes) == 0:
            self.report.error("scenes 必须是非空数组。")
            return
        scene_ids = set()
        for s in scenes:
            if not isinstance(s, dict):
                continue
            sid = s.get("scene_id")
            if sid is None or not isinstance(sid, int) or sid < 1:
                self.report.error(f"scene_id 必须是正整数: {sid}")
                continue
            if sid in scene_ids:
                self.report.error(f"场景 ID 重复: {sid}")
            scene_ids.add(sid)
            heading = s.get("scene_heading", {})
            if isinstance(heading, dict):
                ie = heading.get("interior_exterior", "")
                if ie not in VALID_IE:
                    self.report.error(f"S{sid} interior_exterior 非法值 '{ie}'")
                if "location" not in heading:
                    self.report.error(f"S{sid} scene_heading 缺少 location。")
                t = heading.get("time", "")
                if t not in VALID_TIMES:
                    self.report.error(f"S{sid} time 非法值 '{t}'")
            for field in ("summary", "scene_function", "emotional_tone", "characters_present", "beats"):
                if field not in s:
                    if field in ("beats", "summary"):
                        self.report.error(f"场景 S{sid} 缺少必填字段: {field}")
                    else:
                        self.report.warning(f"场景 S{sid} 缺少字段: {field}")
            if "beats" not in s or not isinstance(s.get("beats"), list):
                self.report.error(f"场景 S{sid} beats 必须是数组。")
                continue
            sf = s.get("scene_function", "")
            if sf and sf not in VALID_SCENE_FUNCTIONS:
                self.report.error(f"S{sid}.scene_function 非法值 '{sf}'")
            self._validate_beats(s.get("beats", []), sid)
        expected = set(range(1, len(scenes) + 1))
        if expected - scene_ids:
            self.report.warning(f"场景编号不连续，缺失: {sorted(expected - scene_ids)}")

    def _validate_beats(self, beats: list, sid: int):
        if not isinstance(beats, list):
            self.report.error(f"S{sid} 的 beats 必须是数组。")
            return
        if len(beats) == 0:
            self.report.warning(f"S{sid} 的 beats 为空。")
            return
        for b in beats:
            if not isinstance(b, dict):
                continue
            bid = b.get("beat_id", "?")
            bt = b.get("beat_type", "")
            if bt not in VALID_BEAT_TYPES:
                self.report.error(f"{bid} beat_type 非法值 '{bt}'。")
            if "content" not in b:
                self.report.warning(f"{bid} 缺少 content。")
            if bt in ("dialogue", "monologue", "voiceover") and "character_id" not in b:
                self.report.error(f"{bid} ({bt}) 必须提供 character_id。")

    def _validate_acts(self, acts: list, scenes: list):
        if not isinstance(acts, list):
            self.report.error("acts 必须是数组。")
            return
        total = len(scenes)
        for a in acts:
            if not isinstance(a, dict):
                continue
            sr = a.get("scene_range", {})
            start, end = sr.get("start", 1), sr.get("end", 0)
            if start < 1:
                self.report.error(f"act scene_range.start 必须 >= 1: {start}")
            if end > total:
                self.report.warning(f"act scene_range.end ({end}) 超出场景总数 ({total})。")
            if start > end:
                self.report.error(f"act scene_range 起始 > 结束 ({start}>{end})。")

    def _validate_characters_scenes_consistency(self, script: dict):
        char_ids = getattr(self, "_char_ids", set())
        if not char_ids:
            return
        used_ids = set()
        for s in script.get("scenes", []):
            for cid in s.get("characters_present", []):
                used_ids.add(cid)
                if cid not in char_ids:
                    self.report.error(f"S{s.get('scene_id','?')} 引用了未定义角色: {cid}")
            for b in s.get("beats", []):
                cid = b.get("character_id", "")
                if cid:
                    used_ids.add(cid)
                    if cid not in char_ids:
                        self.report.error(f"S{s.get('scene_id','?')}/{b.get('beat_id','?')} 引用了未定义角色: {cid}")
        unused = char_ids - used_ids
        if unused:
            self.report.warning(f"定义了但未在任何场景中出现的角色: {sorted(unused)}")

    def _validate_revisions(self, revisions):
        if revisions is None or not isinstance(revisions, list):
            return
        for r in revisions:
            if not isinstance(r, dict):
                continue
            for field in ("version", "timestamp", "author", "summary"):
                if field not in r:
                    self.report.warning(f"revision 缺少字段: {field}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description="剧本 YAML Schema 校验器 — 检查输出是否符合 SCRIPT_SCHEMA.md 规范",
    )
    parser.add_argument("yaml_file", help="待校验的剧本 YAML 文件路径")
    parser.add_argument("--strict", action="store_true", help="严格模式：警告也视为错误（影响退出码）")

    args = parser.parse_args()

    v = ScriptSchemaValidator(strict=args.strict)
    report = v.validate_file(args.yaml_file)
    report.print()

    if args.strict and report.warnings:
        print(f"\n  严格模式：{len(report.warnings)} 条警告导致校验失败。")
        return 1

    return 0 if report.valid else 1


if __name__ == "__main__":
    sys.exit(main())
