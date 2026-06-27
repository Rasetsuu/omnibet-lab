#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def contains_all(text: str, needles: list[str]) -> bool:
    return all(needle in text for needle in needles)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/source_terminal_filters_details.v260.json")
    sample = read_json(root / "tauri-app/src/source-terminal.sample.json")
    renderer_js = (root / "tauri-app/src/source_terminal.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    docs = (root / "docs/source_terminal_filters_details_v260.md").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})
    rows = sample.get("normalized_preview_rows", [])
    adapters = sample.get("adapter_health", [])
    required_row_fields = set(contract.get("required_row_fields", []))
    filter_ids = contract.get("filter_ids", [])
    panel_ids = contract.get("panel_ids", [])
    button_ids = contract.get("button_ids", [])
    source_terminal_page_exists = contract.get("page_id") in html
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_terminal_filters_details_contract.v260",
        "paper_readonly": contract.get("paper_only") is True and contract.get("read_only") is True,
        "locked_state": contract.get("live_fetch_enabled") is False and contract.get("downstream_actions_enabled") is False,
        "sample_shape": sample.get("schema") == "omnibet.source_terminal_desktop_sample.v260" and len(rows) == 5 and len(adapters) == 2,
        "sample_row_fields": all(required_row_fields.issubset(row.keys()) for row in rows),
        "sample_filters_have_multiple_values": len({row.get("provider") for row in rows}) >= 2 and len({row.get("row_type") for row in rows}) >= 3,
        "renderer_filters": contains_all(renderer_js, ["renderFilteredSourceRows", "source-terminal-provider-filter", "source-terminal-row-type-filter", "source-terminal-readiness-filter", "source-terminal-blocker-filter"]),
        "renderer_details": contains_all(renderer_js, ["data-source-row-index", "source-terminal-selected-row", "normalized_preview_rows", "adapter_health"]),
        "renderer_dynamic_panels": contains_all(renderer_js, ["ensurePanel", "source-terminal-filters", "source-terminal-row-details"]),
        "html_source_page": source_terminal_page_exists and "generate-source-terminal-report" in html,
        "html_filter_ids_runtime_owned": all(filter_id in renderer_js for filter_id in filter_ids),
        "docs_updated": "v260 Source Terminal Filters and Row Details" in docs and "no live provider call" in docs,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 8,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_terminal_filters_details_smoke.v260",
        "milestone": "v260_source_terminal_filters_details",
        "acceptance": checks,
        "summary": {
            "filter_ids": filter_ids,
            "panel_ids": panel_ids,
            "button_ids": button_ids,
            "sample_rows": len(rows),
            "adapter_rows": len(adapters),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v260_source_terminal_filters_details.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
