#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/provider_normalization_preview.v255.json")
    odds_fixture = read_json(root / "data/provider_fixtures/v254/odds_provider_snapshot.sample.json")
    football_fixture = read_json(root / "data/provider_fixtures/v254/football_fixture_event.sample.json")
    rust = (root / "rust-core/src/provider_normalize_v255.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    row_types = contract.get("normalized_row_types", {})
    desktop = contract.get("desktop_surface", {})
    acceptance = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.provider_normalization_preview_contract.v255",
        "paper_only": contract.get("paper_only") is True,
        "ci_offline": contract.get("network_calls_allowed_in_ci") is False,
        "no_repo_credentials": contract.get("credentials_stored_in_repo") is False,
        "live_fetch_disabled": contract.get("live_fetch_enabled") is False,
        "quarantine_only": contract.get("quarantine_only") is True,
        "promotion_disabled": contract.get("promotion_allowed") is False,
        "evaluation_disabled": contract.get("evaluation_allowed") is False,
        "training_disabled": contract.get("training_dataset_promotion_allowed") is False,
        "row_types": set(row_types.keys()) == {"odds_snapshot_candidate", "fixture_result_candidate", "event_context_candidate"},
        "odds_fixture_rows": isinstance(odds_fixture, list) and len(odds_fixture) == 1 and len(odds_fixture[0]["bookmakers"][0]["markets"][0]["outcomes"]) == 3,
        "football_fixture_rows": len(football_fixture["response"]) == 1 and len(football_fixture["response"][0]["events"]) == 1,
        "desktop_safe": desktop.get("show_normalized_preview_counts") is True and desktop.get("allow_export_preview") is True and desktop.get("allow_promote_to_bronze") is False and desktop.get("allow_run_evaluation") is False and desktop.get("allow_train_model") is False,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 9,
        "rust_bundle_type": "ProviderNormalizationPreviewBundleV255" in rust,
        "rust_row_type": "ProviderNormalizedPreviewRowV255" in rust,
        "rust_builder": "build_provider_normalization_preview_v255" in rust,
        "rust_normalizers": "normalize_odds_fixture" in rust and "normalize_football_fixture" in rust,
        "rust_row_counts": "odds_snapshot_candidate" in rust and "fixture_result_candidate" in rust and "event_context_candidate" in rust,
        "rust_safety": "training_dataset_promotion_allowed: false" in rust and "evaluation_allowed: false" in rust,
        "rust_tests": "normalizes_offline_provider_fixtures_to_preview_rows" in rust and "malformed_fixture_blocks_without_unlocking_safety" in rust,
        "lib_exports": "pub mod provider_normalize_v255;" in lib and "pub use provider_normalize_v255::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.provider_normalization_preview_smoke.v255",
        "milestone": "v255_offline_normalization_preview",
        "acceptance": checks,
        "summary": {
            "expected_rows": {
                "odds_snapshot_candidate": 3,
                "fixture_result_candidate": 1,
                "event_context_candidate": 1,
            },
            "ci_live_calls_allowed": False,
            "promotion_allowed": False,
            "evaluation_allowed": False,
            "training_dataset_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v255_provider_normalization_preview.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
