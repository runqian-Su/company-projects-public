from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESUME = PROJECT_ROOT / "examples" / "sample-data" / "resume.raw.json"
DEFAULT_INSIGHT = PROJECT_ROOT / "examples" / "sample-data" / "insight.json"
DEFAULT_RUNTIME = PROJECT_ROOT / "examples" / "runtime"


REQUIRED_REPORT_FIELDS = [
    "name",
    "position",
    "reasons",
    "basic",
    "education",
    "jobs",
    "projects",
    "skills",
    "self_eval",
    "extra",
    "eval",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def compose_report(
    resume_path: Path = DEFAULT_RESUME,
    insight_path: Path = DEFAULT_INSIGHT,
    target_position: str = "Demo Operations Director",
    runtime_dir: Path = DEFAULT_RUNTIME,
) -> dict[str, Any]:
    resume = load_json(resume_path)
    insight = load_json(insight_path)
    runtime_dir.mkdir(parents=True, exist_ok=True)

    has_target = bool(target_position and target_position.strip())
    report = {
        "name": resume["name"],
        "position": target_position.strip() if has_target else "",
        "reasons": [
            f"{item['title']}：证据来自 {item['evidence']}"
            for item in insight.get("strengths", [])[:3]
        ]
        if has_target
        else [],
        "basic": [
            ["姓名", resume["name"]],
            ["性别 / 年龄", resume["basic"].get("gender_age", "")],
            ["现居", resume["basic"].get("location", "")],
            ["联系方式", resume["basic"].get("phone", "")],
            ["邮箱", resume["basic"].get("email", "")],
        ],
        "education": [
            f"{item['period']} {item['school']} {item['degree']} {item['major']}"
            for item in resume.get("education", [])
        ],
        "jobs": [
            {
                "title": item["company"],
                "period": item["period"],
                "role": item["role"],
                "content_blocks": [["工作事实：", item.get("facts", [])]],
            }
            for item in resume.get("jobs", [])
        ],
        "projects": [],
        "skills": resume.get("skills", []),
        "self_eval": [],
        "extra": [],
        "eval": [
            f"优势：{item['title']}" for item in insight.get("strengths", [])
        ]
        + [f"待确认：{item['title']}" for item in insight.get("risks", [])],
        "meta": {
            "source_resume": display_path(resume_path),
            "source_insight": display_path(insight_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    output = runtime_dir / "report.json"
    write_json(output, report)
    return {"ok": True, "report_path": display_path(output), "report": report}


def validate_report(report_path: Path = DEFAULT_RUNTIME / "report.json") -> dict[str, Any]:
    if not report_path.exists():
        composed = compose_report(runtime_dir=report_path.parent)
        report = composed["report"]
    else:
        report = load_json(report_path)
    errors: list[str] = []

    for field in REQUIRED_REPORT_FIELDS:
        if field not in report:
            errors.append(f"缺少字段: {field}")
    if not isinstance(report.get("reasons", []), list):
        errors.append("reasons 必须是列表")
    if not isinstance(report.get("basic", []), list):
        errors.append("basic 必须是列表")
    if not isinstance(report.get("jobs", []), list):
        errors.append("jobs 必须是列表")
    if not report.get("position") and report.get("reasons"):
        errors.append("未提供推荐岗位时 reasons 必须为空")

    return {
        "ok": not errors,
        "report_path": display_path(report_path),
        "errors": errors,
        "field_count": len(report.keys()),
    }


def render_markdown(report_path: Path = DEFAULT_RUNTIME / "report.json", runtime_dir: Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    if not report_path.exists():
        compose_report(runtime_dir=report_path.parent)
    report = load_json(report_path)
    lines = [
        f"# {report['name']} 推荐报告",
        "",
        f"推荐岗位：{report.get('position') or '未指定'}",
        "",
        "## 推荐理由",
    ]
    if report.get("reasons"):
        lines.extend(f"- {item}" for item in report["reasons"])
    else:
        lines.append("- 未指定目标岗位，推荐理由留空。")
    lines.extend(["", "## 基本信息"])
    lines.extend(f"- {key}: {value}" for key, value in report.get("basic", []))
    lines.extend(["", "## 工作经历"])
    for job in report.get("jobs", []):
        lines.append(f"### {job['title']} / {job['role']} / {job['period']}")
        for block_title, items in job.get("content_blocks", []):
            lines.append(f"- {block_title}")
            lines.extend(f"  - {item}" for item in items)
    lines.extend(["", "## 综合评价"])
    lines.extend(f"- {item}" for item in report.get("eval", []))

    runtime_dir.mkdir(parents=True, exist_ok=True)
    output = runtime_dir / "report_preview.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "preview_path": display_path(output), "line_count": len(lines)}

