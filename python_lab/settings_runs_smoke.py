#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_FILES = [
    "tauri-app/src/settings.js",
    "tauri-app/src/settings-data.sample.json",
    "tauri-app/src/api.js",
    "tauri-app/src/app.js",
    "tauri-app/src/index.html",
    "tauri-app/src-tauri/src/main.rs",
]

REQUIRED_WORKFLOWS = [
    "generate_dashboard_report",
    "generate_review_report",
    "run_leak_guard",
    "run_feature_export",
    "run_settlement_truth",
    "run_first_model_pass",
]

REQUIRED_UI_MARKERS = [
    "load-settings-report",
    "load-settings-sample",
    "settings-paths",
    "settings-runtime",
    "settings-providers",
    "settings-safety",
    "local-run-buttons",
]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    files = {rel: (root / rel).exists() for rel in REQUIRED_FILES}
    html = read(root, "tauri-app/src/index.html")
    api = read(root, "tauri-app/src/api.js")
    app = read(root, "tauri-app/src/app.js")
    settings_js = read(root, "tauri-app/src/settings.js")
    rust = read(root, "tauri-app/src-tauri/src/main.rs")
    sample = json.loads(read(root, "tauri-app/src/settings-data.sample.json"))

    workflow_ids = [w.get("workflow_id") for w in sample.get("local_workflows", [])]
    ui_markers = {m: m in html for m in REQUIRED_UI_MARKERS}
    workflow_markers = {w: (w in rust and w in settings_js and w in json.dumps(sample)) for w in REQUIRED_WORKFLOWS}
    checks = {
        "files_present": all(files.values()),
        "sample_ok": sample.get("ok") is True,
        "sample_has_paths": bool(sample.get("paths")),
        "sample_has_runtime": bool(sample.get("runtime")),
        "sample_has_providers": len(sample.get("providers", [])) >= 2,
        "sample_no_key_values": sample.get("safety", {}).get("no_api_key_values") is True,
        "all_workflows_in_sample": all(w in workflow_ids for w in REQUIRED_WORKFLOWS),
        "ui_markers_present": all(ui_markers.values()),
        "settings_module_linked": 'src="settings.js"' in html,
        "api_has_settings_loader": "load_app_settings" in api and "loadAppSettings" in api,
        "api_has_workflow_runner": "run_local_workflow" in api and "runLocalWorkflow" in api,
        "app_binds_settings": "loadAndRenderSettings" in app and "load-settings-report" in app,
        "settings_renders_workflows": "local-workflow-button" in settings_js and "runLocalWorkflow" in settings_js,
        "rust_settings_command_registered": "fn load_app_settings" in rust and "load_app_settings" in rust and "generate_handler!" in rust,
        "rust_workflow_command_registered": "fn run_local_workflow" in rust and "run_local_workflow" in rust and "generate_handler!" in rust,
        "rust_has_allowlist": "fn local_workflow_args" in rust and all(w in rust for w in REQUIRED_WORKFLOWS),
        "rust_no_shell_execution": "Command::new" in rust and ".shell" not in rust and "cmd /C" not in rust and "sh -c" not in rust,
        "cross_platform_python_hint": "cfg!(windows)" in rust and "OMNIBET_PYTHON" in rust,
        "paper_only_marker": "PAPER_ONLY" in html,
        "no_network_marker": "network_enabled" in json.dumps(sample) and sample.get("runtime", {}).get("network_enabled") is False,
    }
    return {
        "ok": all(checks.values()),
        "milestone": "v55_v56_settings_and_local_run_controls",
        "files": files,
        "ui_markers": ui_markers,
        "workflow_markers": workflow_markers,
        "workflow_ids": workflow_ids,
        "acceptance": checks,
        "safety": sample.get("safety", {}),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v55_v56_settings_runs.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
