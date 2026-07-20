from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.b_layer import init_demo_db


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RAW_INPUT_DIR = PROJECT_ROOT / "examples" / "raw-input"


class ALayerValidationError(ValueError):
    """A 层清洗校验失败。"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_a_to_b_pipeline(
    *,
    b_db_path: Path = init_demo_db.DEFAULT_B_DB,
    raw_input_dir: Path = DEFAULT_RAW_INPUT_DIR,
    task_id: str = "task-demo-a-to-b-001",
) -> dict[str, Any]:
    timestamp = now()
    raw_input_dir = Path(raw_input_dir)
    day_path = raw_input_dir / "raw_day_records.csv"
    person_path = raw_input_dir / "raw_person_day_records.json"
    if not day_path.exists():
        raise ALayerValidationError(f"缺少原始日数据输入：{day_path}")
    if not person_path.exists():
        raise ALayerValidationError(f"缺少原始个人日数据输入：{person_path}")

    day_records = load_day_csv(day_path)
    person_records = load_person_json(person_path)
    validate_records(day_records, person_records)

    with init_demo_db.connect(b_db_path) as conn:
        init_demo_db.ensure_schema(conn)
        init_demo_db.seed_project(conn, timestamp)
        write_task(conn, task_id, raw_input_dir, day_records, person_records, timestamp)
        write_source_file(conn, "source-demo-day-csv", task_id, day_path, "raw_day_csv", timestamp)
        write_source_file(conn, "source-demo-person-json", task_id, person_path, "raw_person_json", timestamp)
        write_day_facts(conn, task_id, day_records, timestamp)
        write_person_facts(conn, task_id, person_records, timestamp)
        conn.commit()
    return {
        "ok": True,
        "task_id": task_id,
        "b_db": str(b_db_path),
        "raw_input_dir": str(raw_input_dir),
        "day_count": len(day_records),
        "person_count": len(person_records),
    }


def load_day_csv(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            record = {
                "project_id": clean_text(row.get("project_id")),
                "date": clean_text(row.get("date")),
                "planned_headcount": parse_int(row.get("planned_headcount"), "planned_headcount"),
                "actual_headcount": parse_int(row.get("actual_headcount"), "actual_headcount"),
                "business_count": parse_int(row.get("business_count"), "business_count"),
                "quality_flags": parse_flags(row.get("quality_flags")),
                "note": clean_text(row.get("note")),
            }
            records.append(record)
    return records


def load_person_json(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ALayerValidationError("raw_person_day_records.json 必须是数组。")
    records: list[dict[str, Any]] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ALayerValidationError("个人日数据每一行必须是对象。")
        records.append(
            {
                "project_id": clean_text(item.get("project_id")),
                "date": clean_text(item.get("date")),
                "employee_id": clean_text(item.get("employee_id")),
                "employee_label": clean_text(item.get("employee_label")),
                "planned_hours": parse_float(item.get("planned_hours"), "planned_hours"),
                "actual_hours": parse_float(item.get("actual_hours"), "actual_hours"),
                "business_count": parse_int(item.get("business_count"), "business_count"),
                "quality_note": clean_text(item.get("quality_note")),
            }
        )
    return records


def validate_records(day_records: list[dict[str, Any]], person_records: list[dict[str, Any]]) -> None:
    if not day_records:
        raise ALayerValidationError("日数据不能为空。")
    if not person_records:
        raise ALayerValidationError("个人日数据不能为空。")
    seen_day: set[tuple[str, str]] = set()
    for row in day_records:
        require_project(row["project_id"])
        require_date(row["date"])
        key = (row["project_id"], row["date"])
        if key in seen_day:
            raise ALayerValidationError(f"日数据重复：{key}")
        seen_day.add(key)
        if row["actual_headcount"] > row["planned_headcount"]:
            row["quality_flags"] = sorted(set(row["quality_flags"] + ["actual_gt_planned"]))
    seen_person: set[tuple[str, str, str]] = set()
    valid_day_keys = set(seen_day)
    for row in person_records:
        require_project(row["project_id"])
        require_date(row["date"])
        if not row["employee_id"]:
            raise ALayerValidationError("employee_id 不能为空。")
        key = (row["project_id"], row["date"], row["employee_id"])
        if key in seen_person:
            raise ALayerValidationError(f"个人日数据重复：{key}")
        seen_person.add(key)
        if (row["project_id"], row["date"]) not in valid_day_keys:
            raise ALayerValidationError(f"个人日数据找不到对应日数据：{key}")
        if row["actual_hours"] > row["planned_hours"]:
            row["quality_note"] = append_note(row["quality_note"], "actual_hours_gt_planned")


def write_task(
    conn: sqlite3.Connection,
    task_id: str,
    raw_input_dir: Path,
    day_records: list[dict[str, Any]],
    person_records: list[dict[str, Any]],
    timestamp: str,
) -> None:
    conn.execute(
        """
        INSERT INTO process_tasks (
          task_id, project_id, task_type, status, input_summary, output_summary, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(task_id) DO UPDATE SET
          status = excluded.status,
          input_summary = excluded.input_summary,
          output_summary = excluded.output_summary,
          updated_at = excluded.updated_at
        """,
        (
            task_id,
            "demo_retail_ops",
            "a_to_b_fact_pipeline",
            "success",
            f"raw_input_dir={raw_input_dir}",
            f"day={len(day_records)}, person={len(person_records)}",
            timestamp,
            timestamp,
        ),
    )


def write_source_file(
    conn: sqlite3.Connection,
    file_id: str,
    task_id: str,
    path: Path,
    file_type: str,
    timestamp: str,
) -> None:
    conn.execute(
        """
        INSERT INTO source_files (
          file_id, project_id, task_id, file_type, file_name, file_hash,
          business_date, status, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(file_id) DO UPDATE SET
          task_id = excluded.task_id,
          file_hash = excluded.file_hash,
          status = excluded.status,
          metadata_json = excluded.metadata_json,
          updated_at = excluded.updated_at
        """,
        (
            file_id,
            "demo_retail_ops",
            task_id,
            file_type,
            path.name,
            file_hash(path),
            None,
            "processed",
            json.dumps({"synthetic": True, "source": "A 层合成输入"}, ensure_ascii=False),
            timestamp,
            timestamp,
        ),
    )


def write_day_facts(
    conn: sqlite3.Connection,
    task_id: str,
    records: list[dict[str, Any]],
    timestamp: str,
) -> None:
    for row in records:
        conn.execute(
            """
            INSERT INTO demo_day_records (
              project_id, record_date, planned_headcount, actual_headcount, business_count,
              quality_flags_json, note, source_task_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, record_date) DO UPDATE SET
              planned_headcount = excluded.planned_headcount,
              actual_headcount = excluded.actual_headcount,
              business_count = excluded.business_count,
              quality_flags_json = excluded.quality_flags_json,
              note = excluded.note,
              source_task_id = excluded.source_task_id,
              updated_at = excluded.updated_at
            """,
            (
                row["project_id"],
                row["date"],
                row["planned_headcount"],
                row["actual_headcount"],
                row["business_count"],
                json.dumps(row.get("quality_flags", []), ensure_ascii=False),
                row.get("note", ""),
                task_id,
                timestamp,
                timestamp,
            ),
        )


def write_person_facts(
    conn: sqlite3.Connection,
    task_id: str,
    records: list[dict[str, Any]],
    timestamp: str,
) -> None:
    for row in records:
        conn.execute(
            """
            INSERT INTO demo_person_day_records (
              project_id, record_date, employee_id, employee_label, planned_hours, actual_hours,
              business_count, quality_note, source_task_id, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, record_date, employee_id) DO UPDATE SET
              employee_label = excluded.employee_label,
              planned_hours = excluded.planned_hours,
              actual_hours = excluded.actual_hours,
              business_count = excluded.business_count,
              quality_note = excluded.quality_note,
              source_task_id = excluded.source_task_id,
              updated_at = excluded.updated_at
            """,
            (
                row["project_id"],
                row["date"],
                row["employee_id"],
                row["employee_label"],
                row["planned_hours"],
                row["actual_hours"],
                row["business_count"],
                row.get("quality_note", ""),
                task_id,
                timestamp,
                timestamp,
            ),
        )


def clean_text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def parse_int(value: Any, field: str) -> int:
    try:
        return int(str(value).strip())
    except Exception as exc:
        raise ALayerValidationError(f"{field} 必须是整数：{value}") from exc


def parse_float(value: Any, field: str) -> float:
    try:
        return float(str(value).strip())
    except Exception as exc:
        raise ALayerValidationError(f"{field} 必须是数字：{value}") from exc


def parse_flags(value: Any) -> list[str]:
    text = clean_text(value)
    if not text:
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def require_project(project_id: str) -> None:
    if project_id != "demo_retail_ops":
        raise ALayerValidationError(f"未知项目：{project_id}")


def require_date(value: str) -> None:
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ALayerValidationError(f"日期必须是 YYYY-MM-DD：{value}") from exc


def append_note(note: str, addition: str) -> str:
    return addition if not note else f"{note}; {addition}"

