"""AI API 客户端 — 封装 OpenAI 兼容 API 调用。"""

import re
import json
import time
import logging
from typing import Optional

log = logging.getLogger("adapter.ai_client")


class AIClient:
    """OpenAI 兼容 API 客户端，带重试和 JSON 修复。"""

    def __init__(self, api_key: str, api_base: str = "https://api.openai.com/v1",
                 model: str = "deepseek-v4-flash", temperature: float = 0.3,
                 max_tokens: int = 4096, request_delay: float = 1.0):
        self.api_key = api_key
        self.api_base = api_base
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.request_delay = request_delay
        self._client = None
        self._call_count = 0

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        return self._client

    def chat(self, prompt: str, task_name: str = "", expect_list: bool = False,
             language: str = "zh") -> dict | list:
        """调用 Chat Completion，返回解析后的 dict 或 list。

        Args:
            prompt: 用户 prompt
            task_name: 日志用任务名
            expect_list: 期望返回 JSON 数组。
            language: 输出语言 'zh' 或 'en'，影响系统提示。

        Returns:
            解析后的 dict 或 list，失败时返回 {} 或 []
        """
        if language == "en":
            system_prompt = (
                "You are an experienced screenwriter and script consultant, skilled in adapting novels "
                "into film/TV scripts. Your output must strictly follow the required JSON format. "
                "No extra explanations or Markdown markers. Output in English only."
            )
        else:
            system_prompt = (
                "你是一位经验丰富的影视编剧与剧本顾问，擅长将小说改编为电影/电视剧剧本。"
                "你的输出必须严格遵循要求的 JSON 格式，不要添加任何额外解释或 Markdown 标记。"
                "所有内容必须使用中文输出，禁止出现任何英文。"
            )

        extra_kwargs = {}
        if not expect_list:
            extra_kwargs["response_format"] = {"type": "json_object"}

        raw = ""
        for attempt in range(3):
            try:
                log.info("AI 调用中 [%s] 第 %d 次...", task_name, attempt + 1)
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                    **extra_kwargs,
                )
                self._call_count += 1
                raw = resp.choices[0].message.content.strip()
                data = json.loads(raw)
                time.sleep(self.request_delay)
                return data

            except json.JSONDecodeError:
                log.warning("JSON 解析失败，尝试从响应中提取...")
                if raw:
                    m = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw)
                    if m:
                        try:
                            data = json.loads(m.group(1))
                            time.sleep(self.request_delay)
                            return data
                        except json.JSONDecodeError:
                            pass
                if attempt == 2:
                    log.error("3 次尝试均失败，返回空结果。")
                    return {} if raw and raw.strip().startswith("{") else []

            except Exception as e:
                log.error("API 调用异常 [%s]: %s", task_name, str(e))
                if attempt < 2:
                    time.sleep(3 * (attempt + 1))
                else:
                    raise

        return {}
