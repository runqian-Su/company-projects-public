#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def fetch_json(api_base: str, path: str, query: dict[str, str] | None = None) -> dict[str, Any]:
    url = api_base.rstrip("/") + path
    if query:
        url += "?" + urllib.parse.urlencode(query)
    with urllib.request.urlopen(url, timeout=10) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if not payload.get("ok"):
        error = payload.get("error") or {}
        raise RuntimeError(error.get("message") or f"API 调用失败：{url}")
    return payload["data"]


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sync_meta (
          key TEXT PRIMARY KEY,
          value TEXT NOT NULL,
          updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS released_tasks (
          project_id TEXT PRIMARY KEY,
          ba_task_id TEXT NOT NULL,
          published_at TEXT,
          release_summary_json TEXT NOT NULL,
          synced_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS day_records (
          project_id TEXT NOT NULL,
          ba_task_id TEXT NOT NULL,
          record_date TEXT NOT NULL,
          planned_headcount INTEGER NOT NULL,
          actual_headcount INTEGER NOT NULL,
          business_count INTEGER NOT NULL,
          quality_flags_json TEXT NOT NULL,
          note TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (project_id, ba_task_id, record_date)
        );

        CREATE TABLE IF NOT EXISTS person_records (
          project_id TEXT NOT NULL,
          ba_task_id TEXT NOT NULL,
          record_date TEXT NOT NULL,
          employee_id TEXT NOT NULL,
          employee_label TEXT NOT NULL,
          planned_hours REAL NOT NULL,
          actual_hours REAL NOT NULL,
          business_count INTEGER NOT NULL,
          quality_note TEXT NOT NULL,
          updated_at TEXT NOT NULL,
          PRIMARY KEY (project_id, ba_task_id, record_date, employee_id)
        );
        """
    )


def sync_release(api_base: str, project_id: str, db_path: Path) -> dict[str, Any]:
    release_payload = fetch_json(api_base, f"/api/releases/{project_id}/current")
    current_release = release_payload.get("current_release")
    if not current_release:
        raise RuntimeError("当前项目没有已发布 Ba 任务，请先 build 并 publish。")
    ba_task_id = current_release["ba_task_id"]
    day_payload = fetch_json(
        api_base,
        f"/api/ba/tasks/{ba_task_id}/records",
        {"dataset": "day"},
    )
    person_payload = fetch_json(
        api_base,
        f"/api/ba/tasks/{ba_task_id}/records",
        {"dataset": "person"},
    )
    day_records = day_payload.get("records", [])
    person_records = person_payload.get("records", [])
    synced_at = now()
    with connect(db_path) as conn:
        ensure_schema(conn)
        conn.execute("DELETE FROM day_records WHERE project_id = ? AND ba_task_id = ?", (project_id, ba_task_id))
        conn.execute("DELETE FROM person_records WHERE project_id = ? AND ba_task_id = ?", (project_id, ba_task_id))
        conn.execute(
            """
            INSERT INTO released_tasks (
              project_id, ba_task_id, published_at, release_summary_json, synced_at
            ) VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
              ba_task_id = excluded.ba_task_id,
              published_at = excluded.published_at,
              release_summary_json = excluded.release_summary_json,
              synced_at = excluded.synced_at
            """,
            (
                project_id,
                ba_task_id,
                current_release.get("published_at"),
                json.dumps(current_release.get("release_summary", {}), ensure_ascii=False),
                synced_at,
            ),
        )
        for row in day_records:
            conn.execute(
                """
                INSERT INTO day_records (
                  project_id, ba_task_id, record_date, planned_headcount, actual_headcount,
                  business_count, quality_flags_json, note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    ba_task_id,
                    row["record_date"],
                    row["planned_headcount"],
                    row["actual_headcount"],
                    row["business_count"],
                    json.dumps(row.get("quality_flags", []), ensure_ascii=False),
                    row.get("note", ""),
                    row.get("updated_at", synced_at),
                ),
            )
        for row in person_records:
            conn.execute(
                """
                INSERT INTO person_records (
                  project_id, ba_task_id, record_date, employee_id, employee_label,
                  planned_hours, actual_hours, business_count, quality_note, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    project_id,
                    ba_task_id,
                    row["record_date"],
                    row["employee_id"],
                    row["employee_label"],
                    row["planned_hours"],
                    row["actual_hours"],
                    row["business_count"],
                    row.get("quality_note", ""),
                    row.get("updated_at", synced_at),
                ),
            )
        set_meta(conn, "last_project_id", project_id, synced_at)
        set_meta(conn, "last_ba_task_id", ba_task_id, synced_at)
        set_meta(conn, "last_synced_at", synced_at, synced_at)
        conn.commit()
    return {
        "ok": True,
        "project_id": project_id,
        "ba_task_id": ba_task_id,
        "db": str(db_path),
        "day_count": len(day_records),
        "person_count": len(person_records),
        "synced_at": synced_at,
    }


def set_meta(conn: sqlite3.Connection, key: str, value: str, updated_at: str) -> None:
    conn.execute(
        """
        INSERT INTO sync_meta (key, value, updated_at)
        VALUES (?, ?, ?)
        ON CONFLICT(key) DO UPDATE SET
          value = excluded.value,
          updated_at = excluded.updated_at
        """,
        (key, value, updated_at),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="同步当前已发布 Ba 任务到本地 SQLite 可视化池")
    parser.add_argument("--api-base", default="http://127.0.0.1:8787")
    parser.add_argument("--project", default="demo_retail_ops")
    parser.add_argument("--db", default="examples/runtime/client_visualization_pool.sqlite")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        print(json.dumps(sync_release(args.api_base, args.project, Path(args.db)), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

