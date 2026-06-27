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
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def readme_mentions_walk_forward(readme: str) -> bool:
    lowered = readme.lower()
    return "v321-v330" in lowered and ("walk-forward evaluator" in lowered or "walk-forward evaluation" in lowered)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/walk_forward_evaluator.v321_v330.json")
    sample = read_json(root / "data/evaluation/v321_v330/walk_forward_evaluator.sample.json")
    desktop = read_json(root / "tauri-app/src/walk-forward-evaluator.sample.json")
    docs = (root / "docs/walk_forward_evaluator_v321_v330.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/walk_forward_v321.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v321_v330_walk_forward_evaluator.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/walk_forward_evaluator.js").read_text(encoding="utf-8")

    ids = html_ids(html)
    windows = sample.get("windows", [])
    rows = sample.get("rows", [])
    safety_checks = sample.get("safety_checks", [])
    coverage = sample.get("coverage_readiness", {})
    acceptance = contract.get("acceptance", {})
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.walk_forward_evaluator_contract.v321_v330",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("random_split_allowed") is False,
        "sample_safe": sample.get("paper_only") is True and sample.get("credential_values_present") is False and sample.get("live_provider_calls_present") is False and sample.get("real_money_recommendations_present") is False and sample.get("random_split_present") is False and no_secret_values(sample),
        "windows_required": all(required_subset(contract.get("window_required_fields", []), row) for row in windows),
        "rows_required": all(required_subset(contract.get("row_required_fields", []), row) for row in rows),
        "required_safety_checks": {"prediction_time_within_evaluation_window", "feature_observed_at_lte_prediction_time", "label_created_at_gte_settled_at", "label_created_at_gt_prediction_time", "settled_at_gt_prediction_time", "market_family_matches_window", "no_random_split", "coverage_gate_checked"}.issubset(set(contract.get("required_safety_checks", []))),
        "sample_blocks_unsafe_training": coverage.get("ready_for_training") is False and sample.get("report", {}).get("status") == "blocked" and sample.get("report", {}).get("random_split_used") is False,
        "timestamp_failure_present": any(row.get("feature_observed_at", "") > row.get("prediction_time", "") for row in rows),
        "label_settlement_order": all(row.get("label_created_at", "") >= row.get("settled_at", "") for row in rows),
        "labels_after_prediction": all(row.get("label_created_at", "") > row.get("prediction_time", "") and row.get("settled_at", "") > row.get("prediction_time", "") for row in rows),
        "market_family_windows": all(any(window.get("window_id") == row.get("window_id") and window.get("market_family") == row.get("market_family") for window in windows) for row in rows),
        "coverage_gates": contract.get("coverage_gates", {}).get("minimum_eval_rows") == 100 and contract.get("coverage_gates", {}).get("minimum_settlement_coverage_ratio") >= 0.95,
        "safety_check_sample": any(check.get("check") == "feature_observed_at_lte_prediction_time" and check.get("status") == "fail" and check.get("failures") == 1 for check in safety_checks),
        "desktop_sample_shape": desktop.get("schema") == "omnibet.walk_forward_evaluator_desktop_sample.v321_v330" and len(desktop.get("safety_rows", [])) >= 8,
        "rust_module_exposed": "pub mod walk_forward_v321;" in rust_lib and "pub use walk_forward_v321::*;" in rust_lib,
        "rust_evaluator_defined": "evaluate_walk_forward_sample" in rust_module and "validate_walk_forward_contract" in rust_module and "write_walk_forward_report" in rust_module,
        "rust_no_leak_checks": "feature_observed_at > row.prediction_time" in rust_module and "label_created_at < row.settled_at" in rust_module and "random_split_present" in rust_module,
        "html_page_wired": 'data-page="walk-forward-evaluator"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="walk_forward_evaluator.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./walk_forward_evaluator.js" in app_js and "loadAndRenderWalkForwardEvaluatorStatus" in app_js and "load-walk-forward-evaluator-status" in app_js,
        "renderer_wired": "renderWalkForwardEvaluatorStatus" in renderer and "renderSafety" in renderer and "renderCoverage" in renderer,
        "docs_updated": "v321-v330 Rust Dataset Loader" in docs and "no-random-split" in docs,
        "readme_updated": readme_mentions_walk_forward(readme),
        "workflow_updated": "walk_forward_evaluator_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 12,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.walk_forward_evaluator_smoke.v321_v330",
        "milestone": "v321_v330_rust_dataset_loader_walk_forward_evaluator",
        "acceptance": checks,
        "summary": {
            "windows": len(windows),
            "rows": len(rows),
            "safety_checks": len(safety_checks),
            "ready_for_training": coverage.get("ready_for_training"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v321_v330_walk_forward_evaluator.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
