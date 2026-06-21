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
    contract = read_json(root / "configs/source_terminal_report.v256.json")
    rust = (root / "rust-core/src/source_terminal_v256.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    panels = contract.get("desktop_panels", {})
    actions = contract.get("desktop_actions", {})
    readiness = contract.get("readiness_rules", {})
    acceptance = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_terminal_report_contract.v256",
        "paper_only": contract.get("paper_only") is True,
        "ci_offline": contract.get("network_calls_allowed_in_ci") is False,
        "no_repo_credentials": contract.get("credentials_stored_in_repo") is False,
        "live_fetch_disabled": contract.get("live_fetch_enabled") is False,
        "quarantine_only": contract.get("quarantine_only") is True,
        "desktop_panels": all(panels.values()) and len(panels) == 6,
        "desktop_safe_actions": actions.get("inspect_adapters") is True and actions.get("inspect_rows") is True and actions.get("export_report") is True and actions.get("live_fetch") is False and actions.get("promote_to_bronze") is False and actions.get("run_evaluation") is False and actions.get("train_model") is False and actions.get("place_bets") is False,
        "readiness_rules": readiness.get("source_terminal_visible_when_fixture_reports_exist") is True and readiness.get("bronze_write_ready_requires_no_blockers") is False and readiness.get("evaluation_ready_requires_real_historical_backfill") is True and readiness.get("training_ready_requires_walk_forward_validation") is True,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 8,
        "rust_report_type": "SourceTerminalReportV256" in rust,
        "rust_readiness_type": "SourceTerminalReadinessV256" in rust,
        "rust_actions_type": "SourceTerminalDesktopActionsV256" in rust,
        "rust_builder": "build_source_terminal_report_v256" in rust and "build_default_source_terminal_report_v256" in rust,
        "rust_combines_inputs": "validate_provider_adapter_contracts_v254_text" in rust and "build_provider_normalization_preview_v255" in rust,
        "rust_counts": "normalized_row_counts" in rust and "adapter_ok_count" in rust,
        "rust_actions_locked": "live_fetch: false" in rust and "train_model: false" in rust and "place_bets: false" in rust,
        "rust_tests": "builds_source_terminal_report_from_offline_fixtures" in rust and "source_terminal_remains_visible_blocked_when_normalization_has_blockers" in rust,
        "lib_exports": "pub mod source_terminal_v256;" in lib and "pub use source_terminal_v256::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_terminal_report_smoke.v256",
        "milestone": "v256_source_terminal_report",
        "acceptance": checks,
        "summary": {
            "desktop_panels": sorted(panels.keys()),
            "enabled_actions": [key for key, value in actions.items() if value is True],
            "disabled_actions": [key for key, value in actions.items() if value is False],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v256_source_terminal_report.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
