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


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/source_generate_refresh.v259.json")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    source_js = (root / "tauri-app/src/source_terminal.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    settings = read_json(root / "tauri-app/src/settings-data.sample.json")
    acceptance = contract.get("acceptance", {})
    buttons = contract.get("buttons", [])
    workflow_ids = {item.get("workflow_id") for item in settings.get("local_workflows", [])}
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_generate_refresh_contract.v259",
        "paper_local_readonly": contract.get("paper_only") is True and contract.get("local_only") is True and contract.get("read_only_surface") is True,
        "network_disabled": contract.get("network_calls_allowed") is False,
        "workflow_known": contract.get("workflow_id") in workflow_ids,
        "source_helper": "generateAndRenderSourceTerminal" in source_js and "runLocalWorkflow('generate_source_terminal_report')" in source_js and "loadAndRenderSourceTerminal(null)" in source_js,
        "app_imports_helper": "generateAndRenderSourceTerminal" in app_js,
        "app_binds_page_button": "bindSourceGenerateButton('generate-source-terminal-report')" in app_js,
        "app_binds_topbar_button": "bindSourceGenerateButton('generate-source-terminal-report-topbar')" in app_js,
        "html_buttons": all(f'id="{button}"' in html for button in buttons),
        "html_unique_topbar": html.count('id="generate-source-terminal-report-topbar"') == 1,
        "html_unique_page": html.count('id="generate-source-terminal-report"') == 1,
        "refresh_loader": contract.get("refresh_loader") in source_js,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 6,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_generate_refresh_smoke.v259",
        "milestone": "v259_source_generate_refresh",
        "acceptance": checks,
        "summary": {
            "workflow_id": contract.get("workflow_id"),
            "buttons": buttons,
            "expected_output": contract.get("expected_output"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v259_source_generate_refresh.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
