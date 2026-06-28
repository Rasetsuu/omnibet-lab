#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read_csv_rows(path: Path) -> List[Dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def missing_columns(required: Iterable[str], rows: List[Dict[str, str]]) -> List[str]:
    columns = set(rows[0].keys()) if rows else set()
    return [col for col in required if col not in columns]


def bool_value(value: str) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def explicit_safety_flags_ok(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False)
    return (
        '"credential_values_present": true' not in serialized
        and '"recommendation_output_present": true' not in serialized
        and '"ready_for_training": true' not in serialized
    )


def build_preview(root: Path) -> tuple[Dict[str, Any], Dict[str, Any]]:
    contract = read_json(root / "configs/historical_file_adapter.v451_v460.json")
    catalog = read_json(root / "data/historical/v451_v460/adapter_catalog.sample.json")
    accepted = contract["accepted_inputs"]
    fixtures = read_csv_rows(root / accepted["fixture_csv"])
    odds = read_csv_rows(root / accepted["odds_csv"])
    settlements = read_csv_rows(root / accepted["settlement_csv"])
    identities = read_csv_rows(root / accepted["identity_csv"])

    errors: List[str] = []
    warnings: List[str] = []

    for key, required in [
        ("fixture", contract["fixture_required_columns"]),
        ("odds", contract["odds_required_columns"]),
        ("settlement", contract["settlement_required_columns"]),
        ("identity", contract["identity_required_columns"]),
    ]:
        rows = {"fixture": fixtures, "odds": odds, "settlement": settlements, "identity": identities}[key]
        missing = missing_columns(required, rows)
        if missing:
            errors.append(f"{key}_missing_columns:{','.join(missing)}")

    fixture_ids = [row["fixture_id"] for row in fixtures]
    fixture_id_set = set(fixture_ids)
    if len(fixture_ids) != len(fixture_id_set):
        errors.append("duplicate_fixture_id")

    kickoff_by_fixture = {row["fixture_id"]: row["kickoff_utc"] for row in fixtures}

    for row in fixtures:
        if row["result_status"] != "final":
            warnings.append(f"non_final_fixture:{row['fixture_id']}")

    for row in odds:
        fixture_id = row["fixture_id"]
        if fixture_id not in fixture_id_set:
            errors.append(f"odds_missing_fixture:{fixture_id}")
            continue
        try:
            decimal_odds = float(row["decimal_odds"])
        except ValueError:
            errors.append(f"invalid_decimal_odds:{fixture_id}:{row['selection_id']}")
            continue
        if decimal_odds <= 1.0:
            errors.append(f"invalid_decimal_odds:{fixture_id}:{row['selection_id']}")
        if bool_value(row["is_closing_snapshot"]) and row["captured_at_utc"] > kickoff_by_fixture[fixture_id]:
            errors.append(f"closing_odds_after_kickoff:{fixture_id}:{row['selection_id']}")

    odds_keys = {(row["fixture_id"], row["market_family"], row["selection_id"]) for row in odds}
    for row in settlements:
        fixture_id = row["fixture_id"]
        if fixture_id not in fixture_id_set:
            errors.append(f"settlement_missing_fixture:{fixture_id}")
        key = (fixture_id, row["market_family"], row["selection_id"])
        if key not in odds_keys:
            errors.append(f"settlement_missing_odds:{fixture_id}:{row['selection_id']}")
        if row["settlement_result"] not in {"win", "loss", "push", "void"}:
            errors.append(f"invalid_settlement_result:{fixture_id}:{row['selection_id']}")
        matching_odds = [odds_row for odds_row in odds if (odds_row["fixture_id"], odds_row["market_family"], odds_row["selection_id"]) == key]
        if matching_odds and row["label_available_after_utc"] < matching_odds[0]["captured_at_utc"]:
            errors.append(f"label_before_prediction_time:{fixture_id}:{row['selection_id']}")

    for row in identities:
        confidence = float(row["confidence"])
        if confidence < 0.80 and row["review_status"] != "needs_review":
            errors.append(f"low_confidence_identity_without_review:{row['raw_name']}")
        if not row["canonical_id"] or not row["raw_name"]:
            errors.append(f"empty_identity_field:{row['raw_name']}")

    normalized_preview = {
        "schema": "omnibet.historical_file_adapter_normalized_preview.v451_v460",
        "paper_only": True,
        "fixtures": fixtures,
        "odds": [dict(row, decimal_odds=float(row["decimal_odds"]), is_closing_snapshot=bool_value(row["is_closing_snapshot"])) for row in odds],
        "settlements": settlements,
        "identities": [dict(row, confidence=float(row["confidence"])) for row in identities],
        "ready_for_training": False,
        "trust_status": "sample_only",
        "credential_values_present": False,
        "recommendation_output_present": False,
    }

    ok = not errors
    report = {
        "schema": "omnibet.historical_file_adapter_report.v451_v460",
        "paper_only": True,
        "status": "adapter_preview_valid" if ok else "adapter_preview_blocked",
        "adapter_catalog_schema": catalog.get("schema"),
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
        "desktop_upload_ux_placeholder": contract.get("desktop_placeholder", {}),
    }
    return report, normalized_preview


def build_smoke(root: Path, report_path: Path, preview_path: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_file_adapter.v451_v460.json")
    report, preview = build_preview(root)
    write_json(report_path, report)
    write_json(preview_path, preview)
    docs = (root / "docs/historical_file_adapter_v451_v460.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v451_v460_historical_file_adapter.yml").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_file_adapter_contract.v451_v460",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("training_allowed") is False,
        "sample_rows_ok": report["fixture_rows"] == 3 and report["odds_rows"] == 9 and report["settlement_rows"] == 9 and report["identity_rows"] == 6,
        "adapter_preview_valid": report["status"] == "adapter_preview_valid" and report["ready_for_materialization"] is True,
        "training_blocked": report["ready_for_training"] is False and report["trust_status"] == "sample_only",
        "normalized_preview_written": preview.get("schema") == "omnibet.historical_file_adapter_normalized_preview.v451_v460" and len(preview.get("fixtures", [])) == 3 and len(preview.get("odds", [])) == 9,
        "desktop_placeholder_present": contract.get("desktop_placeholder", {}).get("future_page_id") == "historical-file-adapter",
        "docs_updated": "v451-v460 Historical File Adapter" in docs and "ready_for_training = false" in docs and "local CSV" in docs,
        "workflow_updated": "historical_file_adapter_smoke.py" in workflow and "compile_python_sources.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract) and explicit_safety_flags_ok(report) and explicit_safety_flags_ok(preview),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_file_adapter_smoke.v451_v460",
        "milestone": "v451_v460_real_local_historical_file_adapter_import_ux",
        "acceptance": checks,
        "summary": {
            "fixture_rows": report["fixture_rows"],
            "odds_rows": report["odds_rows"],
            "settlement_rows": report["settlement_rows"],
            "identity_rows": report["identity_rows"],
            "ready_for_materialization": report["ready_for_materialization"],
            "ready_for_training": report["ready_for_training"],
            "trust_status": report["trust_status"],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v451_v460_historical_file_adapter.json")
    ap.add_argument("--adapter-report-out", default="reports/historical_file_adapter_v451_v460_report.json")
    ap.add_argument("--normalized-preview-out", default="reports/historical_file_adapter_v451_v460_normalized_preview.json")
    args = ap.parse_args()
    root = Path(args.root)
    smoke = build_smoke(root, Path(args.adapter_report_out), Path(args.normalized_preview_out))
    write_json(Path(args.out), smoke)
    print(json.dumps(smoke, indent=2, ensure_ascii=False))
    if not smoke["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
