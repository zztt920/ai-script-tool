"""章节文件加载器 — 从目录中读取小说章节文本。"""

import re
import logging
from pathlib import Path
from dataclasses import dataclass

log = logging.getLogger("adapter.chapter_loader")


@dataclass
class ChapterData:
    index: int
    title: str
    file: str
    content: str


class ChapterLoader:
    """从目录中加载小说章节文本。

    支持的文件命名约定：
      - 第X章.txt / chapter_01.txt / ch01.txt / 01.txt
    """

    CHAPTER_PATTERNS = [
        re.compile(r"第[\u4e00-\u9fff\d]+章", re.UNICODE),
        re.compile(r"chapter[_\s]*(\d+)", re.IGNORECASE),
        re.compile(r"ch[_\s]*(\d+)", re.IGNORECASE),
        re.compile(r"^(\d+)\.txt$"),
    ]

    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        if not self.input_dir.is_dir():
            raise FileNotFoundError(f"输入目录不存在: {self.input_dir}")

    def load(self) -> list[ChapterData]:
        """加载并排序所有章节，返回 ChapterData 列表。"""
        txt_files = sorted(self.input_dir.glob("*.txt"))
        if len(txt_files) < 3:
            raise ValueError(f"至少需要 3 个章节，当前仅找到 {len(txt_files)} 个 .txt 文件。")

        chapters = []
        for i, fp in enumerate(txt_files, start=1):
            raw = fp.read_text(encoding="utf-8").strip()
            if not raw:
                log.warning("跳过空文件: %s", fp.name)
                continue
            title = self._extract_title(fp.stem, raw)
            chapters.append(ChapterData(index=i, title=title, file=fp.name, content=raw))

        if len(chapters) < 3:
            raise ValueError(f"有效章节不足 3 个（当前 {len(chapters)}），无法继续。")

        log.info("成功加载 %d 个章节（共 %.1f 万字）",
                 len(chapters), sum(len(c.content) for c in chapters) / 10000)
        return chapters

    def _extract_title(self, stem: str, raw: str) -> str:
        for pat in self.CHAPTER_PATTERNS:
            m = pat.search(stem)
            if m:
                return m.group(0)
        first_line = raw.split("\n")[0].strip()
        return first_line[:40] if first_line else stem
