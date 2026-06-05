"""质量审核服务 — AI 对生成剧本进行多维审核，提供改进建议。

参考:
- Scriptify 的 6 维度质量检查系统
- InkOS 的反 AIGC 检测思路
"""

import json
import logging
from adapter.ai_client import AIClient
from domain.enums import AdaptationMode, GenreStyle, Language

log = logging.getLogger("service.quality_review")

# 各风格的质量检查重点
_STYLE_FOCUS = {
    GenreStyle.SUSPENSE: "反转设置是否到位、钩子是否有吸引力、信息释放节奏",
    GenreStyle.ROMANCE:  "甜度是否足够、CP感是否自然、情感递进是否合理",
    GenreStyle.ACTION:   "燃点密度是否够、逆袭爽感是否到位、战斗描写是否精彩",
    GenreStyle.COMEDY:   "笑点是否自然、神转折是否突兀、对话是否有趣",
    GenreStyle.URBAN:    "现实感是否强、情感共鸣是否到位、职场逻辑是否合理",
    GenreStyle.HISTORICAL: "权谋逻辑是否严谨、宫斗层次是否分明、古典感是否足",
    GenreStyle.FANTASY:  "修仙体系是否自洽、境界设定是否清晰、世界观是否宏大",
    GenreStyle.SCI_FI:   "科幻设定是否合理、科技与人性冲突是否深刻",
    GenreStyle.HORROR:   "恐怖氛围是否到位、节奏张弛是否得当、心理描写是否深入",
}


class QualityReviewService:
    """对生成的剧本执行多维度质量审核。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    def review(self, script_dict: dict, mode: AdaptationMode = AdaptationMode.DETAIL,
               style: GenreStyle | None = None, language: Language = Language.ZH) -> dict:
        """返回审核报告 {score, dimensions: [{name, score, comment}], suggestions}"""
        style_focus = _STYLE_FOCUS.get(style, "通用剧本质量标准") if style else "通用剧本质量标准"
        mode_label = {"fast": "快速审查", "detail": "深度审查", "hybrid": "框架审查"}.get(mode.value, "标准审查")

        lang_req = (
            "【语言要求 — 绝对强制】所有审核内容必须使用中文。维度名称、评语、建议、改进方案全部用中文。"
            "禁止出现任何英文。"
            if language == Language.ZH else
            "【LANGUAGE REQUIREMENT — ABSOLUTELY MANDATORY】Output ALL review content in English. "
            "Dimension names, comments, suggestions — everything in English. No Chinese characters."
        )

        prompt = f"""你是一位资深剧本审稿专家。请对以下 AI 生成的剧本初稿进行{mode_label}。

{lang_req}

【风格重点】
{style_focus}

【剧本摘要】
标题：{script_dict.get('meta', {}).get('script_title', '未知')}
类型：{script_dict.get('meta', {}).get('genre', [])}
角色数：{len(script_dict.get('characters', []))}
场景数：{script_dict.get('meta', {}).get('total_scenes', 0)}

【审核要求】
请从以下 6 个维度量化评分（1-10分），并给出具体建议：

1. **人物塑造**：角色是否立体、弧光是否完整、对话是否贴合人设
2. **情节结构**：冲突设计是否合理、节奏控制是否得当、伏笔回收是否到位
3. **对话质量**：台词是否自然、是否有"AI味"（过于工整/书面化/说教感）
4. **场景设计**：场景功能是否明确、视觉调度是否有层次
5. **情感张力**：高潮是否有力、情感层次是否丰富
6. **商业适配**：是否符合目标类型受众预期、爆点设置是否到位

返回 JSON：
```json
{{
  "total_score": 0,
  "grade": "A/B/C/D",
  "dimensions": [
    {{"name": "人物塑造", "score": 8, "comment": "优点：xxx。改进：xxx", "priority": "高/中/低"}},
    ...
  ],
  "top_strengths": ["亮点1", "亮点2"],
  "top_issues": ["问题1", "问题2"],
  "improvement_plan": "总体改进方案（200字内）",
  "ai_trace_level": "低/中/高",
  "ai_trace_notes": "AI痕迹说明"
}}
```"""

        result = self.ai.chat(prompt, "质量审核", language=language.value)
        if isinstance(result, dict):
            return result
        return {"total_score": 0, "grade": "N/A", "dimensions": [], "top_strengths": [], "top_issues": []}

    def anti_ai_polish_prompt(self, dialogue_lines: list[str], character_names: list[str]) -> str:
        """生成去AI味的润色提示词。"""
        chars = "、".join(character_names[:10])
        lines_preview = "\n".join(dialogue_lines[:20])
        return f"""请将以下台词做"去AI味"处理，使其更像真人对话：

【角色】{chars}

【原始台词】
{lines_preview}

处理规则：
1. 打破过于工整的句式，增加口语化表达
2. 适当加入语气词、省略、打断、重复等真实对话特征
3. 确保每个角色的语言风格差异化（不要所有角色说话都像一个模子）
4. 减少说教感和书面语，增加生活化的表达
5. 保留角色核心性格特征，不要改变角色人设

返回 JSON：{{"lines": ["润色后台词1", "润色后台词2", ...]}}"""
