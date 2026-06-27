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


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def readme_mentions_green_sample(readme: str) -> bool:
    lowered = readme.lower()
    return "v351-v360" in lowered and "green" in lowered and "sample" in lowered


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/green_evaluator_sample.v351_v360.json")
    sample = read_json(root / "data/modeling/v351_v360/green_evaluator_sample.sample.json")
    desktop = read_json(root / "tauri-app/src/green-evaluator-sample.sample.json")
    docs = (root / "docs/green_evaluator_sample_v351_v360.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/green_sample_v351.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v351_v360_green_evaluator_sample.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/green_sample.js").read_text(encoding="utf-8")

    manifests = sample.get("source_manifests", [])
    fixtures = sample.get("fixtures", [])
    odds_rows = sample.get("odds_rows", [])
    prediction_rows = sample.get("prediction_rows", [])
    baseline_rows = sample.get("baseline_report", {}).get("metric_summary", [])
    calibration = sample.get("calibration_report", {})
    calibration_bins = calibration.get("calibration_bins", [])
    clv_rows = calibration.get("paper_clv_summary", [])
    no_vig_rows = calibration.get("no_vig_delta_rows", [])
    trust = sample.get("trust_gate", {})
    ids = html_ids(html)
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])
    acceptance = contract.get("acceptance", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.green_evaluator_sample_contract.v351_v360" and sample.get("schema") == "omnibet.green_evaluator_sample.v351_v360",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True and sample.get("paper_only") is True and sample.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and sample.get("live_provider_calls_present") is False and sample.get("credential_values_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "trust_sample_only": contract.get("sample_only_allowed") is True and contract.get("validated_paper_allowed") is False and sample.get("trust_status") == "sample_only" and sample.get("validated_paper_claim_present") is False,
        "manifests_complete": len(manifests) >= 3 and all(required_subset(contract.get("required_source_manifest_fields", []), row) for row in manifests),
        "manifest_hashes_rows_safe": all(len(row.get("content_sha256", "")) == 64 and row.get("row_count", 0) > 0 and row.get("credential_values_present") is False for row in manifests),
        "fixtures_complete": len(fixtures) >= contract.get("green_gate_requirements", {}).get("minimum_fixture_rows", 0) and all(required_subset(contract.get("required_fixture_fields", []), row) for row in fixtures),
        "odds_complete": len(odds_rows) >= 4 and all(required_subset(contract.get("required_odds_fields", []), row) and row.get("closing_price_decimal") is not None for row in odds_rows),
        "predictions_complete": len(prediction_rows) >= contract.get("green_gate_requirements", {}).get("minimum_prediction_rows", 0) and all(required_subset(contract.get("required_prediction_fields", []), row) for row in prediction_rows),
        "timestamp_order_safe": all(row.get("feature_observed_at", "") <= row.get("prediction_time", "") and row.get("settled_at", "") > row.get("prediction_time", "") and row.get("label_created_at", "") >= row.get("settled_at", "") for row in prediction_rows),
        "market_family_count": len({row.get("market_family") for row in prediction_rows}) >= contract.get("green_gate_requirements", {}).get("minimum_market_families", 0),
        "baseline_metrics_non_null": sample.get("baseline_report", {}).get("status") == "ready_for_baseline_reports" and all(row.get("log_loss") is not None and row.get("brier_score") is not None and row.get("calibration_ece") is not None and row.get("status") == "sample_only" for row in baseline_rows),
        "calibration_bins_non_null": calibration.get("status") == "sample_only" and all(row.get("avg_model_probability") is not None and row.get("empirical_hit_rate") is not None and row.get("calibration_gap") is not None and row.get("status") == "sample_only" for row in calibration_bins),
        "no_vig_deltas_non_null": all(row.get("model_probability") is not None and row.get("no_vig_probability") is not None and row.get("delta_vs_no_vig") is not None and row.get("status") == "sample_only" for row in no_vig_rows),
        "paper_clv_non_null": all(row.get("average_clv_decimal") is not None and row.get("positive_clv_ratio") is not None and row.get("status") == "sample_only" for row in clv_rows),
        "trust_locks_outputs": trust.get("status") == "sample_only" and trust.get("validated_paper") is False and trust.get("terminal_prediction_allowed") is False and trust.get("bilet_builder_allowed") is False,
        "desktop_sample_shape": desktop.get("schema") == "omnibet.green_evaluator_desktop_sample.v351_v360" and desktop.get("summary", {}).get("trust_status") == "sample_only" and desktop.get("summary", {}).get("validated_paper") is False,
        "rust_module_exposed": "pub mod green_sample_v351;" in rust_lib and "pub use green_sample_v351::*;" in rust_lib,
        "rust_module_defined": "validate_green_evaluator_sample_contract" in rust_module and "validate_green_evaluator_sample" in rust_module and "feature_observed_at > prediction_time" in rust_module and "validated_paper must remain false" in rust_module,
        "html_page_wired": 'data-page="green-sample"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="green_sample.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./green_sample.js" in app_js and "loadAndRenderGreenSampleStatus" in app_js and "load-green-sample-status" in app_js,
        "renderer_wired": "renderGreenSampleStatus" in renderer and "renderManifests" in renderer and "renderPredictions" in renderer and "renderClv" in renderer,
        "docs_updated": "v351-v360 Green Evaluator Sample" in docs and "sample_only" in docs and "validated_paper" in docs,
        "readme_updated": readme_mentions_green_sample(readme),
        "workflow_updated": "green_evaluator_sample_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 12,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.green_evaluator_sample_smoke.v351_v360",
        "milestone": "v351_v360_green_evaluator_sample",
        "acceptance": checks,
        "summary": {
            "fixtures": len(fixtures),
            "odds_rows": len(odds_rows),
            "prediction_rows": len(prediction_rows),
            "market_families": len({row.get("market_family") for row in prediction_rows}),
            "trust_status": trust.get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v351_v360_green_evaluator_sample.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
