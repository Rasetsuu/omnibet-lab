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
    contract = read_json(root / "configs/historical_import_plan_preview.v246.json")
    rust = (root / "rust-core/src/historical_plan_v246.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    expected = contract.get("expected_plan", {})
    requirements = contract.get("task_requirements", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.historical_import_plan_preview_contract.v246",
        "offline_only": contract.get("offline_only") is True,
        "no_ci_network": contract.get("network_calls_allowed") is False,
        "paper_only": contract.get("paper_only") is True,
        "expected_window_count": expected.get("window_count") == 2,
        "expected_source_count": expected.get("required_source_count") == 3,
        "expected_task_count": expected.get("total_tasks") == 6,
        "expected_clean_plan": expected.get("blocked") is False,
        "expected_import_waits_for_manifest": expected.get("import_allowed_now") is False,
        "expected_next_artifact": expected.get("required_next_artifact") == "offline_file_manifest_with_sha256_and_row_count",
        "task_window_required": requirements.get("window_id_required") is True,
        "task_source_required": requirements.get("source_id_required") is True,
        "task_cutoff_required": requirements.get("snapshot_cutoff_required") is True,
        "task_mapping_required": requirements.get("identity_mapping_required") is True and requirements.get("market_mapping_required_for_odds") is True,
        "rust_types": "HistoricalImportPlanPreview" in rust and "HistoricalImportPlanTask" in rust,
        "rust_builder": "build_historical_import_plan_preview" in rust and "build_default_historical_import_plan_preview" in rust,
        "rust_import_waits": "import_allowed_now: false" in rust,
        "rust_task_count_test": "assert_eq!(plan.total_tasks, 6)" in rust,
        "rust_invalid_contract_test": "blocked_contract_yields_no_tasks" in rust,
        "lib_exports": "pub mod historical_plan_v246;" in lib and "pub use historical_plan_v246::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_import_plan_smoke.v246",
        "milestone": "v246_historical_import_plan_preview",
        "acceptance": checks,
        "expected_plan": expected,
        "safety": {
            "offline_only": True,
            "network_calls_allowed": False,
            "paper_only": True,
            "import_allowed_now": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v246_historical_import_plan.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
