#!/usr/bin/env python3
"""
AI 辅助剧本创作工具 — 小说文本转结构化剧本（YAML）

此为向后兼容入口，实际逻辑已迁移至 cli/main.py。
新代码请使用: python -m cli.main -i ./chapters -o ./output/script.yaml
           或: python -m api.main  (启动 Web API)

依赖: pip install openai pyyaml fastapi uvicorn
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

if __name__ == "__main__":
    from cli.main import main
    sys.exit(main())
