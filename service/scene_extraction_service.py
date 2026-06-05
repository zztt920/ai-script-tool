"""场景提取服务 — 将单个小说章节转换为剧本场景。

增强项：
- 中文优先提示词
- 适应三种创作模式（快/精/混）
- 风格感知的场景功能偏向
"""

import json
import logging
from adapter.ai_client import AIClient
from adapter.chapter_loader import ChapterData
from domain.enums import AdaptationMode, GenreStyle, Language

log = logging.getLogger("service.scene_extraction")


class SceneExtractionService:
    """从小说章节中提取剧本场景。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    def extract(
        self,
        chapter: ChapterData,
        characters: list[dict],
        mode: AdaptationMode = AdaptationMode.DETAIL,
        style: GenreStyle | None = None,
        language: Language = Language.ZH,
    ) -> list[dict]:
        """从单个章节中提取 2-5 个剧本场景。"""
        char_list = json.dumps(
            [{"id": c.get("character_id", ""), "name": c.get("name", ""),
              "role": c.get("role_type", ""), "speech": c.get("speech_style", "")}
             for c in characters], ensure_ascii=False)

        # 模式调整
        mode_instruction = {
            AdaptationMode.FAST:   "快速提取：每章 2-3 个核心场景，聚焦关键情节转折，对话精简。",
            AdaptationMode.DETAIL: "精细提取：每章 3-5 个场景，保留更多细节，内心戏尽量外化为动作/对话。",
            AdaptationMode.HYBRID: "框架提取：每章 2-4 个场景，给出场景骨架和关键 beats，细节标注 [待填充]。",
        }.get(mode, "标准提取")

        style_hint = ""
        if style:
            style_hint = f"【风格要求】{style.value}题材。{self._style_hint(style)}"

        lang_hint = (
            "【语言要求 — 绝对强制】所有输出必须全部是中文。场景概要、对话台词、情感基调、beat内容、" +
            "location(地点名)、time(如日/夜)全部使用中文。禁止出现任何英文单词。"
            if language == Language.ZH else
            "【LANGUAGE REQUIREMENT — ABSOLUTELY MANDATORY】Output ALL content in English. " +
            "Dialogue, scene summaries, emotional tones, beat content — everything in English. No Chinese characters."
        )

        prompt = f"""你是一位资深影视编剧。请将以下小说章节转换为剧本场景。

{mode_instruction}
{style_hint}
{lang_hint}

【已知角色】
{char_list}

【章节内容】
第{chapter.index}章《{chapter.title}》
{chapter.content[:4000]}

请将该章拆分为剧本场景，严格按以下 JSON 格式返回（仅返回 JSON 数组，不要有其他文字）：

```json
[
  {{
    "episode": 1,
    "scene_heading": {{"interior_exterior": "内", "location": "地点", "time": "日", "time_period": "古代/现代/未来"}},
    "summary": "场景概要（50字内，写清楚谁在什么情境下做了什么）",
    "scene_function": "推进主线",
    "emotional_tone": "情感基调",
    "tension_level": 5,
    "characters_present": ["CHAR_001"],
    "props": ["重要道具"],
    "beats": [
      {{"beat_id": "S{chapter.index}_B1", "beat_type": "dialogue", "character_id": "CHAR_001", "content": "具体台词或动作描述", "subtext": "潜台词（角色真正在想/在意的）", "emotion": "情绪状态", "parenthetical": "（动作指示）", "camera_hint": ""}}
    ],
    "transition": "切",
    "estimated_duration": "2min"
  }}
]
```

重要规则：
- beat_type: dialogue/action/description/voiceover/monologue/transition
- interior_exterior: 内/外
- time: 日/夜/傍晚/清晨/凌晨
- scene_function: 推进主线/发展感情/展示世界观/过渡/埋设伏笔/回收伏笔
- tension_level: 1（平静）到 10（极度紧张）
- 每个场景至少 3 个 beats
- 对话必须提供 character_id 和 parenthetical
- subtext（潜台词）很重要：写出角色真正在想什么、怕什么、想要什么"""

        result = self.ai.chat(prompt, f"场景提取-第{chapter.index}章", expect_list=True, language=language.value)
        return result if isinstance(result, list) else []

    @staticmethod
    def _style_hint(style: GenreStyle) -> str:
        hints = {
            GenreStyle.SUSPENSE:   '场景设计注重悬念铺设，每个场景都要有"信息差"——观众知道的比角色多，或角色知道的比观众多。',
            GenreStyle.ROMANCE:    "场景设计注重情感互动，尽可能创造双人封闭空间，让肢体语言和微表情传递情感。",
            GenreStyle.ACTION:     "场景设计注重节奏变化，文武交替。打斗场景要写出招式感和战术博弈。",
            GenreStyle.COMEDY:     "场景设计注重反差和误会，每个场景至少一个笑点。节奏要快，包袱要密。",
            GenreStyle.URBAN:      "场景设计注重现实感和细节真实度，职场/家庭/社交场景要有生活气息。",
            GenreStyle.HISTORICAL: "场景设计注重礼仪规制和身份等级，对话要有古代语感但不过度文言。",
            GenreStyle.FANTASY:    "场景设计注重修炼体系和世界观展示，战斗场景写出境界压制感。",
            GenreStyle.SCI_FI:     "场景设计注重未来感细节，科技设定在场景中自然融入。",
            GenreStyle.HORROR:     "场景设计注重视听恐怖，利用环境描写、声音暗示、镜头调度制造恐惧。",
        }
        return hints.get(style, "")
