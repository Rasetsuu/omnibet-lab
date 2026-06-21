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
    contract = read_json(root / "configs/bronze_preview_field_schema.v251.json")
    rust = (root / "rust-core/src/bronze_field_schema_v251.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    required = contract.get("required_fields_by_class", {})
    acceptance = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.bronze_preview_field_schema_contract.v251",
        "quarantine_only": contract.get("quarantine_only") is True,
        "import_disabled": contract.get("import_allowed_now") is False,
        "promotion_disabled": contract.get("promotion_allowed") is False,
        "evaluation_disabled": contract.get("evaluation_allowed") is False,
        "training_disabled": contract.get("training_dataset_promotion_allowed") is False,
        "fixture_fields": set(required.get("fixture_result", [])) == {"fixture_id", "home_team", "away_team", "kickoff_utc", "result_status"},
        "odds_fields": set(required.get("odds_snapshot", [])) == {"fixture_id", "provider_id", "bookmaker_id", "market_key", "selection_key", "price_decimal", "snapshot_utc"},
        "event_fields": set(required.get("lineup_event_context", [])) == {"fixture_id", "provider_id", "entity_id", "event_type", "observed_at_utc"},
        "unknown_policy": contract.get("unknown_or_incomplete_policy") == "review_required",
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 9,
        "rust_bundle_type": "BronzePreviewFieldSchemaBundle" in rust,
        "rust_row_type": "BronzePreviewFieldSchemaRow" in rust,
        "rust_validator": "validate_bronze_preview_field_schema_bundle" in rust and "validate_bronze_preview_field_schema_row" in rust,
        "rust_required_fields": "required_fields_for_row_class" in rust and "price_decimal" in rust and "observed_at_utc" in rust,
        "rust_missing_fields": "missing_fields" in rust and "missing required fields" in rust,
        "rust_flags_locked": "quarantine_only: true" in rust and "training_dataset_promotion_allowed: false" in rust,
        "rust_tests": "validates_required_fields_and_marks_review_rows" in rust and "field_schema_rows_keep_all_safety_flags_locked" in rust,
        "lib_exports": "pub mod bronze_field_schema_v251;" in lib and "pub use bronze_field_schema_v251::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.bronze_preview_field_schema_smoke.v251",
        "milestone": "v251_bronze_preview_field_schema",
        "acceptance": checks,
        "summary": {
            "required_classes": sorted(required.keys()),
            "unknown_policy": contract.get("unknown_or_incomplete_policy"),
            "quarantine_only": True,
            "training_dataset_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v251_bronze_preview_field_schema.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
