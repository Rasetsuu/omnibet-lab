#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_SOURCES = {
    "football_data_co_uk",
    "api_football",
    "the_odds_api",
    "statsbomb_open_data",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = [
        '"api_key":',
        '"secret":',
        '"bearer_token":',
        '"credential_value":',
        "secret_value",
        "bearer ",
        "sk-",
    ]
    return not any(marker in serialized for marker in forbidden)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_dataset_foundation.v271_v280.json")
    sample = read_json(root / "data/historical/v271_v280/historical_dataset_foundation.sample.json")
    docs = (root / "docs/historical_dataset_foundation_v271_v280.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/historical_dataset_v271.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v271_v280_historical_dataset_foundation.yml").read_text(encoding="utf-8")

    sources = contract.get("source_coverage_matrix", [])
    source_ids = {row.get("source_id") for row in sources}
    targets = contract.get("league_tournament_targets", {})
    league_targets = targets.get("league_targets", [])
    tournament_targets = targets.get("tournament_targets", [])
    manifest_bundle = contract.get("historical_source_manifest_bundle", {})
    settlement = contract.get("settlement_and_closing_odds_targets", {})
    readiness = contract.get("coverage_readiness_report", {})
    build_plan = contract.get("first_dataset_build_plan", {})
    acceptance = contract.get("acceptance", {})

    sample_sources = sample.get("source_coverage_rows", [])
    sample_manifests = sample.get("source_manifests", [])
    sample_coverage = sample.get("coverage_readiness_report", {})
    sample_plan = sample.get("first_dataset_build_plan", {})
    manifest_required = manifest_bundle.get("required_manifest_fields", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.historical_dataset_foundation_contract.v271_v280",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "no_live_calls_or_credentials": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and sample.get("credential_values_present") is False and no_secret_values(sample),
        "primary_sources_present": REQUIRED_SOURCES.issubset(source_ids),
        "source_roles_nonempty": all(row.get("roles") for row in sources),
        "sample_sources_present": REQUIRED_SOURCES.issubset({row.get("source_id") for row in sample_sources}),
        "league_targets_defined": any(target.get("minimum_seasons", 0) >= 5 and "eng_premier" in target.get("competitions", []) for target in league_targets),
        "tournament_targets_defined": any(target.get("minimum_tournament_editions", 0) >= 3 and "world_cup" in target.get("competitions", []) for target in tournament_targets),
        "manifest_bundle_rust_target": manifest_bundle.get("target_runtime") == "rust",
        "manifest_fields_required": {"sha256", "row_count", "observed_at_policy", "promotion_target"}.issubset(set(manifest_required)),
        "sample_manifests_complete": all(required_subset(manifest_required, row) for row in sample_manifests),
        "sample_manifest_hashes": all(len(str(row.get("sha256", ""))) == 64 for row in sample_manifests),
        "sample_manifest_rows_positive": all(row.get("row_count", 0) > 0 for row in sample_manifests),
        "settlement_targets_defined": "1x2" in settlement.get("market_families", []) and settlement.get("paper_clv_required") is True and settlement.get("label_after_settlement_only") is True,
        "sample_settlement_targets_defined": any(row.get("market_family") == "1x2" and row.get("paper_clv_required") is True for row in sample.get("settlement_and_closing_odds_targets", [])),
        "coverage_thresholds_defined": readiness.get("minimum_ready_rows", 0) >= 1000 and readiness.get("minimum_settlement_coverage_ratio", 0.0) >= 0.95,
        "sample_coverage_not_training_ready": sample_coverage.get("ready_for_training") is False and sample_coverage.get("blockers"),
        "dataset_plan_rust_no_leak": build_plan.get("target_runtime") == "rust" and set(["random_split", "train_on_unsettled_games", "store_credentials", "live_provider_calls_in_ci"]).issubset(set(build_plan.get("forbidden_actions", []))),
        "sample_dataset_plan_not_ready": sample_plan.get("ready_for_training_after_phase") is False and sample_plan.get("target_runtime") == "rust",
        "rust_module_exposed": "pub mod historical_dataset_v271;" in rust_lib and "pub use historical_dataset_v271::*;" in rust_lib,
        "rust_module_validation": "validate_historical_dataset_foundation_contract" in rust_module and "football_data_co_uk" in rust_module and "train_on_unsettled_games" in rust_module,
        "docs_updated": "v271-v280 Historical Dataset Foundation" in docs and "Settlement and closing-odds" in docs,
        "readme_updated": "v271-v280 historical dataset foundation" in readme,
        "workflow_updated": "historical_dataset_foundation_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 8,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_dataset_foundation_smoke.v271_v280",
        "milestone": "v271_v280_historical_dataset_foundation",
        "acceptance": checks,
        "summary": {
            "contract_sources": len(sources),
            "sample_sources": len(sample_sources),
            "sample_manifests": len(sample_manifests),
            "league_targets": len(league_targets),
            "tournament_targets": len(tournament_targets),
            "ready_for_training": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v271_v280_historical_dataset_foundation.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
