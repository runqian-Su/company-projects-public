from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from src.b_layer import repository as b_repo
from src.b_layer.init_demo_db import DEFAULT_B_DB, DEFAULT_BA_META_DB


PROJECT_ROOT = Path(__file__).resolve().parents[2]
META_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
EDITABLE_FIELDS = {
    "day": {"planned_headcount": "INTEGER", "note": "TEXT"},
    "person": {"actual_hours": "REAL", "quality_note": "TEXT"},
}
DATASET_TABLES = {
    "day": "demo_day_records",
    "person": "demo_person_day_records",
}


class BaDemoError(ValueError):
    """可展示给 CLI 用户的 Ba 层治理错误。"""


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def utc_from_iso(value: str) -> datetime:
    return datetime.fromisoformat(value)


def connect_meta(meta_db: Path = DEFAULT_BA_META_DB) -> sqlite3.Connection:
    meta_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(meta_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def connect_task(task_db: Path) -> sqlite3.Connection:
    task_db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(task_db)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_meta_db(meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    with connect_meta(meta_db) as conn:
        conn.executescript(META_SCHEMA_PATH.read_text(encoding="utf-8"))
        conn.commit()
    return {"ok": True, "ba_meta_db": str(meta_db)}


def ensure_task_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS demo_day_records (
          project_id TEXT NOT NULL,
          record_date TEXT NOT NULL,
          planned_headcount INTEGER NOT NULL,
          actual_headcount INTEGER NOT NULL,
          business_count INTEGER NOT NULL,
          quality_flags_json TEXT NOT NULL DEFAULT '[]',
          note TEXT NOT NULL DEFAULT '',
          source_task_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (project_id, record_date)
        );

        CREATE TABLE IF NOT EXISTS demo_person_day_records (
          project_id TEXT NOT NULL,
          record_date TEXT NOT NULL,
          employee_id TEXT NOT NULL,
          employee_label TEXT NOT NULL,
          planned_hours REAL NOT NULL,
          actual_hours REAL NOT NULL,
          business_count INTEGER NOT NULL,
          quality_note TEXT NOT NULL DEFAULT '',
          source_task_id TEXT NOT NULL,
          created_at TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (project_id, record_date, employee_id)
        );

        CREATE TABLE IF NOT EXISTS ba_pending_diffs (
          diff_id TEXT PRIMARY KEY,
          dataset TEXT NOT NULL,
          patch_json TEXT NOT NULL,
          preview_json TEXT NOT NULL,
          status TEXT NOT NULL,
          created_at TEXT NOT NULL,
          expires_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ba_edit_logs (
          log_id TEXT PRIMARY KEY,
          diff_id TEXT NOT NULL,
          dataset TEXT NOT NULL,
          reason TEXT NOT NULL,
          changes_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ba_build_runs (
          build_id TEXT PRIMARY KEY,
          status TEXT NOT NULL,
          input_summary_json TEXT NOT NULL,
          started_at TEXT NOT NULL,
          finished_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ba_publish_runs (
          publish_id TEXT PRIMARY KEY,
          build_id TEXT NOT NULL,
          status TEXT NOT NULL,
          release_summary_json TEXT NOT NULL,
          published_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS ba_task_state (
          state_id INTEGER PRIMARY KEY CHECK (state_id = 1),
          fact_revision INTEGER NOT NULL,
          build_revision INTEGER NOT NULL,
          current_build_id TEXT,
          published_build_id TEXT,
          updated_at TEXT NOT NULL
        );
        """
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO ba_task_state (
          state_id, fact_revision, build_revision, current_build_id, published_build_id, updated_at
        ) VALUES (1, 0, -1, NULL, NULL, ?)
        """,
        (now(),),
    )


def create_task_from_b(
    *,
    project_id: str,
    date_start: str,
    date_end: str,
    b_db: Path = DEFAULT_B_DB,
    meta_db: Path = DEFAULT_BA_META_DB,
) -> dict[str, Any]:
    init_meta_db(meta_db)
    task_id = f"ba-{project_id}-{uuid.uuid4().hex[:10]}"
    task_db = Path(meta_db).parent / "tasks" / task_id / "ba.sqlite"
    timestamp = now()
    with b_repo.connect(b_db, readonly=True) as b_conn:
        project = b_repo.get_project(b_conn, project_id)
        if not project:
            raise BaDemoError(f"项目不存在：{project_id}")
        day_rows = b_repo.query_day_records(b_conn, project_id, date_start=date_start, date_end=date_end)
        person_rows = b_repo.query_person_records(b_conn, project_id, date_start=date_start, date_end=date_end)
        if not day_rows and not person_rows:
            raise BaDemoError("指定日期范围没有可复制的 B 层事实数据。")
        source_snapshot = {
            "b_db": str(b_db),
            "project_id": project_id,
            "date_start": date_start,
            "date_end": date_end,
            "day_count": len(day_rows),
            "person_count": len(person_rows),
            "copied_at": timestamp,
        }

    with connect_task(task_db) as task_conn:
        ensure_task_schema(task_conn)
        for row in day_rows:
            task_conn.execute(
                """
                INSERT INTO demo_day_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["project_id"],
                    row["record_date"],
                    row["planned_headcount"],
                    row["actual_headcount"],
                    row["business_count"],
                    json.dumps(row["quality_flags"], ensure_ascii=False),
                    row["note"],
                    row["source_task_id"],
                    row["created_at"],
                    timestamp,
                ),
            )
        for row in person_rows:
            task_conn.execute(
                """
                INSERT INTO demo_person_day_records VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    row["project_id"],
                    row["record_date"],
                    row["employee_id"],
                    row["employee_label"],
                    row["planned_hours"],
                    row["actual_hours"],
                    row["business_count"],
                    row["quality_note"],
                    row["source_task_id"],
                    row["created_at"],
                    timestamp,
                ),
            )
        task_conn.commit()

    with connect_meta(meta_db) as meta_conn:
        meta_conn.execute(
            """
            INSERT INTO ba_tasks (
              ba_task_id, project_id, task_name, date_start, date_end, status, b_db_path,
              ba_db_path, source_snapshot_json, current_build_id, published_at, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (
                task_id,
                project_id,
                f"{project_id} 操作任务 {date_start} 至 {date_end}",
                date_start,
                date_end,
                "editing",
                str(b_db),
                str(task_db),
                json.dumps(source_snapshot, ensure_ascii=False),
                timestamp,
                timestamp,
            ),
        )
        meta_conn.commit()

    return {"ok": True, "ba_task_id": task_id, "source_snapshot": source_snapshot, "ba_db": str(task_db)}


def list_tasks(project_id: str | None = None, meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    init_meta_db(meta_db)
    sql = "SELECT * FROM ba_tasks"
    params: list[Any] = []
    if project_id:
        sql += " WHERE project_id = ?"
        params.append(project_id)
    sql += " ORDER BY created_at DESC"
    with connect_meta(meta_db) as conn:
        rows = [task_row_to_dict(row) for row in conn.execute(sql, params).fetchall()]
    return {"ok": True, "tasks": rows}


def task_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["source_snapshot"] = json.loads(item.pop("source_snapshot_json"))
    return item


def get_task(task_id: str, meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    init_meta_db(meta_db)
    with connect_meta(meta_db) as conn:
        row = conn.execute("SELECT * FROM ba_tasks WHERE ba_task_id = ?", (task_id,)).fetchone()
    if not row:
        raise BaDemoError(f"Ba 任务不存在：{task_id}")
    return task_row_to_dict(row)


def query_records(
    task_id: str,
    dataset: str,
    *,
    date_start: str | None = None,
    date_end: str | None = None,
    meta_db: Path = DEFAULT_BA_META_DB,
) -> dict[str, Any]:
    table = table_for_dataset(dataset)
    task = get_task(task_id, meta_db)
    sql = f"SELECT * FROM {table} WHERE project_id = ?"
    params: list[Any] = [task["project_id"]]
    if date_start:
        sql += " AND record_date >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND record_date <= ?"
        params.append(date_end)
    sql += " ORDER BY record_date"
    if dataset == "person":
        sql += ", employee_id"
    with connect_task(Path(task["ba_db_path"])) as conn:
        rows = [normalize_row(dict(row)) for row in conn.execute(sql, params).fetchall()]
    return {"ok": True, "ba_task_id": task_id, "dataset": dataset, "records": rows}


def editable_schema(task_id: str, dataset: str, meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    get_task(task_id, meta_db)
    if dataset not in EDITABLE_FIELDS:
        raise BaDemoError(f"未知数据集：{dataset}")
    keys = ["record_date"] if dataset == "day" else ["record_date", "employee_id"]
    return {"ok": True, "ba_task_id": task_id, "dataset": dataset, "record_key": keys, "editable_fields": EDITABLE_FIELDS[dataset]}


def generate_diff(
    task_id: str,
    dataset: str,
    changes: list[dict[str, Any]],
    meta_db: Path = DEFAULT_BA_META_DB,
) -> dict[str, Any]:
    if not changes:
        raise BaDemoError("patch 不能为空。")
    table = table_for_dataset(dataset)
    task = get_task(task_id, meta_db)
    diff_id = f"diff-{uuid.uuid4().hex[:16]}"
    created_at = now()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=30)).replace(microsecond=0).isoformat()
    preview: list[dict[str, Any]] = []
    with connect_task(Path(task["ba_db_path"])) as conn:
        for change in changes:
            field = change.get("field")
            if field not in EDITABLE_FIELDS[dataset]:
                raise BaDemoError(f"字段不可编辑：{field}")
            record = fetch_record(conn, table, dataset, task["project_id"], change.get("record_key", {}))
            old_value = record[field]
            new_value = change.get("new_value")
            preview.append(
                {
                    "record_key": change.get("record_key", {}),
                    "field": field,
                    "old_value": old_value,
                    "new_value": new_value,
                    "will_change": old_value != new_value,
                }
            )
        conn.execute(
            """
            INSERT INTO ba_pending_diffs (
              diff_id, dataset, patch_json, preview_json, status, created_at, expires_at
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                diff_id,
                dataset,
                json.dumps(changes, ensure_ascii=False),
                json.dumps(preview, ensure_ascii=False),
                created_at,
                expires_at,
            ),
        )
        conn.commit()
    return {"ok": True, "ba_task_id": task_id, "dataset": dataset, "diff_id": diff_id, "expires_at": expires_at, "preview": preview}


def apply_diff(
    task_id: str,
    dataset: str,
    diff_id: str,
    reason: str,
    meta_db: Path = DEFAULT_BA_META_DB,
) -> dict[str, Any]:
    if not reason.strip():
        raise BaDemoError("apply 必须提供修改原因。")
    table = table_for_dataset(dataset)
    task = get_task(task_id, meta_db)
    timestamp = now()
    with connect_task(Path(task["ba_db_path"])) as conn:
        diff = conn.execute(
            "SELECT * FROM ba_pending_diffs WHERE diff_id = ? AND dataset = ?",
            (diff_id, dataset),
        ).fetchone()
        if not diff:
            raise BaDemoError("diff_id 无效。")
        if diff["status"] != "pending":
            raise BaDemoError("diff 已被使用或失效。")
        if utc_from_iso(diff["expires_at"]) < datetime.now(timezone.utc):
            raise BaDemoError("diff 已过期，请重新执行 diff。")
        changes = json.loads(diff["patch_json"])
        applied: list[dict[str, Any]] = []
        for change in changes:
            record_key = change.get("record_key", {})
            field = change["field"]
            record = fetch_record(conn, table, dataset, task["project_id"], record_key)
            old_value = record[field]
            new_value = change.get("new_value")
            update_record(conn, table, dataset, task["project_id"], record_key, field, new_value, timestamp)
            applied.append({"record_key": record_key, "field": field, "old_value": old_value, "new_value": new_value})
        log_id = f"edit-{uuid.uuid4().hex[:16]}"
        conn.execute(
            """
            INSERT INTO ba_edit_logs (log_id, diff_id, dataset, reason, changes_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (log_id, diff_id, dataset, reason, json.dumps(applied, ensure_ascii=False), timestamp),
        )
        conn.execute("UPDATE ba_pending_diffs SET status = 'applied' WHERE diff_id = ?", (diff_id,))
        conn.execute(
            """
            UPDATE ba_task_state
            SET fact_revision = fact_revision + 1, current_build_id = NULL, updated_at = ?
            WHERE state_id = 1
            """,
            (timestamp,),
        )
        conn.commit()
    with connect_meta(meta_db) as meta_conn:
        meta_conn.execute(
            "UPDATE ba_tasks SET status = 'editing', current_build_id = NULL, updated_at = ? WHERE ba_task_id = ?",
            (timestamp, task_id),
        )
        meta_conn.commit()
    return {"ok": True, "ba_task_id": task_id, "dataset": dataset, "log_id": log_id, "applied": applied}


def list_logs(
    task_id: str,
    *,
    limit: int = 100,
    meta_db: Path = DEFAULT_BA_META_DB,
) -> dict[str, Any]:
    task = get_task(task_id, meta_db)
    with connect_task(Path(task["ba_db_path"])) as conn:
        rows = []
        for row in conn.execute("SELECT * FROM ba_edit_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall():
            item = dict(row)
            item["changes"] = json.loads(item.pop("changes_json"))
            rows.append(item)
    return {"ok": True, "ba_task_id": task_id, "logs": rows}


def build_task(task_id: str, meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    task = get_task(task_id, meta_db)
    timestamp = now()
    build_id = f"build-{uuid.uuid4().hex[:16]}"
    with connect_task(Path(task["ba_db_path"])) as conn:
        day_count = conn.execute("SELECT COUNT(*) FROM demo_day_records").fetchone()[0]
        person_count = conn.execute("SELECT COUNT(*) FROM demo_person_day_records").fetchone()[0]
        state = conn.execute("SELECT fact_revision FROM ba_task_state WHERE state_id = 1").fetchone()
        summary = {"day_count": day_count, "person_count": person_count, "fact_revision": state["fact_revision"]}
        conn.execute(
            """
            INSERT INTO ba_build_runs (build_id, status, input_summary_json, started_at, finished_at)
            VALUES (?, 'success', ?, ?, ?)
            """,
            (build_id, json.dumps(summary, ensure_ascii=False), timestamp, timestamp),
        )
        conn.execute(
            """
            UPDATE ba_task_state
            SET build_revision = fact_revision, current_build_id = ?, updated_at = ?
            WHERE state_id = 1
            """,
            (build_id, timestamp),
        )
        conn.commit()
    with connect_meta(meta_db) as meta_conn:
        meta_conn.execute(
            "UPDATE ba_tasks SET status = 'built', current_build_id = ?, updated_at = ? WHERE ba_task_id = ?",
            (build_id, timestamp, task_id),
        )
        meta_conn.commit()
    return {"ok": True, "ba_task_id": task_id, "build_id": build_id, "summary": summary}


def publish_task(task_id: str, meta_db: Path = DEFAULT_BA_META_DB) -> dict[str, Any]:
    task = get_task(task_id, meta_db)
    timestamp = now()
    publish_id = f"publish-{uuid.uuid4().hex[:16]}"
    with connect_task(Path(task["ba_db_path"])) as conn:
        state = conn.execute("SELECT * FROM ba_task_state WHERE state_id = 1").fetchone()
        if not state["current_build_id"]:
            raise BaDemoError("发布失败：当前任务尚未成功 build。")
        if state["build_revision"] != state["fact_revision"]:
            raise BaDemoError("发布失败：build 已过期，请重新 build。")
        summary = {
            "project_id": task["project_id"],
            "ba_task_id": task_id,
            "build_id": state["current_build_id"],
            "date_start": task["date_start"],
            "date_end": task["date_end"],
        }
        conn.execute(
            """
            INSERT INTO ba_publish_runs (publish_id, build_id, status, release_summary_json, published_at)
            VALUES (?, ?, 'published', ?, ?)
            """,
            (publish_id, state["current_build_id"], json.dumps(summary, ensure_ascii=False), timestamp),
        )
        conn.execute(
            "UPDATE ba_task_state SET published_build_id = ?, updated_at = ? WHERE state_id = 1",
            (state["current_build_id"], timestamp),
        )
        conn.commit()
    with connect_meta(meta_db) as meta_conn:
        meta_conn.execute(
            "UPDATE ba_tasks SET status = 'published', published_at = ?, updated_at = ? WHERE ba_task_id = ?",
            (timestamp, timestamp, task_id),
        )
        meta_conn.execute(
            """
            INSERT INTO ba_release_registry (project_id, ba_task_id, published_at, release_summary_json)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
              ba_task_id = excluded.ba_task_id,
              published_at = excluded.published_at,
              release_summary_json = excluded.release_summary_json
            """,
            (task["project_id"], task_id, timestamp, json.dumps(summary, ensure_ascii=False)),
        )
        meta_conn.commit()
    return {"ok": True, "ba_task_id": task_id, "publish_id": publish_id, "release_summary": summary}


def table_for_dataset(dataset: str) -> str:
    if dataset not in DATASET_TABLES:
        raise BaDemoError(f"未知数据集：{dataset}")
    return DATASET_TABLES[dataset]


def fetch_record(
    conn: sqlite3.Connection,
    table: str,
    dataset: str,
    project_id: str,
    record_key: dict[str, Any],
) -> sqlite3.Row:
    if dataset == "day":
        record_date = record_key.get("record_date") or record_key.get("date")
        row = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? AND record_date = ?",
            (project_id, record_date),
        ).fetchone()
    else:
        record_date = record_key.get("record_date") or record_key.get("date")
        row = conn.execute(
            f"SELECT * FROM {table} WHERE project_id = ? AND record_date = ? AND employee_id = ?",
            (project_id, record_date, record_key.get("employee_id")),
        ).fetchone()
    if not row:
        raise BaDemoError(f"记录不存在：{record_key}")
    return row


def update_record(
    conn: sqlite3.Connection,
    table: str,
    dataset: str,
    project_id: str,
    record_key: dict[str, Any],
    field: str,
    new_value: Any,
    timestamp: str,
) -> None:
    record_date = record_key.get("record_date") or record_key.get("date")
    if dataset == "day":
        conn.execute(
            f"UPDATE {table} SET {field} = ?, updated_at = ? WHERE project_id = ? AND record_date = ?",
            (new_value, timestamp, project_id, record_date),
        )
    else:
        conn.execute(
            f"UPDATE {table} SET {field} = ?, updated_at = ? WHERE project_id = ? AND record_date = ? AND employee_id = ?",
            (new_value, timestamp, project_id, record_date, record_key.get("employee_id")),
        )


def normalize_row(row: dict[str, Any]) -> dict[str, Any]:
    if "quality_flags_json" in row:
        row["quality_flags"] = json.loads(row.pop("quality_flags_json"))
    return row
