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


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def readme_mentions_calibration_clv(readme: str) -> bool:
    lowered = readme.lower()
    return "v341-v350" in lowered and "calibration" in lowered and "clv" in lowered


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/calibration_clv_reports.v341_v350.json")
    sample = read_json(root / "data/modeling/v341_v350/calibration_clv_reports.sample.json")
    desktop = read_json(root / "tauri-app/src/calibration-clv.sample.json")
    docs = (root / "docs/calibration_clv_reports_v341_v350.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/calibration_clv_v341.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v341_v350_calibration_clv_reports.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/calibration_clv.js").read_text(encoding="utf-8")

    ids = html_ids(html)
    acceptance = contract.get("acceptance", {})
    calibration_bins = sample.get("calibration_bins", [])
    metric_summary = sample.get("metric_summary", [])
    no_vig_rows = sample.get("no_vig_delta_rows", [])
    clv_rows = sample.get("paper_clv_summary", [])
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.calibration_clv_reports_contract.v341_v350",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False,
        "gated_reports": contract.get("requires_walk_forward_ready") is True and contract.get("requires_baseline_reports_ready") is True and contract.get("blocked_report_required_when_gates_fail") is True,
        "sample_safe": sample.get("paper_only") is True and sample.get("credential_values_present") is False and sample.get("live_provider_calls_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "report_fields_required": set(contract.get("required_report_fields", [])).issubset({"schema", "report_id", "status", "walk_forward_status", "baseline_status", "calibration_bins", "metric_summary", "no_vig_delta_rows", "paper_clv_summary", "trust_gate", "blocked_reason", "recommendation_output_present"}),
        "calibration_bins_required": all(required_subset(contract.get("calibration_bin_required_fields", []), row) for row in calibration_bins),
        "metric_summary_required": all(required_subset(contract.get("metric_summary_required_fields", []), row) for row in metric_summary),
        "no_vig_delta_required": all(required_subset(contract.get("no_vig_delta_required_fields", []), row) for row in no_vig_rows),
        "paper_clv_required": all(required_subset(contract.get("paper_clv_required_fields", []), row) for row in clv_rows),
        "blocked_when_gates_fail": sample.get("walk_forward_status") == "blocked" and sample.get("baseline_status") == "blocked" and sample.get("report", {}).get("status") == "blocked",
        "metrics_null_when_blocked": all(row.get("status") == "blocked" and row.get("log_loss") is None and row.get("brier_score") is None and row.get("calibration_ece") is None for row in metric_summary),
        "calibration_null_when_blocked": all(row.get("status") == "blocked" and row.get("avg_model_probability") is None and row.get("empirical_hit_rate") is None and row.get("calibration_gap") is None for row in calibration_bins),
        "no_vig_delta_null_when_blocked": all(row.get("status") == "blocked" and row.get("model_probability") is None and row.get("delta_vs_no_vig") is None for row in no_vig_rows),
        "paper_clv_null_when_blocked": all(row.get("status") == "blocked" and row.get("average_clv_decimal") is None and row.get("positive_clv_ratio") is None for row in clv_rows),
        "trust_gate_blocks_terminal": sample.get("trust_gate", {}).get("status") == "blocked_sample" and sample.get("trust_gate", {}).get("terminal_prediction_allowed") is False and sample.get("trust_gate", {}).get("bilet_builder_allowed") is False,
        "desktop_sample_shape": desktop.get("schema") == "omnibet.calibration_clv_desktop_sample.v341_v350" and len(desktop.get("calibration_bins", [])) >= 3 and len(desktop.get("paper_clv_summary", [])) >= 3,
        "rust_module_exposed": "pub mod calibration_clv_v341;" in rust_lib and "pub use calibration_clv_v341::*;" in rust_lib,
        "rust_module_defined": "validate_calibration_clv_contract" in rust_module and "calibration_gap" in rust_module and "brier_score" in rust_module and "no_vig_delta" in rust_module and "clv_decimal" in rust_module and "build_blocked_calibration_clv_report" in rust_module,
        "rust_blocks_when_baseline_blocked": "baseline_reports_not_ready" in rust_module and "terminal_prediction_allowed: false" in rust_module and "bilet_builder_allowed: false" in rust_module,
        "html_page_wired": 'data-page="calibration-clv"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="calibration_clv.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./calibration_clv.js" in app_js and "loadAndRenderCalibrationClvStatus" in app_js and "load-calibration-clv-status" in app_js,
        "renderer_wired": "renderCalibrationClvStatus" in renderer and "renderCalibrationBins" in renderer and "renderNoVig" in renderer and "renderPaperClv" in renderer,
        "docs_updated": "v341-v350 Calibration" in docs and "no-vig" in docs.lower() and "CLV" in docs,
        "readme_updated": readme_mentions_calibration_clv(readme),
        "workflow_updated": "calibration_clv_reports_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 12,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.calibration_clv_reports_smoke.v341_v350",
        "milestone": "v341_v350_calibration_clv_no_vig_reports",
        "acceptance": checks,
        "summary": {
            "calibration_bins": len(calibration_bins),
            "metric_rows": len(metric_summary),
            "no_vig_delta_rows": len(no_vig_rows),
            "paper_clv_rows": len(clv_rows),
            "report_status": sample.get("report", {}).get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v341_v350_calibration_clv_reports.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
