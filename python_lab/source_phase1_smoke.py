#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from local_data_contract import materialize
from review_decision_store import append_decision, decision_record
from source_phase1 import cache_all, promote, status


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read(root: Path, rel: str) -> str:
    return (root / rel).read_text(encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    with tempfile.TemporaryDirectory() as td:
        local_root = Path(td) / "OmniBetLocal"
        contract = materialize(root / "configs/local_data_contract.v61.json", str(local_root), create=True)
        source_status = status(env={})
        cache_report = cache_all(local_root, root)
        decision_store = local_root / "review_decisions" / "review_decisions.jsonl"
        append_decision(decision_store, decision_record("unknown_market", "unknown:accepted", "accepted", "accepted source phase smoke"))
        append_decision(decision_store, decision_record("provider_identity", "identity:accepted", "accepted", "accepted identity smoke"))
        append_decision(decision_store, decision_record("unknown_market", "unknown:rejected", "rejected", "rejected source phase smoke"))
        promotion_out = local_root / "exports" / "mapping_rule_candidates.v66.json"
        promotion = promote(decision_store, promotion_out)

    settings = json.loads(read(root, "tauri-app/src/settings-data.sample.json"))
    settings_js = read(root, "tauri-app/src/settings.js")
    rust = read(root, "tauri-app/src-tauri/src/main.rs")
    helper = read(root, "python_lab/source_phase1.py")

    checks = {
        "contract_ok": contract.get("ok") is True,
        "source_status_ok": source_status.get("ok") is True,
        "sources_disabled": all(row.get("enabled") is False for row in source_status.get("sources", [])),
        "status_only_no_values": source_status.get("safety", {}).get("credential_values_displayed") is False,
        "manual_only": source_status.get("safety", {}).get("manual_only") is True,
        "cache_ok": cache_report.get("ok") is True,
        "cache_two_sources": len(cache_report.get("results", [])) == 2,
        "cache_no_external_calls": cache_report.get("safety", {}).get("external_calls") is False,
        "promotion_ok": promotion.get("ok") is True,
        "promotion_candidate_rows": promotion.get("candidate_rows") == 2,
        "promotion_no_production_rows": promotion.get("production_rows_written") == 0,
        "promotion_candidate_only": promotion.get("safety", {}).get("candidate_only") is True,
        "settings_source_controls": len(settings.get("source_controls", [])) == 2,
        "settings_sources_disabled": all(row.get("enabled") is False for row in settings.get("source_controls", [])),
        "settings_promotion_candidate_only": settings.get("promotion_controls", {}).get("candidate_only") is True,
        "settings_no_secret_values": settings.get("safety", {}).get("no_api_key_values") is True,
        "settings_no_network": settings.get("runtime", {}).get("network_enabled") is False,
        "ui_source_buttons": "source-status-button" in settings_js and "source-cache-button" in settings_js,
        "ui_promotion_button": "promote-review-decisions" in settings_js,
        "ui_uses_tauri_bridge": "invokeCommand('source_status'" in settings_js and "invokeCommand('cache_source_sample'" in settings_js and "invokeCommand('promote_review_decisions'" in settings_js,
        "rust_commands_registered": all(name in rust and "generate_handler!" in rust for name in ["source_status", "cache_source_sample", "promote_review_decisions"]),
        "rust_no_shell_execution": ".shell" not in rust and "cmd /C" not in rust and "sh -c" not in rust,
        "helper_cli_modes": all(flag in helper for flag in ["--status", "--cache-samples", "--promote"]),
    }
    return {
        "ok": all(checks.values()),
        "milestone": "v63_v66_source_optin_cache_promotion",
        "source_status": source_status,
        "cache_report": cache_report,
        "promotion": promotion,
        "acceptance": checks,
        "safety": {
            "offline_local_only": True,
            "credential_values_displayed": False,
            "external_calls_in_ci": False,
            "candidate_only_promotion": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v63_v66_source_phase1.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
