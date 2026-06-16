#!/usr/bin/env python3
"""v50-v52 desktop GUI architecture/bridge smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_FRONTEND_FILES = [
    "tauri-app/src/index.html",
    "tauri-app/src/styles.css",
    "tauri-app/src/api.js",
    "tauri-app/src/dashboard.js",
    "tauri-app/src/app.js",
    "tauri-app/src/dashboard-data.sample.json",
]

REQUIRED_PAGES = [
    "dashboard",
    "events",
    "markets",
    "unknowns",
    "features",
    "settlement",
    "accounting",
    "models",
    "settings",
    "simple",
    "detailed",
    "advanced",
    "builder",
]

REQUIRED_DASHBOARD_MARKERS = [
    "dashboard-events",
    "dashboard-markets",
    "dashboard-unknowns",
    "dashboard-features",
    "dashboard-settlement",
    "dashboard-accounting",
]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    file_presence = {rel: (root / rel).exists() for rel in REQUIRED_FRONTEND_FILES}
    html = read(root, "tauri-app/src/index.html")
    css = read(root, "tauri-app/src/styles.css")
    api = read(root, "tauri-app/src/api.js")
    dashboard = read(root, "tauri-app/src/dashboard.js")
    app = read(root, "tauri-app/src/app.js")
    rust = read(root, "tauri-app/src-tauri/src/main.rs")
    sample = json.loads(read(root, "tauri-app/src/dashboard-data.sample.json"))

    page_markers = {page: (f'id="{page}"' in html and f'data-page="{page}"' in html) for page in REQUIRED_PAGES}
    dashboard_markers = {marker: marker in html for marker in REQUIRED_DASHBOARD_MARKERS}
    frontend_split = {
        "css_linked": 'href="styles.css"' in html,
        "api_module_linked": 'src="api.js"' in html,
        "dashboard_module_linked": 'src="dashboard.js"' in html,
        "app_module_linked": 'src="app.js"' in html,
        "no_inline_script_block": "<script>" not in html,
        "sidebar_present": "desktop-sidebar" in html and "nav-button" in html,
        "responsive_css_present": "@media" in css,
    }
    bridge = {
        "dashboard_payload_struct": "struct DashboardLoadPayload" in rust,
        "load_command_fn": "fn load_dashboard_report" in rust,
        "load_command_registered": "load_dashboard_report" in rust and "generate_handler!" in rust,
        "allowlisted_dashboard_paths": "build" in rust and "v49_dashboard_data.json" in rust and "dashboard-data.sample.json" in rust,
        "local_file_read": "fs::read_to_string" in rust,
        "no_network_code": "reqwest" not in rust and "TcpStream" not in rust,
    }
    js = {
        "uses_tauri_invoke": "window.__TAURI__" in api and "invoke" in api,
        "has_browser_fallback": "fallbackDashboard" in api,
        "unwraps_tauri_payload": "dashboard_json" in dashboard and "unwrapDashboardPayload" in dashboard,
        "binds_sidebar": "querySelectorAll('.nav-button')" in app,
        "loads_dashboard_report": "loadAndRenderDashboard" in app,
    }
    sample_sections = sample.get("sections", {})
    sample_ok = {
        "sample_ok_true": sample.get("ok") is True,
        "has_events": bool(sample_sections.get("events")),
        "has_markets": bool(sample_sections.get("market_snapshots")),
        "has_unknowns": bool(sample_sections.get("unknown_market_queue")),
        "has_features": bool(sample_sections.get("feature_snapshot_preview")),
        "has_settlement": bool(sample_sections.get("settlement_report")),
        "has_accounting": bool(sample_sections.get("result_accounting_report")),
    }
    safety = {
        "paper_only_marker": "PAPER_ONLY" in html,
        "no_recommendation_output_text": "no recommendation output" in html.lower() or "no recommendation output" in api.lower(),
        "browser_preview_secondary": "browser fallback" in api.lower() or "browser preview" in api.lower(),
    }
    acceptance = {
        "all_frontend_files_present": all(file_presence.values()),
        "all_pages_present": all(page_markers.values()),
        "dashboard_markers_present": all(dashboard_markers.values()),
        "frontend_split_ok": all(frontend_split.values()),
        "bridge_ok": all(bridge.values()),
        "js_ok": all(js.values()),
        "sample_ok": all(sample_ok.values()),
        "safety_ok": all(safety.values()),
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v50_v52_desktop_gui_architecture_bridge_navigation",
        "file_presence": file_presence,
        "page_markers": page_markers,
        "dashboard_markers": dashboard_markers,
        "frontend_split": frontend_split,
        "bridge": bridge,
        "js": js,
        "sample": sample_ok,
        "safety": safety,
        "acceptance": acceptance,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v50-v52 desktop GUI bridge smoke.")
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v50_v52_desktop_gui_bridge.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
