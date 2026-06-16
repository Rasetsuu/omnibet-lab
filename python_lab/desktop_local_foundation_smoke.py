#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from local_data_contract import materialize
from review_decision_store import append_decision, decision_record, read_decisions, summarize
from desktop_package_readiness_smoke import build_report as build_package_report


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def build_report(root: Path, platform_name: str) -> Dict[str, Any]:
    package_report = build_package_report(root, platform_name)
    rust = read(root, "tauri-app/src-tauri/src/main.rs")
    api = read(root, "tauri-app/src/api.js")
    review_js = read(root, "tauri-app/src/review.js")
    settings_js = read(root, "tauri-app/src/settings.js")
    settings_sample = json.loads(read(root, "tauri-app/src/settings-data.sample.json"))
    contract_path = root / "configs/local_data_contract.v61.json"
    contract = json.loads(contract_path.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as td:
        local_root = Path(td) / "OmniBetLocal"
        contract_report = materialize(contract_path, str(local_root), create=True)
        store = local_root / "review_decisions" / "review_decisions.jsonl"
        first = decision_record("unknown_market", "unknown:000", "accepted", "offline smoke decision")
        second = decision_record("provider_identity", "identity:000", "needs_review", "ambiguous identity stays review")
        append_decision(store, first)
        append_decision(store, second)
        stored = read_decisions(store)
        decision_summary = summarize(stored)
        created_dirs = {name: Path(path).exists() for name, path in contract_report["directories"].items()}

    required_contract_dirs = ["configs", "reports", "build", "exports", "review_decisions", "logs", "cache"]
    checks = {
        "package_preflight_ok": package_report.get("ok") is True,
        "contract_version_ok": str(contract.get("version", "")).startswith("omnibet.local_data_contract.v61"),
        "contract_dirs_present": all(d in contract.get("directories", {}) for d in required_contract_dirs),
        "contract_files_present": "review_decisions_jsonl" in contract.get("files", {}) and "workflow_runs_jsonl" in contract.get("files", {}),
        "contract_materialized_dirs": all(created_dirs.values()),
        "decision_store_wrote_rows": len(stored) == 2,
        "decision_summary_ok": decision_summary.get("total") == 2 and decision_summary.get("decision_counts", {}).get("accepted") == 1,
        "rust_save_review_command": "fn save_review_decision" in rust and "ReviewDecisionSavePayload" in rust,
        "rust_review_jsonl_path": "review_decisions/review_decisions.jsonl" in rust,
        "rust_workflow_ux_fields": all(s in rust for s in ["state", "started_at_unix", "finished_at_unix", "report_path_hint", "refresh_hint", "stdout_preview", "stderr_preview"]),
        "rust_workflow_log_path": "logs/workflow_runs.jsonl" in rust,
        "rust_local_root_env": "OMNIBET_HOME" in rust and ".omnibet-local" in rust,
        "api_save_review_export": "saveReviewDecision" in api and "save_review_decision" in api,
        "review_js_persists": "saveReviewDecision" in review_js and "Persisted locally" in review_js,
        "settings_js_status_ux": "workflow-status" in settings_js and "report_path_hint" in settings_js and "refresh_hint" in settings_js,
        "settings_sample_local_root": settings_sample.get("paths", {}).get("local_root") == ".omnibet-local",
        "settings_sample_workflows_have_reports": all("expected_report" in w and "refresh_hint" in w for w in settings_sample.get("local_workflows", [])),
        "no_api_key_values": settings_sample.get("safety", {}).get("no_api_key_values") is True,
        "no_network": settings_sample.get("runtime", {}).get("network_enabled") is False,
        "no_shell_execution": package_report.get("safety", {}).get("no_shell_execution") is True,
    }
    return {
        "ok": all(checks.values()),
        "milestone": "v58_v61_desktop_local_foundation",
        "platform": platform_name,
        "package_report_ok": package_report.get("ok"),
        "contract_report": contract_report,
        "created_dirs": created_dirs,
        "decision_summary": decision_summary,
        "acceptance": checks,
        "safety": {
            "offline_local_only": True,
            "no_api_keys": True,
            "no_network_provider_calls": True,
            "no_shell_execution": checks["no_shell_execution"],
            "review_decisions_local_jsonl": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--platform-name", default="local")
    ap.add_argument("--out", default="reports/ci_v58_v61_desktop_local_foundation.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), args.platform_name)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
