#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

KNOWN = {
    "h2h": "match_result_1x2",
    "spreads": "handicap",
    "totals": "total_goals",
    "corners": "total_corners",
    "shots_on_target": "team_shots_on_target",
    "player_shots_on_target": "player_shots_on_target",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def compute_preview_counts(root: Path) -> Dict[str, Any]:
    sample = read_json(root / "data/samples/the_odds_api_event_markets_sample.json")
    groups: Dict[str, Dict[str, Any]] = {}
    raw_rows = 0
    for bookmaker in sample.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            raw_rows += 1
            key = market.get("key")
            group = groups.setdefault(key, {"bookmakers": set(), "outcomes": 0})
            group["bookmakers"].add(bookmaker.get("key"))
            group["outcomes"] += len(market.get("outcomes", []))
    resolved = [key for key in groups if key in KNOWN]
    review = [key for key in groups if key not in KNOWN]
    return {
        "bronze_market_rows": raw_rows,
        "unique_market_groups": len(groups),
        "resolved_market_groups": len(resolved),
        "review_market_groups": len(review),
        "blocked_promotions": len(review),
        "review_keys": sorted(review),
        "player_group_present": "player_shots_on_target" in groups,
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/silver_market_mapping_preview.v238.json")
    rust = (root / "rust-core/src/silver_market.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    counts = compute_preview_counts(root)
    expected = contract.get("expected_offline_preview", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.silver_market_mapping_preview_contract.v238",
        "preview_only": contract.get("promotion_policy", {}).get("preview_only") is True,
        "unknown_auto_promotion_forbidden": contract.get("promotion_policy", {}).get("automatic_unknown_market_promotion_allowed") is False,
        "review_rows_not_promoted": contract.get("promotion_policy", {}).get("review_rows_are_not_promoted") is True,
        "player_lineup_gate": contract.get("promotion_policy", {}).get("player_markets_remain_lineup_gated") is True,
        "expected_raw_rows": counts["bronze_market_rows"] == expected.get("bronze_market_rows"),
        "expected_group_rows": counts["unique_market_groups"] == expected.get("unique_market_groups"),
        "expected_resolved_groups": counts["resolved_market_groups"] == expected.get("resolved_market_groups"),
        "expected_review_groups": counts["review_market_groups"] == expected.get("review_market_groups"),
        "expected_blocked_promotions": counts["blocked_promotions"] == expected.get("blocked_promotions"),
        "review_key_preserved": counts["review_keys"] == [expected.get("review_market_key")],
        "player_group_present": counts["player_group_present"] is True,
        "rust_module_exposed": "pub mod silver_market;" in lib and "pub use silver_market::*;" in lib,
        "rust_preview_types": "SilverMarketMappingPreview" in rust and "SilverMarketMappingRow" in rust and "SilverMarketReviewRow" in rust,
        "rust_preview_builder": "build_silver_market_mapping_preview" in rust and "build_preview_from_offline_samples" in rust,
        "rust_blocks_unknowns": "automatic_unknown_promotion_allowed: false" in rust and "promotion_allowed: false" in rust,
        "rust_lineup_gate_checked": "player_shots_on_target" in rust and "lineup_required" in rust,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.silver_market_mapping_preview_smoke.v238",
        "milestone": "v238_silver_market_mapping_preview",
        "computed_counts": counts,
        "acceptance": checks,
        "safety": {
            "preview_only": True,
            "unknown_markets_auto_promoted": False,
            "review_rows_promoted": False,
            "player_market_lineup_gate_preserved": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v238_silver_market_mapping_preview.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
