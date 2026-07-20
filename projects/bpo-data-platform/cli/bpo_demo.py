#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.b_layer import repository as b_repo  # noqa: E402
from src.b_layer.init_demo_db import DEFAULT_BA_META_DB, DEFAULT_B_DB, init_all  # noqa: E402
from src.ba_layer import service as ba_service  # noqa: E402
from src.a_layer.pipeline import DEFAULT_RAW_INPUT_DIR, run_a_to_b_pipeline  # noqa: E402


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def read_patch(path: str) -> list[dict[str, Any]]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("changes"), list):
        return payload["changes"]
    raise ValueError("patch 文件必须是数组，或包含 changes 数组的对象。")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="BPO 多层数据平台脱敏 Demo CLI")
    parser.add_argument("--b-db", default=str(DEFAULT_B_DB), help="B 层 SQLite 路径")
    parser.add_argument("--ba-meta-db", default=str(DEFAULT_BA_META_DB), help="Ba 层元信息 SQLite 路径")
    sub = parser.add_subparsers(dest="scope", required=True)

    sub.add_parser("init-db", help="初始化 demo SQLite 和合成数据")

    a = sub.add_parser("a", help="A 层合成原始输入处理")
    a_sub = a.add_subparsers(dest="command", required=True)
    a_run = a_sub.add_parser("run", help="运行 A->B 合成事实处理管线")
    a_run.add_argument("--raw-input-dir", default=str(DEFAULT_RAW_INPUT_DIR), help="原始合成输入目录")

    b = sub.add_parser("b", help="B 层只读查询")
    b_sub = b.add_subparsers(dest="command", required=True)
    b_sub.add_parser("projects", help="查询项目列表")
    b_range = b_sub.add_parser("date-range", help="查询项目已入库日期范围")
    b_range.add_argument("--project", required=True)
    b_query = b_sub.add_parser("query", help="查询 B 层事实记录")
    b_query.add_argument("--project", required=True)
    b_query.add_argument("--dataset", choices=["day", "person"], required=True)
    b_query.add_argument("--date-start")
    b_query.add_argument("--date-end")

    ba = sub.add_parser("ba", help="Ba 层任务级受控操作")
    ba_sub = ba.add_subparsers(dest="command", required=True)
    create = ba_sub.add_parser("create-task", help="从 B 层复制事实并创建 Ba 任务")
    create.add_argument("--project", required=True)
    create.add_argument("--date-start", required=True)
    create.add_argument("--date-end", required=True)
    list_tasks = ba_sub.add_parser("list-tasks", help="列出 Ba 任务")
    list_tasks.add_argument("--project")
    query = ba_sub.add_parser("query", help="查询 Ba 任务内记录")
    add_task_dataset_args(query)
    query.add_argument("--date-start")
    query.add_argument("--date-end")
    editable = ba_sub.add_parser("editable", help="查看数据集可编辑字段")
    add_task_dataset_args(editable)
    diff = ba_sub.add_parser("diff", help="生成编辑预览，不写事实表")
    add_task_dataset_args(diff)
    diff.add_argument("--patch", required=True)
    apply = ba_sub.add_parser("apply", help="应用已预览 diff")
    add_task_dataset_args(apply)
    apply.add_argument("--diff-id", required=True)
    apply.add_argument("--reason", required=True)
    logs = ba_sub.add_parser("logs", help="查看编辑日志")
    logs.add_argument("--task", required=True)
    logs.add_argument("--limit", type=int, default=100)
    build = ba_sub.add_parser("build", help="执行 demo 构建")
    build.add_argument("--task", required=True)
    publish = ba_sub.add_parser("publish", help="发布已构建任务")
    publish.add_argument("--task", required=True)
    return parser


def add_task_dataset_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--task", required=True)
    parser.add_argument("--dataset", choices=["day", "person"], required=True)


def run(args: argparse.Namespace) -> Any:
    b_db = Path(args.b_db)
    ba_meta_db = Path(args.ba_meta_db)
    if args.scope == "init-db":
        return init_all(b_db.parent, b_db_path=b_db, ba_meta_db_path=ba_meta_db)
    if args.scope == "a":
        if args.command == "run":
            return run_a_to_b_pipeline(b_db_path=b_db, raw_input_dir=Path(args.raw_input_dir))
    if args.scope == "b":
        with b_repo.connect(b_db, readonly=True) as conn:
            if args.command == "projects":
                return {"ok": True, "projects": b_repo.list_projects(conn)}
            if args.command == "date-range":
                return {"ok": True, **b_repo.date_range(conn, args.project)}
            if args.command == "query":
                if args.dataset == "day":
                    records = b_repo.query_day_records(conn, args.project, date_start=args.date_start, date_end=args.date_end)
                else:
                    records = b_repo.query_person_records(conn, args.project, date_start=args.date_start, date_end=args.date_end)
                return {"ok": True, "project_id": args.project, "dataset": args.dataset, "records": records}
    if args.scope == "ba":
        if args.command == "create-task":
            return ba_service.create_task_from_b(
                project_id=args.project,
                date_start=args.date_start,
                date_end=args.date_end,
                b_db=b_db,
                meta_db=ba_meta_db,
            )
        if args.command == "list-tasks":
            return ba_service.list_tasks(args.project, meta_db=ba_meta_db)
        if args.command == "query":
            return ba_service.query_records(args.task, args.dataset, date_start=args.date_start, date_end=args.date_end, meta_db=ba_meta_db)
        if args.command == "editable":
            return ba_service.editable_schema(args.task, args.dataset, meta_db=ba_meta_db)
        if args.command == "diff":
            return ba_service.generate_diff(args.task, args.dataset, read_patch(args.patch), meta_db=ba_meta_db)
        if args.command == "apply":
            return ba_service.apply_diff(args.task, args.dataset, args.diff_id, args.reason, meta_db=ba_meta_db)
        if args.command == "logs":
            return ba_service.list_logs(args.task, limit=args.limit, meta_db=ba_meta_db)
        if args.command == "build":
            return ba_service.build_task(args.task, meta_db=ba_meta_db)
        if args.command == "publish":
            return ba_service.publish_task(args.task, meta_db=ba_meta_db)
    raise ValueError("未知命令。")


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        print_json(run(args))
        return 0
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
