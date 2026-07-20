#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from proposal_skill.engine import DEFAULT_DECK, DEFAULT_RUNTIME, inspect_registries, render_demo, validate_deck


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="方案生成 Skill 脱敏演示脚本")
    parser.add_argument("--deck", default=str(DEFAULT_DECK), help="deck JSON 路径")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME), help="运行输出目录")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate", help="校验 deck、资产、模板和章节一致性")
    sub.add_parser("render-demo", help="渲染 HTML 预览并生成 render report")
    sub.add_parser("inspect", help="查看内建 registry 摘要")

    args = parser.parse_args()
    deck = Path(args.deck)
    runtime_dir = Path(args.runtime_dir)

    if args.command == "validate":
        print_json(validate_deck(deck))
        return
    if args.command == "render-demo":
        print_json(render_demo(deck, runtime_dir))
        return
    if args.command == "inspect":
        print_json(inspect_registries())
        return


if __name__ == "__main__":
    main()

