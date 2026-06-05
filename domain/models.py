"""领域实体定义 — 纯数据结构，不依赖任何外部模块。"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from .enums import ScriptType, RoleType, Gender, InteriorExterior, TimeOfDay, SceneFunction, BeatType, Transition


# ── 顶层结构 ──────────────────────────────────────────────

@dataclass
class Meta:
    script_title: str
    original_novel: str  = ""
    original_author: str = ""
    adapter: str         = "AI 剧本助手"
    script_version: str  = "0.1.0"
    created_at: str      = ""
    updated_at: str      = ""
    genre: list[str]     = field(default_factory=list)
    script_type: str     = ScriptType.TV_SERIES.value
    total_scenes: int    = 0
    total_episodes: int  = 1
    target_audience: str = ""
    synopsis: str        = ""
    theme_keywords: list[str] = field(default_factory=list)
    adaptation_notes: str = ""


@dataclass
class Relationship:
    target_character_id: str
    relation_type: str
    description: str = ""


@dataclass
class Character:
    character_id: str
    name: str
    role_type: str = RoleType.SUPPORTING.value
    gender: str = ""
    age_range: str = ""
    occupation: str = ""
    physical_description: str = ""
    personality_traits: list[str] = field(default_factory=list)
    background: str = ""
    motivation: str = ""
    arc_summary: str = ""
    speech_style: str = ""
    aliases: list[str] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    first_appearance_scene: Optional[int] = None


# ── 场景相关 ──────────────────────────────────────────────

@dataclass
class SceneHeading:
    interior_exterior: str = InteriorExterior.INTERIOR.value
    location: str = ""
    time: str = TimeOfDay.DAY.value
    time_period: str = ""


@dataclass
class SourceReference:
    novel_chapter: int = 0
    novel_chapter_title: str = ""
    excerpt: str = ""


@dataclass
class Beat:
    beat_id: str
    beat_type: str = BeatType.DESCRIPTION.value
    content: str = ""
    character_id: str = ""
    subtext: str = ""
    emotion: str = ""
    parenthetical: str = ""
    duration_hint: str = ""
    camera_hint: str = ""


@dataclass
class Scene:
    scene_id: int = 0
    episode: int = 1
    scene_heading: SceneHeading = field(default_factory=SceneHeading)
    source_reference: SourceReference = field(default_factory=SourceReference)
    summary: str = ""
    scene_function: str = SceneFunction.ADVANCE_PLOT.value
    emotional_tone: str = ""
    characters_present: list[str] = field(default_factory=list)
    props: list[str] = field(default_factory=list)
    beats: list[Beat] = field(default_factory=list)
    transition: str = Transition.CUT.value
    estimated_duration: str = ""
    notes: str = ""


# ── 分幕 ──────────────────────────────────────────────────

@dataclass
class SceneRange:
    start: int = 1
    end: int = 1


@dataclass
class Act:
    act_number: int
    title: str = ""
    description: str = ""
    scene_range: SceneRange = field(default_factory=SceneRange)
    narrative_function: str = ""


# ── 修订 ──────────────────────────────────────────────────

@dataclass
class Revision:
    version: str
    timestamp: str
    author: str
    summary: str = ""
    changed_scenes: list[int] = field(default_factory=list)


# ── 剧本顶层 ──────────────────────────────────────────────

@dataclass
class Script:
    meta: Meta = field(default_factory=Meta)
    characters: list[Character] = field(default_factory=list)
    acts: list[Act] = field(default_factory=list)
    scenes: list[Scene] = field(default_factory=list)
    revisions: list[Revision] = field(default_factory=list)

    def to_dict(self) -> dict:
        """将 Script 转换为符合 YAML Schema 的字典。"""
        return {
            "meta": _dataclass_to_dict(self.meta),
            "characters": [_dataclass_to_dict(c) for c in self.characters],
            "acts": [_dataclass_to_dict(a) for a in self.acts],
            "scenes": [_serialize_scene(s) for s in self.scenes],
            "revisions": [_dataclass_to_dict(r) for r in self.revisions],
        }

    @staticmethod
    def from_dict(data: dict) -> "Script":
        """从字典反序列化 Script。"""
        meta = Meta(**_strip_extra(data.get("meta", {}), Meta))
        chars = [_parse_character(c) for c in data.get("characters", [])]
        acts  = [_parse_act(a) for a in data.get("acts", [])]
        scenes = [_parse_scene(s) for s in data.get("scenes", [])]
        revisions = [_parse_revision(r) for r in data.get("revisions", [])]
        return Script(meta=meta, characters=chars, acts=acts, scenes=scenes, revisions=revisions)


# ── 序列化辅助 ────────────────────────────────────────────

def _dataclass_to_dict(obj) -> dict:
    """将 dataclass 实例递归转为字典，跳过空值和默认值。"""
    if isinstance(obj, dict):
        return {k: _dataclass_to_dict(v) for k, v in obj.items() if v is not None}
    if isinstance(obj, list):
        return [_dataclass_to_dict(item) for item in obj if item is not None]
    import dataclasses
    if not dataclasses.is_dataclass(obj):
        return obj  # 原生类型（str/int/bool 等）直接返回
    result = {}
    for f in dataclasses.fields(obj):
        v = getattr(obj, f.name)
        if v is None or (isinstance(v, (list, str)) and not v):
            continue
        if dataclasses.is_dataclass(v):
            result[f.name] = _dataclass_to_dict(v)
        elif isinstance(v, list) and v and dataclasses.is_dataclass(v[0]):
            result[f.name] = [_dataclass_to_dict(item) for item in v]
        else:
            result[f.name] = v
    return result


def _strip_extra(data: dict, cls) -> dict:
    """只保留 dataclass 定义的字段。"""
    import dataclasses
    valid = {f.name for f in dataclasses.fields(cls)}
    return {k: v for k, v in data.items() if k in valid}


def _serialize_scene(scene: Scene) -> dict:
    d = _dataclass_to_dict(scene)
    if "source_reference" not in d:
        d["source_reference"] = _dataclass_to_dict(SourceReference())
    return d


def _parse_character(data: dict) -> Character:
    rels = [_parse_relationship(r) for r in data.pop("relationships", [])]
    return Character(relationships=rels, **_strip_extra(data, Character))


def _parse_act(data: dict) -> Act:
    sr_data = data.pop("scene_range", {})
    return Act(scene_range=SceneRange(**sr_data), **_strip_extra(data, Act))


def _parse_scene(data: dict) -> Scene:
    hd_data = data.pop("scene_heading", {})
    sr_data = data.pop("source_reference", {})
    beats_data = [_parse_beat(b) for b in data.pop("beats", [])]
    return Scene(
        scene_heading=SceneHeading(**hd_data),
        source_reference=SourceReference(**sr_data),
        beats=beats_data,
        **_strip_extra(data, Scene),
    )


def _parse_beat(data: dict) -> Beat:
    return Beat(**_strip_extra(data, Beat))


def _parse_relationship(data: dict) -> Relationship:
    return Relationship(**_strip_extra(data, Relationship))


def _parse_revision(data: dict) -> Revision:
    return Revision(**_strip_extra(data, Revision))
