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


def count_the_odds_api(sample: Dict[str, Any]) -> Dict[str, Any]:
    market_rows = 0
    odds_rows = 0
    needs_mapping = 0
    player_prop_rows = 0
    known = {"h2h", "spreads", "totals", "corners", "shots_on_target", "player_shots_on_target"}
    for bookmaker in sample.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            market_rows += 1
            if market.get("key") not in known:
                needs_mapping += 1
            if "player" in str(market.get("key", "")):
                player_prop_rows += len(market.get("outcomes", []))
            odds_rows += len(market.get("outcomes", []))
    return {
        "fixture_count": 1,
        "market_rows": market_rows,
        "odds_rows": odds_rows,
        "needs_mapping_review_rows": needs_mapping,
        "player_prop_rows_min": player_prop_rows,
    }


def count_api_football(sample: Dict[str, Any]) -> Dict[str, Any]:
    response = sample.get("response", [])
    first = response[0] if response else {}
    lineup_rows = 0
    started = 0
    bench = 0
    for lineup in first.get("lineups", []):
        start_rows = len(lineup.get("startXI", []))
        bench_rows = len(lineup.get("substitutes", []))
        started += start_rows
        bench += bench_rows
        lineup_rows += start_rows + bench_rows
    statistic_rows = sum(len(row.get("statistics", [])) for row in first.get("statistics", []))
    return {
        "fixture_count": 1 if response else 0,
        "event_rows": len(first.get("events", [])),
        "lineup_player_rows": lineup_rows,
        "statistic_rows": statistic_rows,
        "started_player_rows": started,
        "bench_player_rows": bench,
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/provider_offline_samples.v235.json")
    rust_provider = (root / "rust-core/src/provider.rs").read_text(encoding="utf-8")
    results: Dict[str, Dict[str, Any]] = {}
    sample_checks: Dict[str, bool] = {}

    for row in contract.get("samples", []):
        sample_id = row["sample_id"]
        sample = read_json(root / row["path"])
        if row["provider_id"] == "the_odds_api":
            actual = count_the_odds_api(sample)
        elif row["provider_id"] == "api_football":
            actual = count_api_football(sample)
        else:
            actual = {}
        expected = row.get("expected", {})
        results[sample_id] = {"actual": actual, "expected": expected}
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            if key.endswith("_min"):
                sample_checks[f"{sample_id}_{key}"] = actual_value is not None and actual_value >= expected_value
            else:
                sample_checks[f"{sample_id}_{key}"] = actual_value == expected_value

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.provider_offline_samples.v235",
        "no_external_calls": contract.get("network_policy", {}).get("external_calls_in_ci") is False,
        "no_credentials_required": contract.get("network_policy", {}).get("credential_values_required") is False,
        "no_credentials_stored_or_displayed": contract.get("network_policy", {}).get("credential_values_stored") is False and contract.get("network_policy", {}).get("credential_values_displayed") is False,
        "samples_declared": len(contract.get("samples", [])) == 2,
        "rust_the_odds_parser": "parse_the_odds_api_event_markets_sample" in rust_provider and "TheOddsApiParseOutput" in rust_provider,
        "rust_api_football_parser": "parse_api_football_live_state_sample" in rust_provider and "ApiFootballParseOutput" in rust_provider,
        "rust_typed_outputs": all(name in rust_provider for name in contract.get("canonical_outputs", [])),
        "rust_unknown_market_review": "needs_mapping_review" in rust_provider and "special_combo_unknown" in rust_provider,
        "rust_source_manifests": "build_sample_snapshot_manifest" in rust_provider and "payload_sha256" in rust_provider,
        "rust_no_external_call": "external_call_performed: false" in rust_provider,
        "mapping_policy_safe": contract.get("market_mapping_policy", {}).get("unknown_provider_markets_require_review") is True and contract.get("market_mapping_policy", {}).get("automatic_unknown_market_promotion_allowed") is False,
        **sample_checks,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.provider_offline_samples_smoke.v235",
        "milestone": "v235_offline_provider_sample_parsers",
        "results": results,
        "acceptance": checks,
        "safety": {
            "external_calls_in_ci": False,
            "credential_values_required": False,
            "credential_values_stored": False,
            "unknown_markets_require_review": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v235_provider_offline_samples.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
