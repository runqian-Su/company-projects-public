#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC_ROOT))

from tender_workflow.pipeline import DEFAULT_CLUSTER_INPUT, DEFAULT_RUNTIME, DEFAULT_V1_INPUT, load_json, run_v1, run_v2_cluster


def print_json(payload: object) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="招投标 Agent 编排脱敏 Demo CLI")
    parser.add_argument("--runtime-dir", default=str(DEFAULT_RUNTIME), help="运行报告输出目录")
    sub = parser.add_subparsers(dest="command", required=True)

    v1 = sub.add_parser("v1-run", help="运行 V1 多 Skill 编排 Demo")
    v1.add_argument("--input", default=str(DEFAULT_V1_INPUT), help="合成候选输入 JSON")

    v2 = sub.add_parser("v2-cluster", help="运行 V2 Agent 集群编排 Demo")
    v2.add_argument("--input", default=str(DEFAULT_CLUSTER_INPUT), help="合成 worker records JSON")

    sub.add_parser("show-samples", help="查看合成输入摘要")

    args = parser.parse_args()
    runtime_dir = Path(args.runtime_dir)

    if args.command == "v1-run":
        print_json(run_v1(Path(args.input), runtime_dir))
        return
    if args.command == "v2-cluster":
        print_json(run_v2_cluster(Path(args.input), runtime_dir))
        return
    if args.command == "show-samples":
        print_json(
            {
                "v1_candidates": load_json(DEFAULT_V1_INPUT),
                "cluster_worker_records": load_json(DEFAULT_CLUSTER_INPUT),
            }
        )
        return


if __name__ == "__main__":
    main()

