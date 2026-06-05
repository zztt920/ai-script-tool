"""对话润色服务 — 按角色语言风格统一润色台词 + 去 AI 痕迹。

增强项（参考 Scriptify + InkOS）：
- 去 AI 味润色：打破过于工整的句式，增加口语化
- 角色语言风格差异化
- 保留角色核心人设
"""

import logging
from adapter.ai_client import AIClient
from domain.enums import Language

log = logging.getLogger("service.dialogue_polish")


class DialoguePolishService:
    """批量润色对话，确保角色语言风格一致，去除 AI 痕迹。"""

    def __init__(self, ai_client: AIClient):
        self.ai = ai_client

    def polish(self, dialogues: list[dict], character_map: dict,
               language: Language = Language.ZH) -> list[dict]:
        if not dialogues:
            return []

        char_context = "\n".join(
            f"{cid}: {info['name']}（{info.get('speech_style', '自然')}，{info.get('role_type', '')}）"
            for cid, info in character_map.items()
        )
        dialogue_text = "\n".join(
            f"[{d['character_id']}]（{d.get('emotion', '')}）：{d['content']}"
            for d in dialogues
        )

        lang_req = (
            "【语言要求】保持中文自然口语，使用地道中文表达，不要翻译腔。"
            if language == Language.ZH else
            "【LANGUAGE REQUIREMENT】Output polished dialogue in natural, conversational English. No Chinese characters."
        )

        prompt = f"""你是一位资深台词指导。请根据角色设定，润色以下对话。
{lang_req}

【角色语言风格】
{char_context}

【待润色对话】
{dialogue_text}

【润色规则 — 去 AI 味】
1. 打破过于工整/书面化的句式，真人不会每句话都那么完整
2. 适当加入打断、重复、省略、语气词（嗯/啊/吧/呢/嘛）等真实对话特征
3. 不同角色说话风格要有明显差异（不要所有人都是一个模子出来的）
4. 减少说教感和"总结式"发言
5. 短句优先，口语化优先
6. 保留角色核心性格，不要改变人设

返回 JSON 数组，每个元素为 {{"index": 原序号(从0开始), "content": "润色后的台词"}}。
只修改明显有 AI 痕迹或不符合角色风格的台词，保留原著中的精彩对白。"""

        result = self.ai.chat(prompt, "对话润色", language=language.value)
        if isinstance(result, list):
            for item in result:
                idx = item.get("index", -1)
                if 0 <= idx < len(dialogues):
                    dialogues[idx]["content"] = item.get("content", dialogues[idx]["content"])
        return dialogues
