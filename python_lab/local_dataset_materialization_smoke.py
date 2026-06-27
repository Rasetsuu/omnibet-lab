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


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/local_dataset_materialization.v301_v310.json")
    sample = read_json(root / "data/materialization/v301_v310/local_dataset_materialization.sample.json")
    desktop_sample = read_json(root / "tauri-app/src/dataset-materialization.sample.json")
    docs = (root / "docs/local_dataset_materialization_v301_v310.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/local_materialization_v301.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v301_v310_local_dataset_materialization.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/dataset_materialization.js").read_text(encoding="utf-8")
    generator = (root / "python_lab/local_dataset_materialization_preview.py").read_text(encoding="utf-8")

    ids = html_ids(html)
    manifests = sample.get("source_manifests", [])
    fixtures = sample.get("fixture_result_preview", [])
    odds = sample.get("odds_import_preview", [])
    settlements = sample.get("settlement_label_preview", [])
    clv = sample.get("closing_odds_clv_preview", [])
    candidates = sample.get("candidate_materialization_preview", [])
    readiness = sample.get("coverage_readiness", {})
    acceptance = contract.get("acceptance", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.local_dataset_materialization_contract.v301_v310",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("writes_real_bronze_silver_gold") is False,
        "sample_safe": sample.get("paper_only") is True and sample.get("credential_values_present") is False and sample.get("real_money_recommendations_present") is False and sample.get("live_provider_calls_present") is False and no_secret_values(sample),
        "manifest_required": all(required_subset(contract.get("manifest_required_fields", []), row) for row in manifests),
        "manifest_hashes": all(len(str(row.get("sha256", ""))) == 64 for row in manifests),
        "fixtures_required": all(required_subset(contract.get("fixture_preview_required_fields", []), row) for row in fixtures),
        "odds_required": all(required_subset(contract.get("odds_preview_required_fields", []), row) for row in odds),
        "settlements_required": all(required_subset(contract.get("settlement_preview_required_fields", []), row) for row in settlements),
        "clv_required": all(required_subset(contract.get("clv_preview_required_fields", []), row) for row in clv),
        "candidates_required": all(required_subset(contract.get("candidate_preview_required_fields", []), row) for row in candidates),
        "candidate_types": {"bronze_raw_candidate", "silver_fact_candidate", "gold_feature_candidate", "market_terminal_preview_candidate"}.issubset({row.get("candidate_type") for row in candidates}),
        "codec_targets": {"jsonl.zstd", "parquet.zstd"}.issubset({row.get("codec_target") for row in candidates}),
        "coverage_readiness_blocks_training": readiness.get("ready_for_training") is False and readiness.get("blockers") and readiness.get("minimum_ready_rows") == 1000,
        "desktop_sample_shape": desktop_sample.get("schema") == "omnibet.dataset_materialization_desktop_sample.v301_v310" and len(desktop_sample.get("candidate_rows", [])) >= 4,
        "generated_paths": contract.get("generated_report_path") == ".omnibet-local/reports/local_v301_v310_dataset_materialization.json" and contract.get("market_terminal_reload_path") == ".omnibet-local/reports/local_v301_v310_market_terminal_preview.json",
        "generator_outputs": "build_market_terminal_preview" in generator and "local_v301_v310_dataset_materialization.json" in generator and "local_v301_v310_market_terminal_preview.json" in generator,
        "html_page_wired": 'data-page="dataset-materialization"' in html and all(panel_id in html for panel_id in contract.get("panel_ids", [])) and all(button_id in html for button_id in contract.get("button_ids", [])) and 'src="dataset_materialization.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./dataset_materialization.js" in app_js and "loadAndRenderDatasetMaterialization" in app_js and "generateAndRenderDatasetMaterialization" in app_js,
        "renderer_wired": "renderDatasetMaterialization" in renderer and "renderCandidates" in renderer and "renderReadiness" in renderer,
        "rust_module_exposed": "pub mod local_materialization_v301;" in rust_lib and "pub use local_materialization_v301::*;" in rust_lib,
        "rust_module_validation": "validate_local_dataset_materialization_contract" in rust_module and "writes_real_bronze_silver_gold" in rust_module and "recommend_real_bet" in rust_module,
        "docs_updated": "v301-v310 Local Dataset Materialization Preview" in docs and "Market Terminal reload" in docs,
        "readme_updated": "v301-v310 real local dataset materialization preview" in readme,
        "workflow_updated": "local_dataset_materialization_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 12,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.local_dataset_materialization_smoke.v301_v310",
        "milestone": "v301_v310_local_dataset_materialization_preview",
        "acceptance": checks,
        "summary": {
            "manifests": len(manifests),
            "fixtures": len(fixtures),
            "odds": len(odds),
            "settlements": len(settlements),
            "clv": len(clv),
            "candidates": len(candidates),
            "ready_for_training": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v301_v310_local_dataset_materialization.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
