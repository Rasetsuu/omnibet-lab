#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rows(obj: Dict[str, Any]) -> list[Dict[str, Any]]:
    return obj.get("rows", [])


def required_subset(required: Iterable[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def validation_report(contract: Dict[str, Any], fixtures: list[Dict[str, Any]], odds: list[Dict[str, Any]], settlements: list[Dict[str, Any]], identities: list[Dict[str, Any]], manifest_ok: bool) -> Dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    fixture_ids = {f.get("fixture_id") for f in fixtures}
    if len(fixture_ids) != len(fixtures):
        errors.append("duplicate_fixture_id")
    kickoff = {f.get("fixture_id"): f.get("kickoff_utc") for f in fixtures}

    for row in odds:
        fixture_id = row.get("fixture_id")
        if fixture_id not in fixture_ids:
            errors.append(f"odds_missing_fixture:{fixture_id}")
        if row.get("decimal_odds", 0) <= 1.0:
            errors.append(f"invalid_decimal_odds:{fixture_id}:{row.get('selection_id')}")
        if row.get("is_closing_snapshot") is True and fixture_id in kickoff and row.get("captured_at_utc") > kickoff[fixture_id]:
            errors.append(f"odds_after_kickoff:{fixture_id}:{row.get('selection_id')}")

    for row in settlements:
        fixture_id = row.get("fixture_id")
        if fixture_id not in fixture_ids:
            errors.append(f"settlement_missing_fixture:{fixture_id}")
        if fixture_id in kickoff and row.get("label_available_after_utc") < kickoff[fixture_id]:
            errors.append(f"label_before_kickoff:{fixture_id}:{row.get('selection_id')}")
        if row.get("settlement_result") not in {"win", "loss", "push", "void"}:
            errors.append(f"invalid_settlement_result:{fixture_id}:{row.get('selection_id')}")

    for row in identities:
        if row.get("confidence", 0) < 0.8 and row.get("review_status") != "needs_review":
            errors.append(f"low_confidence_identity_without_review:{row.get('raw_name')}")

    if not manifest_ok:
        warnings.append("source_manifest_not_verified")

    ok = not errors
    return {
        "schema": "omnibet.historical_import_validation_report.v401_v410",
        "paper_only": True,
        "status": "validated_for_materialization" if ok else "blocked_import_validation",
        "source_manifest_verified": manifest_ok,
        "fixture_rows": len(fixtures),
        "odds_rows": len(odds),
        "settlement_rows": len(settlements),
        "identity_rows": len(identities),
        "validation_errors": errors,
        "validation_warnings": warnings,
        "ready_for_materialization": ok,
        "ready_for_training": False,
        "trust_status": "sample_only",
        "credential_values_present": False,
        "recommendation_output_present": False,
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_source_import.v401_v410.json")
    manifest = read_json(root / "data/historical/v401_v410/historical_import.sample.json")
    fixtures_payload = read_json(root / "data/historical/v401_v410/fixtures.sample.json")
    odds_payload = read_json(root / "data/historical/v401_v410/odds.sample.json")
    settlements_payload = read_json(root / "data/historical/v401_v410/settlements.sample.json")
    identity_payload = read_json(root / "data/historical/v401_v410/identity_map.sample.json")
    rust_module = (root / "rust-core/src/historical_source_import_v401.rs").read_text(encoding="utf-8")
    lib_rs = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    docs = (root / "docs/historical_source_import_v401_v410.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v401_v410_historical_source_import.yml").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")

    fixture_rows = rows(fixtures_payload)
    odds_rows = rows(odds_payload)
    settlement_rows = rows(settlements_payload)
    identity_rows = rows(identity_payload)
    report = validation_report(contract, fixture_rows, odds_rows, settlement_rows, identity_rows, True)
    required_report_fields = contract.get("report_required_fields", [])
    acceptance = contract.get("acceptance", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_source_import_contract.v401_v410",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and contract.get("training_allowed") is False,
        "manifest_schema_ok": manifest.get("schema") == "omnibet.historical_import_manifest.v401_v410" and manifest.get("training_allowed") is False,
        "fixture_rows_schema_ok": fixtures_payload.get("schema") == "omnibet.fixture_history_rows.v401_v410" and all(required_subset(contract.get("fixture_required_fields", []), row) for row in fixture_rows),
        "odds_rows_schema_ok": odds_payload.get("schema") == "omnibet.odds_history_rows.v401_v410" and all(required_subset(contract.get("odds_required_fields", []), row) for row in odds_rows),
        "settlement_rows_schema_ok": settlements_payload.get("schema") == "omnibet.settlement_history_rows.v401_v410" and all(required_subset(contract.get("settlement_required_fields", []), row) for row in settlement_rows),
        "identity_rows_schema_ok": identity_payload.get("schema") == "omnibet.identity_mapping_rows.v401_v410" and all(required_subset(contract.get("identity_required_fields", []), row) for row in identity_rows),
        "sample_counts_ok": len(fixture_rows) == 3 and len(odds_rows) == 9 and len(settlement_rows) == 9 and len(identity_rows) == 6,
        "timing_checks_ok": report["status"] == "validated_for_materialization" and not report["validation_errors"],
        "report_required_fields_ok": required_subset(required_report_fields, report),
        "training_blocked": report["ready_for_materialization"] is True and report["ready_for_training"] is False and report["trust_status"] == "sample_only",
        "rust_module_added": "HistoricalImportValidationReportV401" in rust_module and "validate_historical_import_pack" in rust_module and "load_and_validate_historical_import" in rust_module and "odds_after_kickoff" in rust_module,
        "rust_module_exposed": "pub mod historical_source_import_v401;" in lib_rs and "pub use historical_source_import_v401::*;" in lib_rs,
        "rust_tests_added": "validates_safe_historical_import_pack" in rust_module and "blocks_odds_after_kickoff" in rust_module,
        "docs_updated": "v401-v410 Historical Source Import" in docs and "ready_for_training = false" in docs and "local files" in docs.lower(),
        "readme_updated": "v401-v410" in readme and "historical source import" in readme.lower(),
        "workflow_updated": "historical_source_import_smoke.py" in workflow and "cargo test --manifest-path rust-core/Cargo.toml historical_source_import" in workflow,
        "no_secret_values": no_secret_values(contract) and no_secret_values(manifest) and no_secret_values(fixtures_payload) and no_secret_values(odds_payload) and no_secret_values(settlements_payload) and no_secret_values(identity_payload) and no_secret_values(report),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_source_import_smoke.v401_v410",
        "milestone": "v401_v410_real_historical_source_import_v1",
        "acceptance": checks,
        "validation_report": report,
        "summary": {
            "fixtures": len(fixture_rows),
            "odds": len(odds_rows),
            "settlements": len(settlement_rows),
            "identities": len(identity_rows),
            "ready_for_materialization": report["ready_for_materialization"],
            "ready_for_training": report["ready_for_training"],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v401_v410_historical_source_import.json")
    ap.add_argument("--validation-out", default="reports/historical_source_import_v401_v410_validation.json")
    args = ap.parse_args()
    smoke = build_report(Path(args.root))
    write_json(Path(args.out), smoke)
    write_json(Path(args.validation_out), smoke["validation_report"])
    print(json.dumps(smoke, indent=2, ensure_ascii=False))
    if not smoke["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
