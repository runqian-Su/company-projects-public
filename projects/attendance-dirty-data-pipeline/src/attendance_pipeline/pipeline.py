from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime, time, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PUNCH_LOGS = PROJECT_ROOT / "examples" / "sample-data" / "punch_logs_dirty.csv"
DEFAULT_SPECIAL_STATES = PROJECT_ROOT / "examples" / "sample-data" / "special_states.csv"
DEFAULT_IDENTITY_RULES = PROJECT_ROOT / "examples" / "sample-data" / "identity_rules.json"
DEFAULT_RUNTIME = PROJECT_ROOT / "examples" / "runtime"


@dataclass
class Employee:
    employee_id: str
    canonical_name: str
    department: str
    aliases: list[str]


@dataclass
class DayBucket:
    employee: Employee
    work_date: date
    punches: list[time] = field(default_factory=list)
    sources: set[str] = field(default_factory=set)
    special_state: str | None = None
    special_reason: str | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)


def normalize_name(value: str | None) -> str:
    return " ".join((value or "").strip().split()).lower()


def load_identity_rules(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    employees = [Employee(**item) for item in raw["employees"]]
    by_id = {item.employee_id: item for item in employees}
    by_alias: dict[str, Employee] = {}
    for employee in employees:
        by_alias[normalize_name(employee.canonical_name)] = employee
        for alias in employee.aliases:
            by_alias[normalize_name(alias)] = employee
    return {
        "employees": employees,
        "by_id": by_id,
        "by_alias": by_alias,
        "whitelist": set(raw.get("whitelist_employee_ids", [])),
        "work_start": parse_time(raw.get("work_start", "09:00")),
        "work_end": parse_time(raw.get("work_end", "18:00")),
    }


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    cleaned = value.strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(value: str | None) -> time | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            return datetime.strptime(cleaned, fmt).time()
        except ValueError:
            continue
    return None


def issue(code: str, message: str, row: dict[str, Any] | None = None) -> dict[str, Any]:
    payload: dict[str, Any] = {"code": code, "message": message}
    if row is not None:
        payload["row"] = row
    return payload


def resolve_employee(row: dict[str, str], rules: dict[str, Any]) -> tuple[Employee | None, dict[str, Any] | None]:
    employee_id = (row.get("employee_id") or "").strip()
    name = row.get("name") or ""
    if employee_id and employee_id in rules["by_id"]:
        return rules["by_id"][employee_id], None
    if normalize_name(name) in rules["by_alias"]:
        return rules["by_alias"][normalize_name(name)], None
    return None, issue("unknown_identity", "无法通过工号或姓名别名识别员工", row)


def build_special_state_index(rows: list[dict[str, str]], rules: dict[str, Any]) -> tuple[dict[tuple[str, date], dict[str, str]], list[dict[str, Any]]]:
    states: dict[tuple[str, date], dict[str, str]] = {}
    issues: list[dict[str, Any]] = []
    for row in rows:
        employee, identity_issue = resolve_employee(row, rules)
        work_date = parse_date(row.get("date"))
        if identity_issue:
            issues.append(identity_issue)
            continue
        if work_date is None:
            issues.append(issue("invalid_date", "特殊状态日期无法解析", row))
            continue
        states[(employee.employee_id, work_date)] = {
            "state": (row.get("state") or "").strip(),
            "reason": (row.get("reason") or "").strip(),
        }
    return states, issues


def apply_punch_rows(rows: list[dict[str, str]], rules: dict[str, Any]) -> tuple[dict[tuple[str, date], DayBucket], list[dict[str, Any]]]:
    buckets: dict[tuple[str, date], DayBucket] = {}
    issues: list[dict[str, Any]] = []
    whitelist = rules["whitelist"]

    for row in rows:
        employee, identity_issue = resolve_employee(row, rules)
        if identity_issue:
            issues.append(identity_issue)
            continue
        if employee.employee_id not in whitelist:
            issues.append(issue("not_in_whitelist", "员工不在本次交付白名单内", row))
            continue
        work_date = parse_date(row.get("date"))
        if work_date is None:
            issues.append(issue("invalid_date", "打卡日期无法解析", row))
            continue
        punch = parse_time(row.get("punch_time"))
        key = (employee.employee_id, work_date)
        bucket = buckets.setdefault(key, DayBucket(employee=employee, work_date=work_date))
        bucket.sources.add((row.get("source") or "unknown").strip())
        if punch is None:
            bucket.issues.append(issue("invalid_time", "打卡时间无法解析", row))
            continue
        if punch in bucket.punches:
            bucket.issues.append(issue("duplicate_punch", "重复打卡时间已去重", row))
            continue
        bucket.punches.append(punch)

    for bucket in buckets.values():
        bucket.punches.sort()
    return buckets, issues


def classify_day(bucket: DayBucket, work_start: time, work_end: time) -> dict[str, Any]:
    if bucket.special_state:
        bucket.issues.append(
            issue(
                "special_state_override",
                f"{bucket.special_state} 状态覆盖普通打卡异常",
                {"reason": bucket.special_reason},
            )
        )
        status = bucket.special_state
    elif not bucket.punches:
        bucket.issues.append(issue("absent", "无有效打卡"))
        status = "absent"
    else:
        first = bucket.punches[0]
        last = bucket.punches[-1]
        status_flags: list[str] = []
        if len(bucket.punches) == 1:
            bucket.issues.append(issue("missing_punch", "仅有一次有效打卡"))
            status_flags.append("missing_punch")
        if first > work_start:
            bucket.issues.append(issue("late", "上班打卡晚于规则时间"))
            status_flags.append("late")
        if len(bucket.punches) >= 2 and last < work_end:
            bucket.issues.append(issue("early_leave", "下班打卡早于规则时间"))
            status_flags.append("early_leave")
        status = "normal" if not status_flags else "+".join(status_flags)

    return {
        "employee_id": bucket.employee.employee_id,
        "name": bucket.employee.canonical_name,
        "department": bucket.employee.department,
        "date": bucket.work_date.isoformat(),
        "punches": [p.strftime("%H:%M") for p in bucket.punches],
        "sources": sorted(bucket.sources),
        "special_state": bucket.special_state,
        "status": status,
        "issues": bucket.issues,
    }


def summarize(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = defaultdict(lambda: defaultdict(int))
    meta: dict[str, dict[str, str]] = {}
    for record in records:
        employee_id = record["employee_id"]
        meta[employee_id] = {
            "employee_id": employee_id,
            "name": record["name"],
            "department": record["department"],
        }
        grouped[employee_id]["days"] += 1
        grouped[employee_id][record["status"]] += 1
        grouped[employee_id]["issue_count"] += len(record["issues"])

    result = []
    for employee_id, counters in grouped.items():
        item = dict(meta[employee_id])
        item.update(dict(counters))
        result.append(item)
    return sorted(result, key=lambda row: (row["department"], row["employee_id"]))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_json(name: str, payload: dict[str, Any], runtime_dir: Path) -> Path:
    runtime_dir.mkdir(parents=True, exist_ok=True)
    output = runtime_dir / name
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output


def run_pipeline(
    punch_logs: Path = DEFAULT_PUNCH_LOGS,
    special_states: Path = DEFAULT_SPECIAL_STATES,
    identity_rules: Path = DEFAULT_IDENTITY_RULES,
    runtime_dir: Path = DEFAULT_RUNTIME,
) -> dict[str, Any]:
    rules = load_identity_rules(identity_rules)
    punch_rows = read_csv(punch_logs)
    state_rows = read_csv(special_states)
    buckets, global_issues = apply_punch_rows(punch_rows, rules)
    state_index, state_issues = build_special_state_index(state_rows, rules)
    global_issues.extend(state_issues)

    for key, state in state_index.items():
        employee = rules["by_id"][key[0]]
        bucket = buckets.setdefault(key, DayBucket(employee=employee, work_date=key[1]))
        bucket.special_state = state["state"]
        bucket.special_reason = state["reason"]

    standard_records = [
        classify_day(bucket, rules["work_start"], rules["work_end"])
        for bucket in sorted(buckets.values(), key=lambda item: (item.employee.employee_id, item.work_date))
    ]
    issue_records = [
        {
            "employee_id": record["employee_id"],
            "name": record["name"],
            "date": record["date"],
            "status": record["status"],
            "issues": record["issues"],
        }
        for record in standard_records
        if record["issues"]
    ]
    report = {
        "pipeline": "attendance_dirty_data_demo",
        "input": {
            "punch_logs": display_path(punch_logs),
            "special_states": display_path(special_states),
            "identity_rules": display_path(identity_rules),
        },
        "raw_punch_row_count": len(punch_rows),
        "standard_day_record_count": len(standard_records),
        "global_issue_count": len(global_issues),
        "day_issue_record_count": len(issue_records),
        "standard_records": standard_records,
        "global_issues": global_issues,
        "summary": summarize(standard_records),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output = write_json(f"attendance_pipeline_report_{stamp}.json", report, runtime_dir)
    report["report_path"] = display_path(output)
    return report


def load_samples() -> dict[str, Any]:
    return {
        "punch_logs_dirty": read_csv(DEFAULT_PUNCH_LOGS),
        "special_states": read_csv(DEFAULT_SPECIAL_STATES),
        "identity_rules": json.loads(DEFAULT_IDENTITY_RULES.read_text(encoding="utf-8")),
    }

