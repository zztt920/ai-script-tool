"""剧本构建服务 — 将分析结果组装为结构化 Script 对象。

增强项：
- 风格感知的分幕结构（古装 4 幕、悬疑 5 幕等）
- 场景自动编号与来源追溯
"""

import logging
from datetime import datetime, timezone, timedelta

from domain.models import Script, Meta, Act, SceneRange
from domain.enums import GenreStyle, Language
from adapter.chapter_loader import ChapterData

log = logging.getLogger("service.script_builder")
LOCAL_TZ = timezone(timedelta(hours=8))

# 风格感知的分幕结构
_STYLE_ACT_STRUCTURES = {
    GenreStyle.SUSPENSE: [
        {"title": "谜面", "desc": "抛出核心悬疑，建立世界观与规则", "pct": 0.20, "fn": "悬念铺设"},
        {"title": "误导", "desc": "引入假线索与红鲱鱼，误导观众推理", "pct": 0.15, "fn": "信息混淆"},
        {"title": "追查", "desc": "角色深入调查，逐步接近真相", "pct": 0.25, "fn": "探索推进"},
        {"title": "反转", "desc": "关键证据曝光，颠覆此前认知", "pct": 0.20, "fn": "核心反转"},
        {"title": "真相", "desc": "揭开最终真相，收束所有伏笔", "pct": 0.20, "fn": "收束与余韵"},
    ],
    GenreStyle.ROMANCE: [
        {"title": "邂逅", "desc": "男女主初次相遇，建立初始关系", "pct": 0.20, "fn": "情感铺垫"},
        {"title": "试探", "desc": "情感萌芽，暧昧与拉扯", "pct": 0.25, "fn": "甜度积累"},
        {"title": "考验", "desc": "外部阻碍/误会引发情感危机", "pct": 0.25, "fn": "虐点爆发"},
        {"title": "奔赴", "desc": "破除障碍，双向奔赴", "pct": 0.30, "fn": "高甜结局"},
    ],
    GenreStyle.ACTION: [
        {"title": "觉醒", "desc": "平凡世界被打破，主角获得初始力量", "pct": 0.20, "fn": "世界观建立"},
        {"title": "闯关", "desc": "连续战斗与升级，建立对手关系", "pct": 0.30, "fn": "爽感累积"},
        {"title": "逆袭", "desc": "被逼入绝境后爆发，实现逆袭", "pct": 0.25, "fn": "燃点爆发"},
        {"title": "封神", "desc": "登顶巅峰，清算恩怨", "pct": 0.25, "fn": "最高爽感"},
    ],
    GenreStyle.COMEDY: [
        {"title": "离谱开局", "desc": "荒诞情境建立，角色反差登场", "pct": 0.20, "fn": "笑点建立"},
        {"title": "越搞越糟", "desc": "误会连环叠加，局势不断恶化", "pct": 0.30, "fn": "包袱叠加"},
        {"title": "神转折", "desc": "意料之外的反转，推翻所有认知", "pct": 0.20, "fn": "反转爆笑"},
        {"title": "圆满收场", "desc": "啼笑皆非的结局，各得其所", "pct": 0.30, "fn": "温馨收尾"},
    ],
    GenreStyle.HISTORICAL: [
        {"title": "入局", "desc": "角色进入权力场，初步了解规则", "pct": 0.20, "fn": "世界观展现"},
        {"title": "博弈", "desc": "多线权谋展开，结盟与背叛", "pct": 0.25, "fn": "权谋交织"},
        {"title": "翻覆", "desc": "关键事件导致势力重组，局势逆转", "pct": 0.25, "fn": "大局变动"},
        {"title": "定鼎", "desc": "最终对决，尘埃落定", "pct": 0.30, "fn": "结局高潮"},
    ],
    GenreStyle.FANTASY: [
        {"title": "入门", "desc": "主角踏入修仙之路，掌握基础功法", "pct": 0.15, "fn": "体系建立"},
        {"title": "筑基", "desc": "境界突破，初露锋芒", "pct": 0.25, "fn": "成长爽感"},
        {"title": "渡劫", "desc": "遭遇重大考验或天劫，生死一线", "pct": 0.25, "fn": "核心危机"},
        {"title": "飞升", "desc": "突破至高境界，超脱束缚", "pct": 0.20, "fn": "巅峰之战"},
        {"title": "开天", "desc": "开创属于自己的世界/秩序", "pct": 0.15, "fn": "圆满收束"},
    ],
    GenreStyle.URBAN: [
        {"title": "困局", "desc": "展示主角所处现实困境与社会身份", "pct": 0.22, "fn": "困境建立"},
        {"title": "挣扎", "desc": "主角在多条社会线索中周旋、应对", "pct": 0.28, "fn": "多层展开"},
        {"title": "抉择", "desc": "面对道德/利益/情感的重大抉择", "pct": 0.22, "fn": "核心冲突"},
        {"title": "破局", "desc": "找到突破口，重塑生活秩序", "pct": 0.28, "fn": "共鸣结局"},
    ],
    GenreStyle.SCI_FI: [
        {"title": "发现", "desc": "主角接触异常科技现象或未来世界", "pct": 0.20, "fn": "世界观建立"},
        {"title": "探索", "desc": "深入理解科技原理，揭示背后真相", "pct": 0.25, "fn": "逐步揭示"},
        {"title": "危机", "desc": "科技失控或伦理冲突爆发", "pct": 0.25, "fn": "核心危机"},
        {"title": "重生", "desc": "在科技与人性的交锋中达成新平衡", "pct": 0.30, "fn": "反思结局"},
    ],
    GenreStyle.HORROR: [
        {"title": "征兆", "desc": "异常现象初现，建立不安氛围", "pct": 0.18, "fn": "恐怖铺垫"},
        {"title": "升级", "desc": "恐怖源逐步显露，威胁持续升级", "pct": 0.27, "fn": "恐惧加深"},
        {"title": "崩溃", "desc": "角色心理防线被击穿，直面核心恐惧", "pct": 0.25, "fn": "极致恐惧"},
        {"title": "余悸", "desc": "表面平息，但暗示恐怖并未真正结束", "pct": 0.30, "fn": "余味与反噬"},
    ],
}


class ScriptBuilderService:
    """组装最终剧本，支持风格感知的分幕结构。"""

    def __init__(self, model_name: str = "deepseek-v4-flash"):
        self.model_name = model_name

    def build(self, chapters: list[ChapterData], overview: dict, all_scenes: list[dict],
              language: Language = Language.ZH) -> Script:
        now = datetime.now(LOCAL_TZ).isoformat()
        style = self._resolve_style(overview)
        is_en = (language == Language.EN)

        acts = self._build_acts(overview, all_scenes, style, language)

        adapter_name = "AI Script Assistant" if is_en else "AI 剧本助手"
        default_title = "Untitled Script" if is_en else "未命名剧本"

        meta = Meta(
            script_title=overview.get("script_title", default_title),
            original_novel=overview.get("original_novel", ""),
            original_author=overview.get("original_author", ""),
            adapter=f"{adapter_name} ({self.model_name})",
            script_version="0.1.0",
            created_at=now,
            updated_at=now,
            genre=overview.get("genre", []),
            script_type=overview.get("script_type", "tv_series"),
            total_scenes=len(all_scenes),
            total_episodes=overview.get("total_episodes", 1),
            target_audience=overview.get("target_audience", ""),
            synopsis=overview.get("synopsis", ""),
            theme_keywords=overview.get("theme_keywords", []),
            adaptation_notes=overview.get("adaptation_notes", ""),
        )

        script = Script(meta=meta, acts=acts)
        script.characters = overview.get("characters", [])
        script.scenes = self._renumber_scenes(all_scenes, chapters)

        from domain.models import Revision
        style_label = f" [{style.value}]" if style else ""
        revision_summary = (
            f"First draft generated by AI, {len(all_scenes)} scenes."
            if is_en else
            f"初稿{style_label}：由 AI 自动生成，共 {len(all_scenes)} 个场景。"
        )
        script.revisions = [
            Revision(
                version="0.1.0", timestamp=now,
                author=f"{adapter_name} ({self.model_name})",
                summary=revision_summary,
                changed_scenes=list(range(1, len(all_scenes) + 1)),
            )
        ]
        return script

    def _resolve_style(self, overview: dict) -> GenreStyle | None:
        """从 overview 解析风格。"""
        raw = overview.get("_style", "")
        if raw and raw != "auto":
            try:
                return GenreStyle(raw)
            except ValueError:
                pass
        return None

    def _build_acts(self, overview: dict, scenes: list[dict],
                    style: GenreStyle | None = None,
                    language: Language = Language.ZH) -> list[Act]:
        n = len(scenes) or 1

        # 优先使用风格感知的分幕结构
        if style and style in _STYLE_ACT_STRUCTURES:
            act_defs = _STYLE_ACT_STRUCTURES[style]
            acts = []
            cursor = 0
            for i, ad in enumerate(act_defs):
                title = self._localize_act_title(ad["title"], style.value, i, language)
                desc_text = ad["desc"]
                fn_text = ad["fn"]
                length = max(1, round(n * ad["pct"]))
                start = cursor + 1
                end = min(cursor + length, n)
                if i == len(act_defs) - 1:
                    end = n  # 确保最后一幕覆盖到底
                else:
                    end = max(end, start)  # 确保场景少时 start <= end
                acts.append(Act(
                    act_number=i + 1, title=title,
                    description=desc_text,
                    scene_range=SceneRange(start=start, end=end),
                    narrative_function=fn_text,
                ))
                cursor = end
            return acts

        # 使用 AI 分析出的幕结构
        raw_acts = overview.get("acts", [])
        if raw_acts:
            return [
                Act(
                    act_number=a.get("act_number", i + 1),
                    title=a.get("title", f"第{i+1}幕"),
                    description=a.get("description", ""),
                    scene_range=SceneRange(
                        start=a.get("scene_range_start", 1),
                        end=a.get("scene_range_end", n),
                    ),
                    narrative_function=a.get("narrative_function", ""),
                )
                for i, a in enumerate(raw_acts)
            ]

        # 经典三幕结构作为默认回退 — 跟随语言
        is_en = (language == Language.EN)
        third = max(1, n // 3)
        return [
            Act(1, "Setup" if is_en else "建置", 
                "Introduce world and core conflict" if is_en else "引入世界观与核心冲突",
                SceneRange(1, third), 
                "World-building & character intro" if is_en else "建置世界观、引入角色与冲突"),
            Act(2, "Confrontation" if is_en else "对抗", 
                "Conflict escalates, protagonist faces greatest challenge" if is_en else "冲突升级，角色面临最大挑战",
                SceneRange(third + 1, third * 2), 
                "Rising action & growth" if is_en else "冲突升级、角色成长"),
            Act(3, "Resolution" if is_en else "结局", 
                "Conflict resolved, story concludes" if is_en else "冲突解决，故事收束",
                SceneRange(third * 2 + 1, n), 
                "Climax & denouement" if is_en else "高潮与结局"),
        ]

    def _localize_act_title(self, title: str, style_value: str, idx: int,
                            language: Language) -> str:
        """根据语言返回分幕标题。"""
        if language != Language.EN:
            return title
        en_titles = {
            ("悬疑", 0): "The Mystery", ("悬疑", 1): "Misdirection", ("悬疑", 2): "The Hunt",
            ("悬疑", 3): "The Twist", ("悬疑", 4): "The Truth",
            ("甜宠", 0): "First Encounter", ("甜宠", 1): "Testing Waters",
            ("甜宠", 2): "Trial", ("甜宠", 3): "Together",
            ("热血", 0): "Awakening", ("热血", 1): "Trials",
            ("热血", 2): "Comeback", ("热血", 3): "Ascension",
            ("沙雕", 0): "Absurd Start", ("沙雕", 1): "Going Wrong",
            ("沙雕", 2): "Plot Twist", ("沙雕", 3): "Happy Ending",
            ("都市", 0): "Predicament", ("都市", 1): "Struggle",
            ("都市", 2): "Crossroads", ("都市", 3): "Breakthrough",
            ("古装", 0): "Entering the Game", ("古装", 1): "The Gambit",
            ("古装", 2): "Upheaval", ("古装", 3): "Coronation",
            ("仙侠", 0): "Initiation", ("仙侠", 1): "Foundation",
            ("仙侠", 2): "Tribulation", ("仙侠", 3): "Ascension", ("仙侠", 4): "Genesis",
            ("科幻", 0): "Discovery", ("科幻", 1): "Exploration",
            ("科幻", 2): "Crisis", ("科幻", 3): "Rebirth",
            ("惊悚", 0): "Omen", ("惊悚", 1): "Escalation",
            ("惊悚", 2): "Collapse", ("惊悚", 3): "Aftermath",
        }
        return en_titles.get((style_value, idx), title)

    def _renumber_scenes(self, scenes: list[dict], chapters: list) -> list[dict]:
        if not chapters:
            for i, scene in enumerate(scenes):
                scene["scene_id"] = i + 1
                for j, beat in enumerate(scene.get("beats", [])):
                    beat["beat_id"] = f"S{i + 1}_B{j + 1}"
            return scenes

        chapter_map = {ch.index: ch for ch in chapters}
        for i, scene in enumerate(scenes):
            new_id = i + 1
            scene["scene_id"] = new_id
            ch_idx = scene.pop("_chapter_index",
                               (new_id - 1) // max(1, len(scenes) // len(chapters)) + 1)
            if ch_idx in chapter_map:
                scene["source_reference"] = {
                    "novel_chapter": ch_idx,
                    "novel_chapter_title": chapter_map[ch_idx].title,
                    "excerpt": scene.get("source_reference", {}).get("excerpt", ""),
                }
            elif "source_reference" not in scene:
                scene["source_reference"] = {"novel_chapter": ch_idx, "novel_chapter_title": ""}
            scene.pop("scene_id_placeholder", None)
            for j, beat in enumerate(scene.get("beats", [])):
                beat["beat_id"] = f"S{new_id}_B{j + 1}"
        return scenes
