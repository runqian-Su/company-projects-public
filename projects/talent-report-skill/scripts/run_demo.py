#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from talent_report_skill.engine import DEFAULT_INSIGHT, DEFAULT_RESUME, DEFAULT_RUNTIME, compose_report, render_markdown, validate_report


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="猎头推荐报告 Skill 脱敏演示脚本")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME), help="运行输出目录")
    sub = parser.add_subparsers(dest="command", required=True)

    compose = sub.add_parser("compose", help="合成标准 report.json")
    compose.add_argument("--resume", default=str(DEFAULT_RESUME), help="合成 resume.raw.json")
    compose.add_argument("--insight", default=str(DEFAULT_INSIGHT), help="合成 insight.json")
    compose.add_argument("--target-position", default="Demo Operations Director", help="目标岗位；为空时推荐理由留空")

    validate = sub.add_parser("validate", help="校验 report.json")
    validate.add_argument("--report", default=None, help="report.json 路径；缺省时使用 runtime/report.json")

    render = sub.add_parser("render-preview", help="渲染 Markdown 预览")
    render.add_argument("--report", default=None, help="report.json 路径；缺省时使用 runtime/report.json")

    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir)

    if args.command == "compose":
        print_json(compose_report(Path(args.resume), Path(args.insight), args.target_position, runtime_dir))
        return
    if args.command == "validate":
        report = Path(args.report) if args.report else runtime_dir / "report.json"
        print_json(validate_report(report))
        return
    if args.command == "render-preview":
        report = Path(args.report) if args.report else runtime_dir / "report.json"
        print_json(render_markdown(report, runtime_dir))
        return


if __name__ == "__main__":
    main()

