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


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/baseline_training_reports.v331_v340.json")
    sample = read_json(root / "data/modeling/v331_v340/baseline_training_reports.sample.json")
    desktop = read_json(root / "tauri-app/src/baseline-reports.sample.json")
    docs = (root / "docs/baseline_training_reports_v331_v340.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/baseline_reports_v331.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v331_v340_baseline_training_reports.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/baseline_reports.js").read_text(encoding="utf-8")

    ids = html_ids(html)
    acceptance = contract.get("acceptance", {})
    baseline_rows = sample.get("baseline_rows", [])
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.baseline_training_reports_contract.v331_v340",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False,
        "gated_training": contract.get("training_requires_walk_forward_ready") is True and contract.get("blocked_report_required_when_gates_fail") is True,
        "sample_safe": sample.get("paper_only") is True and sample.get("credential_values_present") is False and sample.get("live_provider_calls_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "baseline_families_present": {"no_vig_1x2_v331", "no_vig_totals_v332", "no_vig_btts_v333", "poisson_elo_team_strength_candidate_v334"}.issubset({row.get("baseline_id") for row in contract.get("baseline_families", [])}),
        "baseline_rows_required": all(required_subset(contract.get("required_baseline_row_fields", []), row) for row in baseline_rows),
        "blocked_when_walk_forward_blocked": sample.get("walk_forward_status") == "blocked" and sample.get("report", {}).get("status") == "blocked" and sample.get("artifact_manifest", {}).get("training_rows") == 0,
        "metrics_null_when_blocked": all(row.get("status") == "blocked" and row.get("log_loss") is None and row.get("brier_score") is None for row in baseline_rows),
        "no_vig_preview_present": sample.get("no_vig_preview", {}).get("preview_only") is True and len(sample.get("no_vig_preview", {}).get("no_vig_probabilities", [])) >= 2,
        "artifact_manifest_safe": sample.get("artifact_manifest", {}).get("credential_values_stored") is False and sample.get("artifact_manifest", {}).get("recommendation_output_present") is False and len(sample.get("artifact_manifest", {}).get("content_sha256", "")) == 64,
        "trust_gate_blocks_terminal": sample.get("trust_gate", {}).get("status") == "blocked_sample" and sample.get("trust_gate", {}).get("terminal_prediction_allowed") is False and sample.get("trust_gate", {}).get("bilet_builder_allowed") is False,
        "desktop_sample_shape": desktop.get("schema") == "omnibet.baseline_reports_desktop_sample.v331_v340" and len(desktop.get("baseline_rows", [])) >= 4,
        "rust_module_exposed": "pub mod baseline_reports_v331;" in rust_lib and "pub use baseline_reports_v331::*;" in rust_lib,
        "rust_module_defined": "validate_baseline_reports_contract" in rust_module and "no_vig_from_decimal_prices" in rust_module and "build_baseline_training_report" in rust_module and "write_baseline_training_report" in rust_module,
        "rust_blocks_when_walk_forward_blocked": "walk_forward_evaluator_gates_failed" in rust_module and "terminal_prediction_allowed: false" in rust_module and "bilet_builder_allowed: false" in rust_module,
        "html_page_wired": 'data-page="baseline-reports"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="baseline_reports.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./baseline_reports.js" in app_js and "loadAndRenderBaselineReportsStatus" in app_js and "load-baseline-reports-status" in app_js,
        "renderer_wired": "renderBaselineReportsStatus" in renderer and "renderTrust" in renderer and "renderArtifact" in renderer,
        "docs_updated": "v331-v340 Baseline Training Reports" in docs and "blocked" in docs,
        "readme_updated": "v331-v340 baseline" in readme,
        "workflow_updated": "baseline_training_reports_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 12,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.baseline_training_reports_smoke.v331_v340",
        "milestone": "v331_v340_first_baseline_training_reports",
        "acceptance": checks,
        "summary": {
            "baseline_rows": len(baseline_rows),
            "walk_forward_status": sample.get("walk_forward_status"),
            "report_status": sample.get("report", {}).get("status"),
            "trust_status": sample.get("trust_gate", {}).get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v331_v340_baseline_training_reports.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
