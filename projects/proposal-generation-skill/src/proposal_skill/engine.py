from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DECK = PROJECT_ROOT / "examples" / "decks" / "demo_retail_deck.json"
DEFAULT_RUNTIME = PROJECT_ROOT / "examples" / "runtime"
ASSET_REGISTRY = PROJECT_ROOT / "assets" / "registry" / "asset_registry.json"
TEMPLATE_REGISTRY = PROJECT_ROOT / "assets" / "registry" / "template_registry.json"
STRUCTURE_REGISTRY = PROJECT_ROOT / "assets" / "structure_modes" / "registry.json"
INDUSTRY_REGISTRY = PROJECT_ROOT / "assets" / "industry_narratives" / "registry.json"
BASE_CSS = PROJECT_ROOT / "assets" / "templates" / "base.css"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(PROJECT_ROOT))
    except ValueError:
        return str(path)


def registry_index(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    return {item[key]: item for item in items}


def load_context() -> dict[str, Any]:
    assets = registry_index(load_json(ASSET_REGISTRY)["assets"], "asset_id")
    templates = registry_index(load_json(TEMPLATE_REGISTRY)["templates"], "template_id")
    structures = registry_index(load_json(STRUCTURE_REGISTRY)["modes"], "mode_id")
    industries_meta = registry_index(load_json(INDUSTRY_REGISTRY)["industries"], "industry_id")
    industries = {}
    for industry_id, meta in industries_meta.items():
        industries[industry_id] = load_json(PROJECT_ROOT / meta["file"])
    return {
        "assets": assets,
        "templates": templates,
        "structures": structures,
        "industries": industries,
    }


def validate_deck(deck_path: Path = DEFAULT_DECK) -> dict[str, Any]:
    deck = load_json(deck_path)
    ctx = load_context()
    errors: list[str] = []
    warnings: list[str] = []

    if "pages" not in deck or not isinstance(deck["pages"], list):
        errors.append("deck.pages 必须是列表")
        pages = []
    else:
        pages = deck["pages"]

    structure = deck.get("structure") or {}
    mode = structure.get("mode")
    if mode not in ctx["structures"]:
        errors.append(f"未登记的结构模式: {mode}")
    section_titles = [item.get("title") for item in structure.get("sections", [])]

    agenda_pages = [page for page in pages if page.get("template") == "agenda"]
    if agenda_pages:
        agenda_items = agenda_pages[0].get("data", {}).get("items", [])
        if agenda_items != section_titles:
            errors.append("agenda items 与 structure.sections 标题不一致")

    covered_titles: list[str] = []
    for section in structure.get("sections", []):
        covered_titles.extend(section.get("page_titles", []))

    actual_body_titles = [
        page.get("data", {}).get("title")
        for page in pages
        if page.get("template") in {"asset_page", "industry_cards"}
    ]
    if covered_titles != actual_body_titles:
        errors.append("structure.sections.page_titles 与正文页标题不一致")

    for idx, page in enumerate(pages, start=1):
        template_id = page.get("template")
        data = page.get("data") or {}
        if template_id not in ctx["templates"]:
            errors.append(f"第 {idx} 页模板未登记: {template_id}")
            continue
        for field in ctx["templates"][template_id]["required_fields"]:
            if field not in data:
                errors.append(f"第 {idx} 页缺少字段: {field}")
        source_type = page.get("source_type")
        if source_type not in {"asset", "industry_narrative", "structure", "manual_input"}:
            errors.append(f"第 {idx} 页 source_type 不合法: {source_type}")
        if template_id == "asset_page":
            asset_id = data.get("asset_id")
            asset = ctx["assets"].get(asset_id)
            if not asset:
                errors.append(f"第 {idx} 页资产未登记: {asset_id}")
            elif template_id not in asset.get("allowed_templates", []):
                errors.append(f"第 {idx} 页资产 {asset_id} 不允许使用模板 {template_id}")
        if template_id == "industry_cards":
            industry_id = data.get("industry_id")
            field = data.get("field")
            industry = ctx["industries"].get(industry_id)
            if not industry:
                errors.append(f"第 {idx} 页行业叙述未登记: {industry_id}")
            elif field not in industry:
                errors.append(f"第 {idx} 页行业字段不存在: {industry_id}.{field}")

    if not errors and len(pages) < 4:
        warnings.append("deck 页数较少，仅适合机制演示")

    return {
        "deck": display_path(deck_path),
        "ok": not errors,
        "page_count": len(pages),
        "errors": errors,
        "warnings": warnings,
    }


def render_page(page: dict[str, Any], ctx: dict[str, Any], index: int) -> str:
    template = page["template"]
    data = page["data"]
    kicker = html.escape(page.get("source_type", ""))
    if template == "cover":
        return f"""
<section class="slide">
  <div class="kicker">{kicker}</div>
  <h1>{html.escape(data["title"])}</h1>
  <h2>{html.escape(data["client_name"])}</h2>
  <p>{html.escape(data["subtitle"])}</p>
</section>"""
    if template == "agenda":
        items = "".join(f"<li>{html.escape(item)}</li>" for item in data["items"])
        return f"""
<section class="slide">
  <div class="kicker">{kicker}</div>
  <h2>汇报结构</h2>
  <ol>{items}</ol>
</section>"""
    if template == "section_cover":
        items = "".join(f"<li>{html.escape(item)}</li>" for item in data["highlights"])
        return f"""
<section class="slide">
  <div class="kicker">{kicker}</div>
  <h1>{html.escape(data["title"])}</h1>
  <ul>{items}</ul>
</section>"""
    if template == "asset_page":
        asset = ctx["assets"][data["asset_id"]]
        content = asset["content"]
        bullets = "".join(f"<li>{html.escape(item)}</li>" for item in content.get("bullets", []))
        return f"""
<section class="slide">
  <div class="kicker">{kicker} / {html.escape(data["asset_id"])}</div>
  <h2>{html.escape(content["headline"])}</h2>
  <p>{html.escape(content["body"])}</p>
  <ul>{bullets}</ul>
</section>"""
    if template == "industry_cards":
        industry = ctx["industries"][data["industry_id"]]
        cards = "".join(f"<div class=\"card\">{html.escape(item)}</div>" for item in industry[data["field"]])
        return f"""
<section class="slide">
  <div class="kicker">{kicker} / {html.escape(data["industry_id"])}</div>
  <h2>{html.escape(data["title"])}</h2>
  <div class="grid">{cards}</div>
</section>"""
    if template == "back_cover":
        return f"""
<section class="slide">
  <div class="kicker">{kicker}</div>
  <h1>{html.escape(data["title"])}</h1>
</section>"""
    return f"<section class=\"slide\"><h2>Unsupported page {index}</h2></section>"


def render_demo(deck_path: Path = DEFAULT_DECK, runtime_dir: Path = DEFAULT_RUNTIME) -> dict[str, Any]:
    validation = validate_deck(deck_path)
    runtime_dir.mkdir(parents=True, exist_ok=True)
    if not validation["ok"]:
        report = {
            "ok": False,
            "validation": validation,
            "html_output": None,
        }
    else:
        deck = load_json(deck_path)
        ctx = load_context()
        css = BASE_CSS.read_text(encoding="utf-8")
        pages = "\n".join(render_page(page, ctx, i) for i, page in enumerate(deck["pages"], start=1))
        html_doc = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>{html.escape(deck["title"])}</title>
  <style>{css}</style>
</head>
<body>
  <main class="deck">{pages}</main>
</body>
</html>
"""
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        html_output = runtime_dir / f"demo_proposal_{stamp}.html"
        html_output.write_text(html_doc, encoding="utf-8")
        report = {
            "ok": True,
            "validation": validation,
            "html_output": display_path(html_output),
            "page_count": len(deck["pages"]),
        }

    report_output = runtime_dir / "render_report.json"
    report_output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["render_report"] = display_path(report_output)
    return report


def inspect_registries() -> dict[str, Any]:
    ctx = load_context()
    return {
        "asset_ids": sorted(ctx["assets"].keys()),
        "template_ids": sorted(ctx["templates"].keys()),
        "structure_modes": sorted(ctx["structures"].keys()),
        "industry_ids": sorted(ctx["industries"].keys()),
    }

