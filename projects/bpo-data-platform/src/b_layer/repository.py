from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any


def connect(db_path: Path, *, readonly: bool = False) -> sqlite3.Connection:
    db_path = Path(db_path)
    if readonly:
        uri = f"file:{db_path.resolve()}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _loads(value: str) -> Any:
    return json.loads(value) if value else None


def _rows(cursor: sqlite3.Cursor) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for row in cursor.fetchall():
        item = dict(row)
        for key in ("metadata_json", "quality_flags_json", "summary_json"):
            if key in item:
                item[key.replace("_json", "")] = _loads(item.pop(key))
        result.append(item)
    return result


def list_projects(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    return _rows(
        conn.execute(
            """
            SELECT project_id, project_name, project_code, client_name, business_type,
                   schema_version, status, metadata_json, created_at, updated_at
            FROM projects
            ORDER BY project_id
            """
        )
    )


def get_project(conn: sqlite3.Connection, project_id: str) -> dict[str, Any] | None:
    rows = _rows(
        conn.execute(
            """
            SELECT project_id, project_name, project_code, client_name, business_type,
                   schema_version, status, metadata_json, created_at, updated_at
            FROM projects
            WHERE project_id = ?
            """,
            (project_id,),
        )
    )
    return rows[0] if rows else None


def date_range(conn: sqlite3.Connection, project_id: str) -> dict[str, Any]:
    day = conn.execute(
        "SELECT MIN(record_date) AS date_start, MAX(record_date) AS date_end, COUNT(*) AS row_count "
        "FROM demo_day_records WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    person = conn.execute(
        "SELECT MIN(record_date) AS date_start, MAX(record_date) AS date_end, COUNT(*) AS row_count "
        "FROM demo_person_day_records WHERE project_id = ?",
        (project_id,),
    ).fetchone()
    return {
        "project_id": project_id,
        "day": dict(day),
        "person": dict(person),
    }


def query_day_records(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    date_start: str | None = None,
    date_end: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM demo_day_records WHERE project_id = ?"
    params: list[Any] = [project_id]
    if date_start:
        sql += " AND record_date >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND record_date <= ?"
        params.append(date_end)
    sql += " ORDER BY record_date"
    return _rows(conn.execute(sql, params))


def query_person_records(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    date_start: str | None = None,
    date_end: str | None = None,
) -> list[dict[str, Any]]:
    sql = "SELECT * FROM demo_person_day_records WHERE project_id = ?"
    params: list[Any] = [project_id]
    if date_start:
        sql += " AND record_date >= ?"
        params.append(date_start)
    if date_end:
        sql += " AND record_date <= ?"
        params.append(date_end)
    sql += " ORDER BY record_date, employee_id"
    return _rows(conn.execute(sql, params))

