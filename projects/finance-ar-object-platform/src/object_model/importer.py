from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repository import connect


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_DB = PROJECT_ROOT / "examples" / "runtime" / "finance_ar.sqlite"
DEFAULT_INPUT = PROJECT_ROOT / "examples" / "raw-input" / "ar_lines.csv"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def object_id(*parts: str) -> str:
    return "::".join(part.strip().replace(" ", "_").lower() for part in parts)


def parse_amount(value: str) -> float:
    text = (value or "").strip()
    return round(float(text), 2) if text else 0.0


def read_lines(input_path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with input_path.open("r", encoding="utf-8", newline="") as f:
        for index, row in enumerate(csv.DictReader(f), start=1):
            rows.append(
                {
                    "source_row": index,
                    "entity_name": row["entity_name"].strip(),
                    "customer_name": row["customer_name"].strip(),
                    "source_doc_no": row["source_doc_no"].strip(),
                    "line_no": int(row["line_no"]),
                    "ar_amount": parse_amount(row["ar_amount"]),
                    "posting_date": row["posting_date"].strip(),
                    "writeoff_amount": parse_amount(row["writeoff_amount"]),
                    "ar_balance": parse_amount(row["ar_balance"]),
                    "description": row.get("description", "").strip(),
                }
            )
    return rows


def init_and_import(
    *,
    db_path: Path = DEFAULT_DB,
    input_path: Path = DEFAULT_INPUT,
    group_name: str = "DemoCorp Group",
    as_of_date: str = "2026-05-31",
    task_id: str = "task-demo-finance-ar-001",
) -> dict[str, Any]:
    timestamp = now()
    lines = read_lines(input_path)
    grouped: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for line in lines:
        grouped[(line["entity_name"], line["customer_name"], line["source_doc_no"])].append(line)

    with connect(db_path) as conn:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.execute("DELETE FROM ar_balance_fact_lines WHERE source_task_id = ?", (task_id,))
        conn.execute("DELETE FROM ar_balance_facts WHERE source_task_id = ?", (task_id,))
        conn.execute("DELETE FROM finance_business_objects")
        conn.execute("DELETE FROM finance_entities")
        conn.execute("DELETE FROM finance_groups")
        conn.execute("DELETE FROM process_tasks WHERE task_id = ?", (task_id,))
        group_id = "group-demo"
        conn.execute(
            "INSERT INTO finance_groups VALUES (?, ?, 'active', ?, ?, ?)",
            (group_id, group_name, '{"demo": true}', timestamp, timestamp),
        )
        conn.execute(
            """
            INSERT INTO process_tasks (
              task_id, task_type, status, input_file, as_of_date, summary_json, created_at, updated_at
            ) VALUES (?, 'import_ar_lines', 'success', ?, ?, ?, ?, ?)
            """,
            (
                task_id,
                str(input_path),
                as_of_date,
                json.dumps({"raw_line_count": len(lines)}, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        entity_ids: dict[str, str] = {}
        counterparty_ids: dict[tuple[str, str], str] = {}
        fact_count = 0
        fact_line_count = 0
        for (entity_name, customer_name, source_doc_no), doc_lines in grouped.items():
            entity_id = entity_ids.get(entity_name)
            if not entity_id:
                entity_id = object_id("entity", entity_name)
                entity_ids[entity_name] = entity_id
                conn.execute(
                    "INSERT INTO finance_entities VALUES (?, ?, ?, 'active', '{}', ?, ?)",
                    (entity_id, group_id, entity_name, timestamp, timestamp),
                )
            cp_key = (entity_name, customer_name)
            counterparty_id = counterparty_ids.get(cp_key)
            if not counterparty_id:
                counterparty_id = object_id("counterparty", entity_name, customer_name)
                counterparty_ids[cp_key] = counterparty_id
                conn.execute(
                    """
                    INSERT INTO finance_business_objects (
                      object_id, group_id, entity_id, parent_object_id, object_level, object_type,
                      object_key, object_name, customer_name, source_doc_no, status, metadata_json,
                      created_at, updated_at
                    ) VALUES (?, ?, ?, NULL, 'L3', 'counterparty', ?, ?, ?, NULL, 'active', '{}', ?, ?)
                    """,
                    (
                        counterparty_id,
                        group_id,
                        entity_id,
                        f"{entity_name}|{customer_name}",
                        customer_name,
                        customer_name,
                        timestamp,
                        timestamp,
                    ),
                )
            doc_id = object_id("document", entity_name, customer_name, source_doc_no)
            conn.execute(
                """
                INSERT INTO finance_business_objects (
                  object_id, group_id, entity_id, parent_object_id, object_level, object_type,
                  object_key, object_name, customer_name, source_doc_no, status, metadata_json,
                  created_at, updated_at
                ) VALUES (?, ?, ?, ?, 'L4', 'document', ?, ?, ?, ?, 'active', '{}', ?, ?)
                """,
                (
                    doc_id,
                    group_id,
                    entity_id,
                    counterparty_id,
                    f"{entity_name}|{customer_name}|{source_doc_no}",
                    source_doc_no,
                    customer_name,
                    source_doc_no,
                    timestamp,
                    timestamp,
                ),
            )
            balance = round(sum(line["ar_balance"] for line in doc_lines), 2)
            if balance == 0:
                continue
            fact_id = object_id("fact", doc_id, as_of_date)
            conn.execute(
                """
                INSERT INTO ar_balance_facts (
                  fact_id, object_id, group_id, entity_id, as_of_date, has_open_balance,
                  open_balance_amount, line_count, source_task_id, raw_summary_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fact_id,
                    doc_id,
                    group_id,
                    entity_id,
                    as_of_date,
                    balance,
                    len(doc_lines),
                    task_id,
                    json.dumps({"object_level_hit": True}, ensure_ascii=False),
                    timestamp,
                    timestamp,
                ),
            )
            fact_count += 1
            for line in doc_lines:
                conn.execute(
                    """
                    INSERT INTO ar_balance_fact_lines (
                      line_id, fact_id, object_id, group_id, entity_id, source_row, customer_name,
                      source_doc_no, ar_amount, posting_date, writeoff_amount, ar_balance,
                      description, raw_json, source_task_id, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        object_id("line", fact_id, str(line["source_row"])),
                        fact_id,
                        doc_id,
                        group_id,
                        entity_id,
                        line["source_row"],
                        customer_name,
                        source_doc_no,
                        line["ar_amount"],
                        line["posting_date"],
                        line["writeoff_amount"],
                        line["ar_balance"],
                        line["description"],
                        json.dumps(line, ensure_ascii=False),
                        task_id,
                        timestamp,
                        timestamp,
                    ),
                )
                fact_line_count += 1
        conn.execute(
            "UPDATE process_tasks SET summary_json = ?, updated_at = ? WHERE task_id = ?",
            (
                json.dumps(
                    {
                        "raw_line_count": len(lines),
                        "entity_count": len(entity_ids),
                        "counterparty_count": len(counterparty_ids),
                        "document_fact_count": fact_count,
                        "fact_line_count": fact_line_count,
                    },
                    ensure_ascii=False,
                ),
                timestamp,
                task_id,
            ),
        )
        conn.commit()
    return {
        "ok": True,
        "db": str(db_path),
        "task_id": task_id,
        "as_of_date": as_of_date,
        "raw_line_count": len(lines),
        "entity_count": len(entity_ids),
        "counterparty_count": len(counterparty_ids),
        "document_fact_count": fact_count,
        "fact_line_count": fact_line_count,
    }

