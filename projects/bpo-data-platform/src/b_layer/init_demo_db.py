from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .repository import connect


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = Path(__file__).with_name("schema.sql")
DEFAULT_RUNTIME_DIR = PROJECT_ROOT / "examples" / "runtime"
DEFAULT_B_DB = DEFAULT_RUNTIME_DIR / "b_layer.sqlite"
DEFAULT_BA_META_DB = DEFAULT_RUNTIME_DIR / "ba_meta.sqlite"


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def init_b_db(db_path: Path = DEFAULT_B_DB) -> dict[str, Any]:
    timestamp = now()
    with connect(db_path) as conn:
        ensure_schema(conn)
        seed_project(conn, timestamp)
        conn.commit()
    return {"ok": True, "b_db": str(db_path)}


def ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def seed_project(conn: sqlite3.Connection, timestamp: str) -> None:
    conn.execute(
        """
        INSERT INTO projects (
          project_id, project_name, project_code, client_name, business_type,
          schema_version, status, metadata_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(project_id) DO UPDATE SET
          project_name = excluded.project_name,
          project_code = excluded.project_code,
          client_name = excluded.client_name,
          business_type = excluded.business_type,
          schema_version = excluded.schema_version,
          status = excluded.status,
          metadata_json = excluded.metadata_json,
          updated_at = excluded.updated_at
        """,
        (
            "demo_retail_ops",
            "DemoCorp 零售运营样例项目",
            "DEMO-RETAIL-OPS",
            "客户 A",
            "BPO 运营数据",
            "demo-1.0",
            "active",
            '{"demo": true, "description": "合成样例项目"}',
            timestamp,
            timestamp,
        ),
    )


def init_all(
    runtime_dir: Path = DEFAULT_RUNTIME_DIR,
    *,
    b_db_path: Path | None = None,
    ba_meta_db_path: Path | None = None,
) -> dict[str, Any]:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    b_db = b_db_path or runtime_dir / "b_layer.sqlite"
    ba_meta = ba_meta_db_path or runtime_dir / "ba_meta.sqlite"
    result = init_b_db(b_db)
    from src.a_layer.pipeline import run_a_to_b_pipeline
    from src.ba_layer.service import init_meta_db

    b_db.parent.mkdir(parents=True, exist_ok=True)
    ba_meta.parent.mkdir(parents=True, exist_ok=True)
    pipeline_result = run_a_to_b_pipeline(b_db_path=b_db)
    init_meta_db(ba_meta)
    result["ba_meta_db"] = str(ba_meta)
    result["a_to_b"] = pipeline_result
    return result
