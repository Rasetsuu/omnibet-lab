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


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/generated_history_index.v391_v400.json")
    cli = (root / "rust-core/src/bin/omnibet-local-import-runner.rs").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/generated_green.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    docs = (root / "docs/generated_history_index_v391_v400.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v391_v400_generated_history_index.yml").read_text(encoding="utf-8")
    sample_history = read_json(root / "tauri-app/src/generated-history.sample.json")

    latest_report_path = root / "reports/generated_v371_v380_green_sample.json"
    latest_desktop_path = root / "tauri-app/src/generated-green-sample.generated.json"
    latest_storage_path = root / "reports/generated_v371_v380_storage_manifest.json"
    history_index_path = root / "reports/generated_history/index.json"
    run_dir = root / "reports/generated_history/runs/ci_v391_v400"
    history_files = ["green_report.json", "desktop_report.json", "storage_manifest.json", "command_result.json"]

    latest_report = read_json(latest_report_path) if latest_report_path.exists() else {}
    latest_desktop = read_json(latest_desktop_path) if latest_desktop_path.exists() else {}
    latest_storage = read_json(latest_storage_path) if latest_storage_path.exists() else {}
    history_index = read_json(history_index_path) if history_index_path.exists() else {}
    history_run_files = {name: read_json(run_dir / name) if (run_dir / name).exists() else {} for name in history_files}
    history_runs = history_index.get("runs", [])
    latest_entry = next((row for row in history_runs if row.get("run_id") == "ci_v391_v400"), {})
    acceptance = contract.get("acceptance", {})
    ids = html_ids(html)

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.generated_history_index_contract.v391_v400",
        "contract_safe_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and contract.get("sample_only_allowed") is True,
        "runner_args_defined": all(arg in contract.get("runner", {}).get("new_args", []) for arg in ["--history-dir", "--history-index-out", "--run-id"]),
        "runner_archive_code_present": "archive_history" in cli and "update_history_index" in cli and "history_entry" in cli and "reports/generated_history/runs" in cli and "reports/generated_history/index.json" in cli,
        "runner_failure_preserved": "integrity_failed_sample_only" in cli and "Err(err)" in cli and "archive_history(&args, &report_value" in cli,
        "latest_outputs_exist": latest_report.get("schema") == "omnibet.generated_green_report.v361_v370" and latest_desktop.get("schema") == "omnibet.generated_green_sample_desktop.v391_v400" and latest_storage.get("schema") == "omnibet.generated_storage_manifest.v391_v400",
        "history_index_exists": history_index.get("schema") == "omnibet.generated_history_index.v391_v400" and history_index.get("latest_run_id") == "ci_v391_v400" and history_index.get("run_count", 0) >= 1,
        "history_index_fields": required_subset(contract.get("history_index_required_fields", []), history_index),
        "history_entry_fields": required_subset(contract.get("history_run_required_fields", []), latest_entry),
        "history_run_files_exist": all((run_dir / name).exists() for name in history_files),
        "history_run_files_safe": all(no_secret_values(value) and value.get("recommendation_output_present") is not True for value in history_run_files.values()),
        "history_latest_entry_safe": latest_entry.get("trust_status") == "sample_only" and latest_entry.get("validated_paper") is False and latest_entry.get("recommendation_output_present") is False,
        "desktop_history_sample_ok": sample_history.get("schema") == "omnibet.generated_history_index.v391_v400" and sample_history.get("latest_status") == "generated_sample_only" and sample_history.get("validated_paper") is False,
        "desktop_history_panel_wired": "generated-green-history" in html and "renderHistory" in renderer and "loadAndRenderGeneratedHistoryStatus" in renderer and "generated-history.sample.json" in renderer,
        "html_ids_unique": len(ids) == len(set(ids)),
        "docs_updated": "v391-v400 Generated Report Persistence" in docs and "immutable" in docs.lower() and "sample_only" in docs,
        "workflow_updated": "generated_history_index_smoke.py" in workflow and "--history-dir" in workflow and "--history-index-out" in workflow and "ci_v391_v400" in workflow and "upload-artifact" in workflow,
        "no_secret_values": no_secret_values(contract) and no_secret_values(latest_report) and no_secret_values(latest_desktop) and no_secret_values(latest_storage) and no_secret_values(history_index),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.generated_history_index_smoke.v391_v400",
        "milestone": "v391_v400_generated_report_persistence_and_local_history_index",
        "acceptance": checks,
        "summary": {
            "latest_run_id": history_index.get("latest_run_id"),
            "run_count": history_index.get("run_count"),
            "latest_status": history_index.get("latest_status"),
            "history_files": sorted(history_run_files.keys()),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v391_v400_generated_history_index.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
