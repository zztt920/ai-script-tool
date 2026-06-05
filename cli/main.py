#!/usr/bin/env python3
"""
AI 辅助剧本创作工具 — CLI 入口

用法：
  python -m cli.main -i ./chapters -o ./output/script.yaml
  python -m cli.main -i ./chapters -o ./output/script.yaml --dry-run
  python -m cli.main -i ./chapters -o ./output/script.yaml -t "书名" -a "作者" -c config.yaml
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# 确保项目根目录在 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapter.ai_client import AIClient
from service.conversion_pipeline import ConversionPipeline
from domain.enums import Language, AdaptationMode, GenreStyle

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cli")


def build_config_from_file(config_path: str = None) -> dict:
    """从配置文件或环境变量构建 AIClient 参数。"""
    import yaml
    cfg = {
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "api_base": os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"),
        "model": os.getenv("OPENAI_MODEL", "deepseek-v4-flash"),
    }
    if config_path:
        p = Path(config_path)
        if p.exists():
            with open(p, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            cfg.update({k: v for k, v in data.items() if v})
    return cfg


def main():
    parser = argparse.ArgumentParser(
        description="AI 辅助剧本创作工具 — 将小说章节转换为结构化 YAML 剧本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""示例:
  python -m cli.main -i ./chapters -o ./output/script.yaml
  python -m cli.main -i ./chapters -o ./output/script.yaml -t "长安十二时辰" -a "马伯庸"
  python -m cli.main -i ./chapters -o ./output/script.yaml -c config.yaml
        """,
    )
    parser.add_argument("-i", "--input", required=True, help="小说章节目录（含 .txt 文件）")
    parser.add_argument("-o", "--output", default="./output/script.yaml", help="输出 YAML 路径")
    parser.add_argument("-c", "--config", default=None, help="配置文件路径（YAML）")
    parser.add_argument("-t", "--title", default="", help="原著小说标题")
    parser.add_argument("-a", "--author", default="", help="原著作者")
    parser.add_argument("-m", "--model", default=None, help="AI 模型名称（覆盖配置）")
    parser.add_argument("--lang", default="zh", choices=["zh", "en"], help="输出语言（默认: zh/中文）")
    parser.add_argument("--mode", default="detail", choices=["fast", "detail", "hybrid"],
                        help="改编模式: fast=快速/detail=精细/hybrid=混合（默认: detail）")
    parser.add_argument("--style", default=None,
                        choices=["悬疑", "甜宠", "热血", "沙雕", "都市", "古装", "仙侠", "科幻", "惊悚", "自动"],
                        help="风格模板（默认: 自动推断）")
    parser.add_argument("--no-review", action="store_true", help="跳过 AI 质量审核")
    parser.add_argument("--dry-run", action="store_true", help="仅加载章节，不调用 AI")
    parser.add_argument("--checkpoint-dir", default="./checkpoints", help="断点存储目录")

    args = parser.parse_args()

    # dry-run 模式：仅加载章节
    if args.dry_run:
        from adapter.chapter_loader import ChapterLoader
        loader = ChapterLoader(args.input)
        chapters = loader.load()
        for ch in chapters:
            print(f"  [{ch.index}] {ch.title} ({len(ch.content)} 字)")
        print(f"\n共 {len(chapters)} 章，可去掉 --dry-run 开始转换。")
        return 0

    # 构建配置
    cfg = build_config_from_file(args.config)
    if args.model:
        cfg["model"] = args.model
    if not cfg.get("api_key"):
        log.error("未设置 OPENAI_API_KEY，请通过环境变量或 -c 指定配置文件。")
        return 1

    # 创建 AI 客户端
    client = AIClient(
        api_key=cfg["api_key"],
        api_base=cfg["api_base"],
        model=cfg["model"],
        request_delay=cfg.get("request_delay", 1.0),
    )

    # 运行流水线
    pipeline = ConversionPipeline(client, checkpoint_dir=args.checkpoint_dir)
    lang = Language(args.lang)
    mode = AdaptationMode(args.mode)
    sty = GenreStyle(args.style) if args.style and args.style != "自动" else None
    try:
        result_path = pipeline.run(
            input_dir=args.input,
            output_path=args.output,
            title=args.title,
            author=args.author,
            language=lang,
            mode=mode,
            style=sty,
            enable_review=not args.no_review,
        )
        print(f"\n剧本已生成: {result_path}")
    except KeyboardInterrupt:
        log.warning("\n用户中断。断点已保存，下次运行自动恢复。")
        return 130
    except Exception as e:
        log.exception("转换过程出错: %s", str(e))
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
