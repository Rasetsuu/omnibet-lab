#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

KNOWN_ALIASES = {
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


def count_provider_markets(root: Path) -> Dict[str, Any]:
    sample = read_json(root / "data/samples/the_odds_api_event_markets_sample.json")
    rows = []
    for bookmaker in sample.get("bookmakers", []):
        for market in bookmaker.get("markets", []):
            key = market.get("key")
            rows.append({"bookmaker": bookmaker.get("key"), "market_key": key})
    known = [row for row in rows if row["market_key"] in KNOWN_ALIASES]
    unknown = [row for row in rows if row["market_key"] not in KNOWN_ALIASES]
    return {
        "total_market_rows": len(rows),
        "known_market_rows": len(known),
        "unknown_market_rows": len(unknown),
        "unknown_keys": sorted({row["market_key"] for row in unknown}),
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/market_registry.v237.json")
    rust = (root / "rust-core/src/market_registry.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    market_counts = count_provider_markets(root)

    canonical = {row["canonical_market_id"]: row for row in contract.get("canonical_markets", [])}
    aliases = contract.get("provider_aliases", [])
    alias_pairs = {(row.get("provider_id"), row.get("provider_market_key")): row.get("canonical_market_id") for row in aliases}
    policy = contract.get("promotion_policy", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.market_registry.v237",
        "unknown_auto_promotion_forbidden": policy.get("automatic_unknown_market_promotion_allowed") is False,
        "provider_alias_required": policy.get("provider_alias_required") is True,
        "review_required_for_unmapped": policy.get("review_required_for_unmapped_markets") is True,
        "settlement_rule_required": policy.get("settlement_rule_required") is True,
        "all_canonical_have_family": all(row.get("family") for row in canonical.values()),
        "all_canonical_have_settlement": all(row.get("settlement_rule") for row in canonical.values()),
        "all_aliases_reference_canonical": all(target in canonical for target in alias_pairs.values()),
        "sample_known_aliases_covered": all(("the_odds_api", key) in alias_pairs for key in KNOWN_ALIASES),
        "player_market_lineup_gated": canonical.get("player_shots_on_target", {}).get("lineup_required") is True and canonical.get("player_shots_on_target", {}).get("player_required") is True,
        "line_markets_have_line_required": all(canonical[target].get("line_required") is True for target in ["handicap", "total_goals", "total_corners", "team_shots_on_target", "player_shots_on_target"]),
        "sample_market_counts": market_counts["total_market_rows"] == 8 and market_counts["known_market_rows"] == 7 and market_counts["unknown_market_rows"] == 1,
        "unknown_sample_reviewed": market_counts["unknown_keys"] == ["special_combo_unknown"],
        "rust_module_exposed": "pub mod market_registry;" in lib and "pub use market_registry::*;" in lib,
        "rust_types": "MarketRegistryContract" in rust and "CanonicalMarket" in rust and "MarketResolution" in rust,
        "rust_resolver": "resolve_provider_market" in rust and "promotion_allowed" in rust,
        "rust_blocks_unknowns": "special_combo_unknown" in rust and "unmapped_provider_market" in rust,
        "rust_checks_bronze_rows": "resolve_market_discovery_rows" in rust and "ProviderMarketDiscoverySnapshot" in rust,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.market_registry_smoke.v237",
        "milestone": "v237_canonical_market_registry",
        "provider_sample_market_counts": market_counts,
        "acceptance": checks,
        "safety": {
            "unknown_markets_auto_promoted": False,
            "unmapped_markets_require_review": True,
            "player_markets_require_lineup": True,
            "settlement_rules_required": True
        }
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v237_market_registry.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
