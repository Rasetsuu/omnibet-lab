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


def build_desktop_payload(sample: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "schema": "omnibet.dataset_materialization_generated_report.v301_v310",
        "paper_only": True,
        "source": "generated_local_preview",
        "generated_at": sample.get("generated_at"),
        "summary": sample.get("summary", {}),
        "manifest_rows": [
            {
                "source_id": row.get("source_id"),
                "provider": row.get("provider"),
                "source_role": row.get("source_role"),
                "expected_codec": row.get("expected_codec"),
                "row_count": row.get("row_count"),
                "readiness": row.get("readiness"),
            }
            for row in sample.get("source_manifests", [])
        ],
        "fixture_rows": [
            {
                "canonical_fixture_id": row.get("canonical_fixture_id"),
                "label": f"{row.get('home_team')} vs {row.get('away_team')}",
                "competition_id": row.get("competition_id"),
                "result_status": row.get("result_status"),
                "candidate_state": row.get("candidate_state"),
            }
            for row in sample.get("fixture_result_preview", [])
        ],
        "odds_rows": sample.get("odds_import_preview", []),
        "settlement_rows": sample.get("settlement_label_preview", []),
        "clv_rows": sample.get("closing_odds_clv_preview", []),
        "candidate_rows": sample.get("candidate_materialization_preview", []),
        "coverage_readiness": sample.get("coverage_readiness", {}),
    }


def build_market_terminal_preview(sample: Dict[str, Any]) -> Dict[str, Any]:
    fixtures = []
    for row in sample.get("fixture_result_preview", []):
        fixtures.append(
            {
                "canonical_fixture_id": row.get("canonical_fixture_id"),
                "label": f"{row.get('home_team')} vs {row.get('away_team')}",
                "competition": row.get("competition_id"),
                "status": row.get("result_status"),
                "kickoff_time": row.get("kickoff_time"),
                "source_freshness": "generated_local_preview",
                "available_markets": sorted({odds.get("market_key") for odds in sample.get("odds_import_preview", []) if odds.get("canonical_fixture_id") == row.get("canonical_fixture_id")}),
                "trust_summary": "local_materialization_preview_only",
            }
        )
    prediction_rows = []
    for odds in sample.get("odds_import_preview", []):
        prediction_rows.append(
            {
                "canonical_fixture_id": odds.get("canonical_fixture_id"),
                "market_key": odds.get("market_key"),
                "selection_key": odds.get("selection_key"),
                "model_probability": None,
                "fair_odds_decimal": None,
                "bookmaker_odds_decimal": odds.get("price_decimal"),
                "no_vig_probability": None,
                "edge_vs_no_vig": None,
                "trust_status": "sample_only",
                "blockers": ["generated_preview_not_training_ready"],
                "allowed_action": "inspect",
                "movement_preview": {
                    "opening_price_decimal": None,
                    "current_price_decimal": odds.get("price_decimal"),
                    "closing_price_decimal": None,
                    "movement_status": "generated_local_preview_only",
                },
            }
        )
    return {
        "schema": "omnibet.market_terminal_generated_preview.v310",
        "sample_id": "v310_market_terminal_reload_from_materialization_preview",
        "paper_only": True,
        "credential_values_present": False,
        "real_money_recommendations_present": False,
        "summary": {
            "fixtures": len(fixtures),
            "prediction_rows": len(prediction_rows),
            "paper_watch_rows": 0,
            "paper_ledger_rows": 0,
            "bilet_builder_enabled": False,
            "ready_for_real_predictions": False,
        },
        "fixtures": fixtures,
        "prediction_rows": prediction_rows,
        "paper_watchlist": [],
        "paper_ledger_preview": [],
        "bilet_builder_placeholder": {
            "enabled": False,
            "disabled_reason": "generated_preview_not_validated_for_bilet_builder",
            "minimum_required_trust_status": "validated_paper",
            "current_best_status": "sample_only",
            "allowed_action": "inspect",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=".omnibet-local/reports/local_v301_v310_dataset_materialization.json")
    ap.add_argument("--market-terminal-out", default=".omnibet-local/reports/local_v301_v310_market_terminal_preview.json")
    args = ap.parse_args()
    root = Path(args.root)
    sample = read_json(root / "data/materialization/v301_v310/local_dataset_materialization.sample.json")
    report = build_desktop_payload(sample)
    market = build_market_terminal_preview(sample)
    write_json(root / args.out, report)
    write_json(root / args.market_terminal_out, market)
    print(json.dumps({"ok": True, "report": args.out, "market_terminal_report": args.market_terminal_out, "rows": report.get("summary", {})}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
