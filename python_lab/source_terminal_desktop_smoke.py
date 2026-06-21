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
    contract = read_json(root / "configs/source_terminal_desktop.v257.json")
    sample = read_json(root / "tauri-app/src/source-terminal.sample.json")
    main_rs = (root / "tauri-app/src-tauri/src/main.rs").read_text(encoding="utf-8")
    api_js = (root / "tauri-app/src/api.js").read_text(encoding="utf-8")
    renderer_js = (root / "tauri-app/src/source_terminal.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})
    panel_ids = contract.get("panel_ids", [])
    button_ids = contract.get("button_ids", [])
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_terminal_desktop_contract.v257",
        "paper_readonly": contract.get("paper_only") is True and contract.get("read_only") is True,
        "locked_state": contract.get("live_fetch_enabled") is False and contract.get("downstream_actions_enabled") is False,
        "sample_shape": sample.get("source_terminal_visible") is True and sample.get("adapter_count") == 2 and sample.get("normalized_total_rows") == 5,
        "sample_counts": sample.get("normalized_row_counts", {}).get("odds_snapshot_candidate") == 3 and sample.get("normalized_row_counts", {}).get("fixture_result_candidate") == 1 and sample.get("normalized_row_counts", {}).get("event_context_candidate") == 1,
        "tauri_command": contains_all(main_rs, ["SourceTerminalLoadPayload", "load_first_source_terminal_json", "load_source_terminal_report", "source-terminal.sample.json"]),
        "tauri_handler": "load_source_terminal_report" in main_rs and "tauri::generate_handler!" in main_rs,
        "frontend_api": contains_all(api_js, ["fallbackSourceTerminal", "load_source_terminal_report", "loadSourceTerminalReport"]),
        "frontend_renderer": contains_all(renderer_js, ["loadAndRenderSourceTerminal", "source-terminal-summary", "source-terminal-readiness", "source-terminal-actions", "source-terminal-blockers"]),
        "app_binding": contains_all(app_js, ["loadAndRenderSourceTerminal", "load-source-terminal-report", "load-source-terminal-sample"]),
        "html_page": contract.get("page_id") in html and all(panel in html for panel in panel_ids) and all(button in html for button in button_ids),
        "html_script": "source_terminal.js" in html,
        "sample_locked_list": isinstance(sample.get("locked_ui_actions"), list) and len(sample.get("locked_ui_actions", [])) >= 5,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 7,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_terminal_desktop_smoke.v257",
        "milestone": "v257_source_terminal_desktop_surface",
        "acceptance": checks,
        "summary": {
            "page_id": contract.get("page_id"),
            "button_ids": button_ids,
            "panel_ids": panel_ids,
            "sample_rows": sample.get("normalized_total_rows"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v257_source_terminal_desktop.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
