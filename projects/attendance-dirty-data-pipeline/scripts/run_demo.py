#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from attendance_pipeline.pipeline import (
    DEFAULT_IDENTITY_RULES,
    DEFAULT_PUNCH_LOGS,
    DEFAULT_RUNTIME,
    DEFAULT_SPECIAL_STATES,
    load_samples,
    run_pipeline,
)


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="考勤脏数据处理脱敏演示脚本")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME), help="运行报告输出目录")
    sub = parser.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="运行完整脏数据处理 Demo")
    run.add_argument("--punch-logs", default=str(DEFAULT_PUNCH_LOGS), help="合成打卡 CSV")
    run.add_argument("--special-states", default=str(DEFAULT_SPECIAL_STATES), help="合成请假/外出 CSV")
    run.add_argument("--identity-rules", default=str(DEFAULT_IDENTITY_RULES), help="合成身份规则 JSON")

    sub.add_parser("show-samples", help="查看合成输入")

    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir)

    if args.command == "run":
        print_json(
            run_pipeline(
                punch_logs=Path(args.punch_logs),
                special_states=Path(args.special_states),
                identity_rules=Path(args.identity_rules),
                runtime_dir=runtime_dir,
            )
        )
        return
    if args.command == "show-samples":
        print_json(load_samples())
        return


if __name__ == "__main__":
    main()
