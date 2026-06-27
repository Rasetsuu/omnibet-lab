#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def no_secret_strings(*texts: str) -> bool:
    merged = "\n".join(texts).lower()
    forbidden = ["api_key\"", "secret\"", "bearer_token", "credential_value\"", "secret_value", "bearer ", "sk-"]
    return not any(marker in merged for marker in forbidden)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/generated_command_bridge.v381_v390.json")
    main_rs = (root / "tauri-app/src-tauri/src/main.rs").read_text(encoding="utf-8")
    api_js = (root / "tauri-app/src/api.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/generated_green.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    docs = (root / "docs/generated_command_bridge_v381_v390.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v381_v390_generated_command_bridge.yml").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})
    desktop = contract.get("desktop", {})
    tauri_command = contract.get("tauri_command", {})
    ids = html_ids(html)
    required_command_fields = contract.get("command_result_required_fields", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.generated_command_bridge_contract.v381_v390",
        "safe_contract_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and contract.get("sample_only_allowed") is True,
        "tauri_command_contract": tauri_command.get("command_name") == "run_generated_green_report" and tauri_command.get("allowlisted_binary") == "omnibet-local-import-runner" and tauri_command.get("shell_execution_allowed") is False,
        "tauri_backend_command_added": "fn run_generated_green_report() -> CliBridgePayload" in main_rs and "run_allowed_cli(\"omnibet-local-import-runner\", generated_green_args())" in main_rs and "run_generated_green_report" in main_rs and "tauri::generate_handler!" in main_rs,
        "tauri_allowlist_fixed": "omnibet-local-import-runner" in main_rs and "let allowed = [" in main_rs and "Command::new(path).args(&args).output()" in main_rs and "no shell execution" in main_rs.lower(),
        "fixed_args_present": all(arg in main_rs for arg in tauri_command.get("default_args", [])),
        "browser_fallback_safe": "run_generated_green_report" in api_js and "browser_preview_no_execution" in api_js and "recommendation_output_present: false" in api_js and "validated_paper: false" in api_js,
        "renderer_invokes_command": "invokeCommand" in renderer and "run_generated_green_report" in renderer and "runAndRenderGeneratedGreenStatus" in renderer and "renderCommand" in renderer,
        "renderer_reloads_generated": "loadAndRenderGeneratedGreenStatus('tauri-app/src/generated-green-sample.generated.json')" in renderer and "generated-green-sample.sample.json" in renderer,
        "desktop_buttons_present": all(button_id in html for button_id in desktop.get("button_ids", [])),
        "desktop_panels_present": all(panel_id in html for panel_id in desktop.get("panel_ids", [])),
        "app_bindings_present": "runAndRenderGeneratedGreenStatus" in app_js and "bindGeneratedGreenRunButton" in app_js and "bindGeneratedGreenLoadButton" in app_js and "run-generated-green-report-topbar" in app_js and "load-generated-green-status-page" in app_js,
        "html_ids_unique": len(ids) == len(set(ids)),
        "command_result_fields_documented": all(field in json.dumps(contract) for field in required_command_fields),
        "docs_updated": "v381-v390 Generated Report Command Bridge" in docs and "run_generated_green_report" in docs and "sample_only" in docs and "No user-provided shell command" in docs,
        "workflow_updated": "generated_command_bridge_smoke.py" in workflow and "generated_report_writer_smoke.py" in workflow and "cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-local-import-runner" in workflow,
        "no_secret_strings": no_secret_strings(main_rs, api_js, app_js, renderer, html, docs),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.generated_command_bridge_smoke.v381_v390",
        "milestone": "v381_v390_generated_report_command_bridge_and_desktop_local_run_button",
        "acceptance": checks,
        "summary": {
            "button_count": len(desktop.get("button_ids", [])),
            "panel_count": len(desktop.get("panel_ids", [])),
            "html_id_count": len(ids),
            "command": tauri_command.get("command_name"),
            "allowlisted_binary": tauri_command.get("allowlisted_binary"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v381_v390_generated_command_bridge.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
