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

from src.object_model.importer import DEFAULT_DB, DEFAULT_INPUT, init_and_import  # noqa: E402
from src.object_model.repository import (  # noqa: E402
    connect,
    query_counterparty_balances,
    query_document_balances,
    query_document_lines,
    query_entity_balances,
    query_summary,
    verify_consistency,
)


def print_json(payload: Any) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="财务应收对象库脱敏 Demo CLI")
    parser.add_argument("--db", default=str(DEFAULT_DB), help="SQLite 路径")
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init-db", help="初始化对象库并导入合成明细")
    init.add_argument("--input", default=str(DEFAULT_INPUT), help="合成 AR 明细 CSV")
    init.add_argument("--as-of-date", default="2026-05-31")
    for name in ("summary", "entity-balances", "counterparty-balances", "document-balances", "verify"):
        p = sub.add_parser(name)
        p.add_argument("--as-of-date", default="2026-05-31")
    lines = sub.add_parser("document-lines")
    lines.add_argument("--as-of-date", default="2026-05-31")
    lines.add_argument("--entity-name", required=True)
    lines.add_argument("--customer-name", required=True)
    lines.add_argument("--source-doc-no", required=True)
    return parser


def run(args: argparse.Namespace) -> Any:
    db = Path(args.db)
    if args.command == "init-db":
        return init_and_import(db_path=db, input_path=Path(args.input), as_of_date=args.as_of_date)
    with connect(db, readonly=True) as conn:
        if args.command == "summary":
            return query_summary(conn, args.as_of_date)
        if args.command == "entity-balances":
            return query_entity_balances(conn, args.as_of_date)
        if args.command == "counterparty-balances":
            return query_counterparty_balances(conn, args.as_of_date)
        if args.command == "document-balances":
            return query_document_balances(conn, args.as_of_date)
        if args.command == "document-lines":
            return query_document_lines(
                conn,
                args.as_of_date,
                entity_name=args.entity_name,
                customer_name=args.customer_name,
                source_doc_no=args.source_doc_no,
            )
        if args.command == "verify":
            return verify_consistency(conn, args.as_of_date)
    raise ValueError("未知命令。")


def main() -> int:
    try:
        print_json(run(build_parser().parse_args()))
        return 0
    except Exception as exc:
        print_json({"ok": False, "error": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

