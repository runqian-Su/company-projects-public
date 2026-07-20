from __future__ import annotations

import os
import json
from pathlib import Path
from typing import Any, Literal

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from src.a_layer.pipeline import DEFAULT_RAW_INPUT_DIR, run_a_to_b_pipeline
from src.b_layer import repository as b_repo
from src.b_layer.init_demo_db import DEFAULT_BA_META_DB, DEFAULT_B_DB, init_all
from src.ba_layer import service as ba_service


PROJECT_ROOT = Path(__file__).resolve().parents[2]
B_DB = Path(os.environ.get("BPO_DEMO_B_DB", str(DEFAULT_B_DB)))
BA_META_DB = Path(os.environ.get("BPO_DEMO_BA_META_DB", str(DEFAULT_BA_META_DB)))

app = FastAPI(
    title="BPO 多层数据平台 Demo API",
    version="0.3.0",
    description="A/B/Ba/C 分层数据治理 Demo 的最小 FastAPI 实现。",
)


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    ok: bool
    data: Any = None
    error: ApiError | None = None


class ALayerRunRequest(BaseModel):
    project_id: str = "demo_retail_ops"
    raw_input_dir: str = Field(default=str(DEFAULT_RAW_INPUT_DIR))


class CreateBaTaskRequest(BaseModel):
    project_id: str = "demo_retail_ops"
    date_start: str
    date_end: str


class ChangeItem(BaseModel):
    record_key: dict[str, Any]
    field: str
    new_value: Any


class DiffRequest(BaseModel):
    dataset: Literal["day", "person"]
    changes: list[ChangeItem]


class ApplyRequest(BaseModel):
    dataset: Literal["day", "person"]
    diff_id: str
    reason: str


def ok(data: Any) -> dict[str, Any]:
    return {"ok": True, "data": data, "error": None}


def fail(message: str, *, code: str = "validation_error") -> dict[str, Any]:
    return {"ok": False, "data": None, "error": {"code": code, "message": message}}


def ensure_initialized() -> None:
    if not B_DB.exists() or not BA_META_DB.exists():
        init_all(B_DB.parent, b_db_path=B_DB, ba_meta_db_path=BA_META_DB)


@app.get("/api/health", response_model=ApiResponse)
def health() -> dict[str, Any]:
    return ok({"service": "bpo-data-platform-demo", "status": "ok"})


@app.post("/api/demo/init", response_model=ApiResponse)
def init_demo() -> dict[str, Any]:
    try:
        return ok(init_all(B_DB.parent, b_db_path=B_DB, ba_meta_db_path=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/projects", response_model=ApiResponse)
def projects() -> dict[str, Any]:
    try:
        ensure_initialized()
        with b_repo.connect(B_DB, readonly=True) as conn:
            return ok({"projects": b_repo.list_projects(conn)})
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/a-layer/run", response_model=ApiResponse)
def a_layer_run(payload: ALayerRunRequest) -> dict[str, Any]:
    try:
        if payload.project_id != "demo_retail_ops":
            return fail(f"未知项目：{payload.project_id}")
        return ok(run_a_to_b_pipeline(b_db_path=B_DB, raw_input_dir=Path(payload.raw_input_dir)))
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/b-layer/{project_id}/date-range", response_model=ApiResponse)
def b_date_range(project_id: str) -> dict[str, Any]:
    try:
        ensure_initialized()
        with b_repo.connect(B_DB, readonly=True) as conn:
            return ok(b_repo.date_range(conn, project_id))
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/b-layer/{project_id}/records", response_model=ApiResponse)
def b_records(
    project_id: str,
    dataset: Literal["day", "person"] = Query(...),
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict[str, Any]:
    try:
        ensure_initialized()
        with b_repo.connect(B_DB, readonly=True) as conn:
            if dataset == "day":
                records = b_repo.query_day_records(conn, project_id, date_start=date_start, date_end=date_end)
            else:
                records = b_repo.query_person_records(conn, project_id, date_start=date_start, date_end=date_end)
            return ok({"project_id": project_id, "dataset": dataset, "records": records})
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/ba/tasks", response_model=ApiResponse)
def ba_create_task(payload: CreateBaTaskRequest) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(
            ba_service.create_task_from_b(
                project_id=payload.project_id,
                date_start=payload.date_start,
                date_end=payload.date_end,
                b_db=B_DB,
                meta_db=BA_META_DB,
            )
        )
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/ba/tasks", response_model=ApiResponse)
def ba_tasks(project_id: str | None = None) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(ba_service.list_tasks(project_id, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/ba/tasks/{ba_task_id}/records", response_model=ApiResponse)
def ba_records(
    ba_task_id: str,
    dataset: Literal["day", "person"] = Query(...),
    date_start: str | None = None,
    date_end: str | None = None,
) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(
            ba_service.query_records(
                ba_task_id,
                dataset,
                date_start=date_start,
                date_end=date_end,
                meta_db=BA_META_DB,
            )
        )
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/ba/tasks/{ba_task_id}/editable", response_model=ApiResponse)
def ba_editable(ba_task_id: str, dataset: Literal["day", "person"] = Query(...)) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(ba_service.editable_schema(ba_task_id, dataset, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/ba/tasks/{ba_task_id}/diff", response_model=ApiResponse)
def ba_diff(ba_task_id: str, payload: DiffRequest) -> dict[str, Any]:
    try:
        ensure_initialized()
        changes = [item.dict() for item in payload.changes]
        return ok(ba_service.generate_diff(ba_task_id, payload.dataset, changes, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/ba/tasks/{ba_task_id}/apply", response_model=ApiResponse)
def ba_apply(ba_task_id: str, payload: ApplyRequest) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(
            ba_service.apply_diff(
                ba_task_id,
                payload.dataset,
                payload.diff_id,
                payload.reason,
                meta_db=BA_META_DB,
            )
        )
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/ba/tasks/{ba_task_id}/logs", response_model=ApiResponse)
def ba_logs(ba_task_id: str, limit: int = 100) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(ba_service.list_logs(ba_task_id, limit=limit, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/ba/tasks/{ba_task_id}/build", response_model=ApiResponse)
def ba_build(ba_task_id: str) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(ba_service.build_task(ba_task_id, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.post("/api/ba/tasks/{ba_task_id}/publish", response_model=ApiResponse)
def ba_publish(ba_task_id: str) -> dict[str, Any]:
    try:
        ensure_initialized()
        return ok(ba_service.publish_task(ba_task_id, meta_db=BA_META_DB))
    except Exception as exc:
        return fail(str(exc))


@app.get("/api/releases/{project_id}/current", response_model=ApiResponse)
def current_release(project_id: str) -> dict[str, Any]:
    try:
        ensure_initialized()
        with ba_service.connect_meta(BA_META_DB) as conn:
            row = conn.execute(
                "SELECT * FROM ba_release_registry WHERE project_id = ?",
                (project_id,),
            ).fetchone()
        if not row:
            return ok({"project_id": project_id, "current_release": None})
        return ok(
            {
                "project_id": project_id,
                "current_release": {
                    "ba_task_id": row["ba_task_id"],
                    "published_at": row["published_at"],
                    "release_summary": json.loads(row["release_summary_json"]),
                },
            }
        )
    except Exception as exc:
        return fail(str(exc))
