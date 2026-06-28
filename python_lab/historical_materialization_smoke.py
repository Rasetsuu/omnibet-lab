#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
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


def identity_lookup(identity_rows: list[Dict[str, Any]]) -> dict[str, tuple[str, str]]:
    return {row["raw_name"]: (row["canonical_id"], row["canonical_name"]) for row in identity_rows}


def build_bronze_fixtures(fixtures: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "fixture_id": row["fixture_id"],
            "source_id": row["source_id"],
            "competition": row["competition"],
            "season": row["season"],
            "kickoff_utc": row["kickoff_utc"],
            "home_team_raw": row["home_team_raw"],
            "away_team_raw": row["away_team_raw"],
            "result_status": row["result_status"],
        }
        for row in fixtures
    ]


def build_bronze_odds(odds: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "fixture_id": row["fixture_id"],
            "source_id": row["source_id"],
            "market_family": row["market_family"],
            "market_id": row["market_id"],
            "selection_id": row["selection_id"],
            "selection_raw": row["selection_raw"],
            "bookmaker": row["bookmaker"],
            "captured_at_utc": row["captured_at_utc"],
            "decimal_odds": row["decimal_odds"],
            "is_closing_snapshot": row["is_closing_snapshot"],
        }
        for row in odds
    ]


def build_bronze_settlements(settlements: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "fixture_id": row["fixture_id"],
            "market_family": row["market_family"],
            "selection_id": row["selection_id"],
            "settled_at_utc": row["settled_at_utc"],
            "settlement_result": row["settlement_result"],
            "label_available_after_utc": row["label_available_after_utc"],
        }
        for row in settlements
    ]


def build_silver_fixtures(fixtures: list[Dict[str, Any]], identities: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    lookup = identity_lookup(identities)
    output = []
    for row in fixtures:
        home = lookup.get(row["home_team_raw"], (row["home_team_canonical_id"], row["home_team_raw"]))
        away = lookup.get(row["away_team_raw"], (row["away_team_canonical_id"], row["away_team_raw"]))
        output.append(
            {
                "fixture_id": row["fixture_id"],
                "competition": row["competition"],
                "season": row["season"],
                "kickoff_utc": row["kickoff_utc"],
                "home_team_id": home[0],
                "away_team_id": away[0],
                "home_team_name": home[1],
                "away_team_name": away[1],
                "result_status": row["result_status"],
            }
        )
    return output


def build_silver_odds(odds: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    return [
        {
            "fixture_id": row["fixture_id"],
            "market_family": row["market_family"],
            "market_id": row["market_id"],
            "selection_id": row["selection_id"],
            "bookmaker": row["bookmaker"],
            "captured_at_utc": row["captured_at_utc"],
            "decimal_odds": row["decimal_odds"],
            "no_vig_group_key": f"{row['fixture_id']}:{row['bookmaker']}:{row['market_family']}:{row['captured_at_utc']}",
            "is_closing_snapshot": row["is_closing_snapshot"],
        }
        for row in odds
    ]


def build_gold_candidates(odds: list[Dict[str, Any]], settlements: list[Dict[str, Any]]) -> list[Dict[str, Any]]:
    settled = {(row["fixture_id"], row["market_family"], row["selection_id"]): row for row in settlements}
    output = []
    for row in odds:
        settlement = settled.get((row["fixture_id"], row["market_family"], row["selection_id"]))
        if not settlement:
            continue
        output.append(
            {
                "candidate_id": f"candidate:{row['fixture_id']}:{row['selection_id']}",
                "fixture_id": row["fixture_id"],
                "prediction_time_utc": row["captured_at_utc"],
                "label_available_after_utc": settlement["label_available_after_utc"],
                "market_family": row["market_family"],
                "selection_id": row["selection_id"],
                "decimal_odds": row["decimal_odds"],
                "settlement_result": settlement["settlement_result"],
                "feature_leakage_safe": settlement["label_available_after_utc"] >= row["captured_at_utc"],
            }
        )
    return output


def table_summary(table_id: str, row_count: int, path: str) -> Dict[str, Any]:
    return {"table_id": table_id, "row_count": row_count, "status": "preview_written", "preview_path": path}


def build_materialization(root: Path) -> tuple[Dict[str, Any], dict[str, list[Dict[str, Any]]]]:
    fixtures = rows(read_json(root / "data/historical/v401_v410/fixtures.sample.json"))
    odds = rows(read_json(root / "data/historical/v401_v410/odds.sample.json"))
    settlements = rows(read_json(root / "data/historical/v401_v410/settlements.sample.json"))
    identities = rows(read_json(root / "data/historical/v401_v410/identity_map.sample.json"))
    bronze_fixtures = build_bronze_fixtures(fixtures)
    bronze_odds = build_bronze_odds(odds)
    bronze_settlements = build_bronze_settlements(settlements)
    silver_fixtures = build_silver_fixtures(fixtures, identities)
    silver_odds = build_silver_odds(odds)
    gold_candidates = build_gold_candidates(odds, settlements)
    output_paths = {
        "bronze_fixtures": "reports/materialized/v411_v420/bronze_fixtures.preview.json",
        "bronze_odds": "reports/materialized/v411_v420/bronze_odds.preview.json",
        "bronze_settlements": "reports/materialized/v411_v420/bronze_settlements.preview.json",
        "silver_fixtures": "reports/materialized/v411_v420/silver_fixtures.preview.json",
        "silver_odds": "reports/materialized/v411_v420/silver_odds.preview.json",
        "gold_candidates": "reports/materialized/v411_v420/gold_evaluation_candidates.preview.json",
    }
    manifest = {
        "schema": "omnibet.historical_materialization_manifest.v411_v420",
        "paper_only": True,
        "status": "materialized_preview",
        "bronze_tables": [
            table_summary("bronze_fixtures_v411", len(bronze_fixtures), output_paths["bronze_fixtures"]),
            table_summary("bronze_odds_v412", len(bronze_odds), output_paths["bronze_odds"]),
            table_summary("bronze_settlements_v413", len(bronze_settlements), output_paths["bronze_settlements"]),
        ],
        "silver_tables": [
            table_summary("silver_fixtures_v415", len(silver_fixtures), output_paths["silver_fixtures"]),
            table_summary("silver_odds_v416", len(silver_odds), output_paths["silver_odds"]),
        ],
        "gold_tables": [table_summary("gold_evaluation_candidates_v417", len(gold_candidates), output_paths["gold_candidates"])],
        "content_hashes_present": False,
        "preferred_large_scale_codec": "jsonl.zstd",
        "future_large_scale_codec": "parquet.zstd",
        "ready_for_training": False,
        "credential_values_present": False,
        "recommendation_output_present": False,
    }
    report = {
        "schema": "omnibet.historical_materialization_report.v411_v420",
        "paper_only": True,
        "status": "materialized_preview",
        "source_import_status": "validated_for_materialization",
        "bronze_fixture_rows": len(bronze_fixtures),
        "bronze_odds_rows": len(bronze_odds),
        "bronze_settlement_rows": len(bronze_settlements),
        "silver_fixture_rows": len(silver_fixtures),
        "silver_odds_rows": len(silver_odds),
        "gold_candidate_rows": len(gold_candidates),
        "materialization_manifest": manifest,
        "ready_for_walk_forward": True,
        "ready_for_training": False,
        "trust_status": "sample_only",
        "validation_errors": [],
        "credential_values_present": False,
        "recommendation_output_present": False,
    }
    tables = {
        "bronze_fixtures": bronze_fixtures,
        "bronze_odds": bronze_odds,
        "bronze_settlements": bronze_settlements,
        "silver_fixtures": silver_fixtures,
        "silver_odds": silver_odds,
        "gold_candidates": gold_candidates,
    }
    return report, tables


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_materialization.v411_v420.json")
    rust_module = (root / "rust-core/src/historical_materialization_v411.rs").read_text(encoding="utf-8")
    lib_rs = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    docs = (root / "docs/historical_materialization_v411_v420.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v411_v420_historical_materialization.yml").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    report, tables = build_materialization(root)
    acceptance = contract.get("acceptance", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_materialization_contract.v411_v420",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and contract.get("training_allowed") is False,
        "depends_on_v401": "omnibet.historical_import_validation_report.v401_v410" in contract.get("depends_on", []),
        "bronze_tables_ok": len(tables["bronze_fixtures"]) == 3 and len(tables["bronze_odds"]) == 9 and len(tables["bronze_settlements"]) == 9,
        "silver_tables_ok": len(tables["silver_fixtures"]) == 3 and len(tables["silver_odds"]) == 9,
        "gold_candidates_ok": len(tables["gold_candidates"]) == 9 and all(row["feature_leakage_safe"] is True for row in tables["gold_candidates"]),
        "required_fields_ok": all(required_subset(contract.get("bronze_fixture_required_fields", []), row) for row in tables["bronze_fixtures"]) and all(required_subset(contract.get("silver_fixture_required_fields", []), row) for row in tables["silver_fixtures"]) and all(required_subset(contract.get("gold_candidate_required_fields", []), row) for row in tables["gold_candidates"]),
        "manifest_fields_ok": required_subset(contract.get("manifest_required_fields", []), report["materialization_manifest"]),
        "training_blocked": report["ready_for_walk_forward"] is True and report["ready_for_training"] is False and report["trust_status"] == "sample_only",
        "rust_module_added": "HistoricalMaterializationReportV411" in rust_module and "build_historical_materialization_report_v411" in rust_module and "write_historical_materialization_preview_v411" in rust_module,
        "rust_unique_names": "parse_historical_materialization_contract_v411" in rust_module and "validate_historical_materialization_contract_v411" in rust_module and "parse_historical_import_contract(root" not in rust_module,
        "rust_module_exposed": "pub mod historical_materialization_v411;" in lib_rs and "pub use historical_materialization_v411::*;" in lib_rs,
        "rust_tests_added": "silver_fixtures_apply_identity_map_v411" in rust_module and "gold_candidates_require_settlements_and_stay_safe_v411" in rust_module,
        "docs_updated": "v411-v420 Historical Materialization" in docs and "ready_for_training = false" in docs and "Bronze" in docs and "Silver" in docs and "Gold" in docs,
        "readme_updated": "v411-v420" in readme and "historical materialization" in readme.lower(),
        "workflow_updated": "historical_materialization_smoke.py" in workflow and "cargo test --manifest-path rust-core/Cargo.toml historical_materialization" in workflow,
        "no_secret_values": no_secret_values(contract) and no_secret_values(report) and all(no_secret_values(table) for table in tables.values()),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_materialization_smoke.v411_v420",
        "milestone": "v411_v420_historical_materialization_from_validated_local_files",
        "acceptance": checks,
        "materialization_report": report,
        "summary": {
            "bronze_fixtures": len(tables["bronze_fixtures"]),
            "bronze_odds": len(tables["bronze_odds"]),
            "bronze_settlements": len(tables["bronze_settlements"]),
            "silver_fixtures": len(tables["silver_fixtures"]),
            "silver_odds": len(tables["silver_odds"]),
            "gold_candidates": len(tables["gold_candidates"]),
            "ready_for_walk_forward": report["ready_for_walk_forward"],
            "ready_for_training": report["ready_for_training"],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v411_v420_historical_materialization.json")
    ap.add_argument("--report-out", default="reports/historical_materialization_v411_v420_report.json")
    args = ap.parse_args()
    smoke = build_report(Path(args.root))
    write_json(Path(args.out), smoke)
    write_json(Path(args.report_out), smoke["materialization_report"])
    print(json.dumps(smoke, indent=2, ensure_ascii=False))
    if not smoke["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
