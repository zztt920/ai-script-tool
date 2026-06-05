"""YAML 写入器 — 将剧本字典序列化为 YAML 文件，支持 key 名语言切换。"""

import yaml
import logging
from pathlib import Path

log = logging.getLogger("adapter.yaml_writer")

# YAML key 名中英对照表（内部英→中文输出）
_KEY_MAP_ZH = {
    # meta
    "meta": "元信息",
    "script_title": "剧本标题",
    "original_novel": "原著名称",
    "original_author": "原著作者",
    "adapter": "改编工具",
    "script_version": "剧本版本",
    "created_at": "创建时间",
    "updated_at": "更新时间",
    "genre": "类型标签",
    "script_type": "剧本类型",
    "total_scenes": "场景总数",
    "total_episodes": "总集数",
    "target_audience": "目标受众",
    "synopsis": "故事梗概",
    "theme_keywords": "主题关键词",
    "adaptation_notes": "改编说明",
    # characters
    "characters": "角色列表",
    "character_id": "角色ID",
    "name": "姓名",
    "aliases": "别名",
    "role_type": "角色类型",
    "gender": "性别",
    "age_range": "年龄段",
    "occupation": "职业",
    "importance": "重要度",
    "physical_description": "外貌特征",
    "personality_traits": "性格特征",
    "background": "背景故事",
    "motivation": "核心动机",
    "arc_summary": "角色弧光",
    "speech_style": "语言风格",
    "secrets": "隐藏秘密",
    "relationships": "角色关系",
    "relation_type": "关系类型",
    "target_character_id": "关联角色ID",
    "description": "描述",
    "conflict_level": "冲突等级",
    "relationship_arc": "关系弧线",
    "first_appearance_scene": "首次出场场景",
    # acts
    "acts": "分幕结构",
    "act_number": "幕序号",
    "title": "幕标题",
    "narrative_function": "叙事功能",
    "scene_range": "场景范围",
    "start": "起始场景",
    "end": "结束场景",
    "key_turning_points": "关键转折",
    # scenes
    "scenes": "场景列表",
    "scene_id": "场景编号",
    "episode": "所属集数",
    "scene_heading": "场景标题",
    "interior_exterior": "内外景",
    "location": "地点",
    "time": "时间",
    "time_period": "时代背景",
    "source_reference": "原著出处",
    "novel_chapter": "原著章节",
    "novel_chapter_title": "原著章节标题",
    "excerpt": "原文摘录",
    "summary": "场景概要",
    "scene_function": "场景功能",
    "emotional_tone": "情感基调",
    "tension_level": "紧张度",
    "characters_present": "出场角色",
    "props": "道具",
    "beats": "节拍",
    "transition": "转场",
    "estimated_duration": "预计时长",
    "notes": "备注",
    # beats
    "beat_id": "节拍编号",
    "beat_type": "节拍类型",
    "content": "内容",
    "subtext": "潜台词",
    "emotion": "情绪",
    "parenthetical": "动作指示",
    "duration_hint": "时长提示",
    "camera_hint": "镜头提示",
    # revisions
    "revisions": "修订记录",
    "version": "版本",
    "timestamp": "时间戳",
    "author": "修订者",
    "changed_scenes": "修改场景",
}


class YAMLWriter:
    """将 Script.to_dict() 的输出写入 YAML 文件，支持 key 名中文化。"""

    @staticmethod
    def write(script: dict, output_path: str) -> str:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        class ScriptDumper(yaml.Dumper):
            pass

        def str_representer(dumper, data):
            if "\n" in data:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")
            if len(data) > 80:
                return dumper.represent_scalar("tag:yaml.org,2002:str", data, style=">")
            return dumper.represent_scalar("tag:yaml.org,2002:str", data)

        ScriptDumper.add_representer(str, str_representer)

        with open(out, "w", encoding="utf-8") as f:
            yaml.dump(
                script, f,
                Dumper=ScriptDumper,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
                indent=2,
                width=120,
            )

        log.info("剧本已生成: %s (%.1f KB)", out, out.stat().st_size / 1024)
        return str(out)

    @staticmethod
    def write_localized(script: dict, output_path: str, language: str = "zh") -> str:
        """写入 YAML，key 名跟随语言（zh 时翻译为中文，en 保持英文）。"""
        if language == "zh":
            script = _translate_keys(script, _KEY_MAP_ZH)
        return YAMLWriter.write(script, output_path)


def _translate_keys(obj, key_map):
    """递归翻译 dict 的 key 名。"""
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            new_key = key_map.get(k, k)
            result[new_key] = _translate_keys(v, key_map)
        return result
    if isinstance(obj, list):
        return [_translate_keys(item, key_map) for item in obj]
    return obj
