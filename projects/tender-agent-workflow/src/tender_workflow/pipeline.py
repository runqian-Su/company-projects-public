from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_V1_INPUT = PROJECT_ROOT / "examples" / "sample-data" / "v1_candidates.json"
DEFAULT_CLUSTER_INPUT = PROJECT_ROOT / "examples" / "sample-data" / "cluster_worker_records.json"
DEFAULT_RUNTIME = PROJECT_ROOT / "examples" / "runtime"

TARGET_SERVICE_KEYWORDS = {
    "outsourcing": 30,
    "staffing": 30,
    "bpo": 30,
    "customer service": 20,
    "field operation": 20,
    "payroll": 20,
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(name: str, payload: dict[str, Any], runtime_dir: Path = DEFAULT_RUNTIME) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output = runtime_dir / name
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def stable_key(record: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(record.get("buyer", "")).strip().lower(),
            str(record.get("project_name", "")).strip().lower(),
            str(record.get("deadline", "")).strip(),
        ]
    )
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]


def hard_gate(candidate: dict[str, Any]) -> tuple[bool, list[str]]:
    title = str(candidate.get("title", "")).lower()
    detail = str(candidate.get("detail_text", "")).lower()
    text = f"{title}\n{detail}"
    flags: list[str] = []

    if not any(keyword in text for keyword in TARGET_SERVICE_KEYWORDS):
        flags.append("service_type_not_matched")
    if "budget:" not in detail:
        flags.append("budget_missing")
    if "deadline:" not in detail:
        flags.append("deadline_missing")
    if "project name:" not in detail:
        flags.append("project_name_missing")

    return not flags, flags


def extract_field(detail_text: str, label: str) -> str | None:
    marker = f"{label}:"
    start = detail_text.find(marker)
    if start < 0:
        return None
    value_start = start + len(marker)
    value_end = detail_text.find(".", value_start)
    if value_end < 0:
        value_end = len(detail_text)
    return detail_text[value_start:value_end].strip()


def extract_record(candidate: dict[str, Any], gate_flags: list[str]) -> dict[str, Any]:
    detail = str(candidate.get("detail_text", ""))
    budget_raw = extract_field(detail, "Budget")
    try:
        budget = float(budget_raw) if budget_raw else None
    except ValueError:
        budget = None

    record = {
        "record_id": candidate["candidate_id"],
        "title": candidate.get("title"),
        "buyer": str(candidate.get("title", "Demo Buyer")).split(" customer")[0].split(" field")[0].strip(),
        "project_name": extract_field(detail, "Project name"),
        "service_type": extract_field(detail, "Service type"),
        "budget": budget,
        "region": extract_field(detail, "Region"),
        "deadline": extract_field(detail, "Deadline"),
        "source": candidate.get("source"),
        "source_url": candidate.get("url"),
        "quality_flags": list(gate_flags),
    }
    for field in ["project_name", "service_type", "budget", "deadline"]:
        if record.get(field) in (None, ""):
            record["quality_flags"].append(f"{field}_missing")
    return record


def score_record(record: dict[str, Any]) -> dict[str, Any]:
    text = f"{record.get('title', '')} {record.get('service_type', '')}".lower()
    score = 0
    reasons: list[str] = []
    for keyword, points in TARGET_SERVICE_KEYWORDS.items():
        if keyword in text:
            score += points
            reasons.append(f"matched:{keyword}")
    if record.get("budget") and record["budget"] >= 1_000_000:
        score += 15
        reasons.append("budget_above_demo_threshold")
    if record.get("quality_flags"):
        score -= 20
        reasons.append("quality_flags_penalty")

    priority = "high" if score >= 55 else "medium" if score >= 30 else "low"
    enriched = dict(record)
    enriched.update({"match_score": score, "priority": priority, "match_reasons": reasons})
    return enriched


def run_v1(input_path: Path = DEFAULT_V1_INPUT, runtime_dir: Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    candidates = load_json(input_path)
    gated: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for candidate in candidates:
        passed, flags = hard_gate(candidate)
        if passed:
            gated.append(extract_record(candidate, flags))
        else:
            rejected.append(
                {
                    "candidate_id": candidate.get("candidate_id"),
                    "title": candidate.get("title"),
                    "reject_flags": flags,
                }
            )

    analyzed = [score_record(record) for record in gated]
    push_preview = [
        {
            "title": item["title"],
            "project_name": item["project_name"],
            "priority": item["priority"],
            "match_score": item["match_score"],
            "deadline": item["deadline"],
        }
        for item in sorted(analyzed, key=lambda row: row["match_score"], reverse=True)
    ]

    report = {
        "pipeline": "v1_multi_skill",
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "candidate_count": len(candidates),
        "passed_gate_count": len(gated),
        "rejected_count": len(rejected),
        "records": analyzed,
        "rejected": rejected,
        "push_preview": push_preview,
    }
    output = write_report(f"v1_pipeline_report_{now_stamp()}.json", report, runtime_dir)
    report["report_path"] = display_path(output)
    return report


def run_v2_cluster(input_path: Path = DEFAULT_CLUSTER_INPUT, runtime_dir: Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    worker_records: dict[str, list[dict[str, Any]]] = load_json(input_path)
    merged: dict[str, dict[str, Any]] = {}
    duplicates: list[dict[str, Any]] = []
    worker_summary: dict[str, Any] = {}

    for worker, records in worker_records.items():
        worker_summary[worker] = {"status": "success", "record_count": len(records)}
        for record in records:
            key = stable_key(record)
            enriched = score_record(record)
            enriched["worker"] = worker
            enriched["dedupe_key"] = key
            if key in merged:
                duplicates.append(
                    {
                        "dedupe_key": key,
                        "kept_record_id": merged[key]["record_id"],
                        "dropped_record_id": record["record_id"],
                        "dropped_worker": worker,
                    }
                )
                continue
            merged[key] = enriched

    final_records = sorted(merged.values(), key=lambda row: row["match_score"], reverse=True)
    report = {
        "pipeline": "v2_agent_cluster",
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "worker_summary": worker_summary,
        "worker_count": len(worker_records),
        "raw_record_count": sum(len(records) for records in worker_records.values()),
        "final_record_count": len(final_records),
        "duplicate_count": len(duplicates),
        "duplicates": duplicates,
        "final_records": final_records,
        "delivery_preview": [
            {
                "project_name": item["project_name"],
                "buyer": item["buyer"],
                "priority": item["priority"],
                "match_score": item["match_score"],
                "worker": item["worker"],
            }
            for item in final_records
        ],
    }
    output = write_report(f"v2_cluster_report_{now_stamp()}.json", report, runtime_dir)
    report["report_path"] = display_path(output)
    return report
