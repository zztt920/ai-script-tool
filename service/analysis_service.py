"""全局分析服务 — 角色提取、类型判断、故事梗概、角色关系图。

增强项（参考 Scriptify + Toonflow + InkOS）：
- 中文优先提示词
- 风格模板感知（古装/悬疑/甜宠等 10 种风格不同的分析侧重）
- 角色关系图深度分析（动机链、冲突链、情感链）
"""

import json
import logging
from adapter.ai_client import AIClient
from adapter.chapter_loader import ChapterData
from domain.enums import Language, AdaptationMode, GenreStyle

log = logging.getLogger("service.analysis")

# 风格专用分析指引
_STYLE_GUIDE = {
    GenreStyle.SUSPENSE:   "重点关注：伏笔设置、信息不对称、反转节点、节奏控制。分析每个角色的秘密和谎言。",
    GenreStyle.ROMANCE:    "重点关注：感情线递进、CP 化学反应、甜度节点、虐点设置。分析角色间的吸引力来源和感情障碍。",
    GenreStyle.ACTION:     "重点关注：战力体系、升级路径、打斗场景分布、爽感节奏。分析主角成长线和反派压迫感。",
    GenreStyle.COMEDY:     "重点关注：笑点密度、反差萌设置、吐槽节奏。分析角色间的喜剧化学反应和包袱设计。",
    GenreStyle.URBAN:      "重点关注：现实逻辑、职场生态、社会议题映射。分析角色的社会身份和现实困境。",
    GenreStyle.HISTORICAL: "重点关注：权谋逻辑、派系划分、宫斗层次。分析角色间的利益关系和阵营博弈。",
    GenreStyle.FANTASY:    "重点关注：修仙体系、境界设定、宗门关系、天材地宝分布。分析角色的修炼路径和机缘设计。",
    GenreStyle.SCI_FI:     "重点关注：科幻设定的自洽性、科技伦理冲突。分析角色面对的科技困境和人性抉择。",
    GenreStyle.HORROR:     "重点关注：恐怖源设定、氛围铺垫、心理恐惧层次。分析角色的恐惧触发点和生存逻辑。",
}


class AnalysisService:
    """分析小说全局信息，支持语言选择、创作模式和风格模板。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    def analyze(
        self,
        chapters: list[ChapterData],
        language: Language = Language.ZH,
        mode: AdaptationMode = AdaptationMode.DETAIL,
        style: GenreStyle | None = None,
    ) -> dict:
        """分析整部小说，返回 overview dict。"""
        # 构建章节摘要上下文
        chapter_summaries = []
        for ch in chapters:
            preview = ch.content[:1500]
            if len(ch.content) > 2000:
                preview += f"\n...（省略 {len(ch.content)-2000} 字）...\n"
                preview += ch.content[-500:]
            chapter_summaries.append(f"第{ch.index}章《{ch.title}》：\n{preview}")

        full_context = "\n\n---\n\n".join(chapter_summaries)

        # 风格分析指南
        style_guide = _STYLE_GUIDE.get(style, "通用分析：全面梳理角色、情节、世界观。") if style else "通用分析：全面梳理角色、情节、世界观。"

        # 模式对分析深度的要求
        mode_detail = {
            AdaptationMode.FAST:   "快速分析，聚焦核心角色（5-8个）和主线冲突即可",
            AdaptationMode.DETAIL: "深度分析，覆盖所有有名角色，详细梳理关系和动机",
            AdaptationMode.HYBRID: "框架分析，给出角色骨架和关系拓扑，具体细节留待人工填充",
        }.get(mode, "标准分析")

        lang_hint = (
            "【语言要求 — 绝对强制】所有输出必须全部使用中文。角色名字必须是中文名（如'苏慕'而非'Su Mu'）。"
            "地点名用中文。类型标签用中文（如'悬疑'而非'Suspense'）。故事梗概用中文。"
            "分幕标题和描述用中文。所有字段值全部是中文。禁止出现任何英文单词。禁止中英混杂。"
            if language == Language.ZH else
            "【LANGUAGE REQUIREMENT — ABSOLUTELY MANDATORY】Output ALL content in English. "
            "Character names, locations, genres, synopses, act titles — everything in English. "
            "Do NOT output any Chinese characters at all."
        )

        prompt = f"""你是一位资深影视编剧和文学分析师。请仔细阅读以下小说章节内容，完成全局分析。

【分析模式】{mode_detail}
【风格指引】{style_guide}
【语言要求】{lang_hint}

【小说章节内容】
{full_context[:12000]}

请严格按以下 JSON 格式返回分析结果（不要输出其他内容，确保 JSON 可直接解析）：

```json
{{
  "genre": ["类型1", "类型2"],
  "script_type": "tv_series",
  "target_audience": "目标受众描述（年龄段+偏好）",
  "synopsis": "300-500字的故事梗概，涵盖核心冲突、主要人物关系、关键转折",
  "theme_keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
  "tone": "整体基调描述（如：悬疑冷峻、轻松甜宠、热血燃情）",
  "adaptation_notes": "从小说到剧本的改编策略（100-200字），包括：哪些情节需要压缩、哪些需要放大、哪些内心戏需要外化",
  "characters": [
    {{
      "character_id": "CHAR_001",
      "name": "角色名",
      "aliases": [],
      "role_type": "主角",
      "gender": "男",
      "age_range": "25-30",
      "occupation": "职业",
      "importance": 10,
      "physical_description": "外貌特征",
      "personality_traits": ["特征1", "特征2", "特征3"],
      "background": "角色背景故事",
      "motivation": "核心动机",
      "arc_summary": "角色弧光总结",
      "speech_style": "语言风格（如：沉稳简练、话多跳脱、咬文嚼字）",
      "secrets": "角色隐藏的秘密（如有）",
      "relationships": [
        {{"target_character_id": "CHAR_002", "relation_type": "师徒", "description": "xx是yy的师父，但暗中对yy的家族秘密有所察觉", "conflict_level": 7, "relationship_arc": "从信任到背叛再到和解"}}
      ]
    }}
  ],
  "acts": [
    {{"act_number": 1, "title": "幕标题", "description": "幕描述（50字）", "narrative_function": "叙事功能", "scene_range_start": 1, "scene_range_end": 10, "key_turning_points": ["关键转折1"]}}
  ]
}}
```

重要规则：
- character_id 使用 CHAR_001, CHAR_002... 递增
- role_type：主角、反派、配角、客串
- importance：1（路人）到 10（绝对核心）
- relation_type：师徒、父子/母子、恋人、朋友、仇敌、上下级、利益同盟、暗恋、竞争对手、守护、背叛等
- relationship_arc：关系发展弧线（如：从敌对到同盟）
- conflict_level：冲突等级，1（和谐）到 10（你死我活）
- 角色关系必须成对标注（A→B 和 B→A 各有独立描述）"""

        result = self.ai.chat(prompt, "全局分析", language=language.value)
        return result if isinstance(result, dict) else {}
