#!/usr/bin/env python3
"""OmniBet v30 bookmaker odds and Bet Builder market contract.

This is dependency-free and network-free. It defines how bookmaker odds,
Romanian `cota/cote`, and Bet Builder / same-game parlay legs should be
represented before any sportsbook/provider integration is added.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from math import prod
from pathlib import Path
from typing import Any, Dict, List


BASE_MARKETS: List[Dict[str, Any]] = [
    {
        "market_id": "football_1x2_regulation",
        "display": "1X2 regulation time",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["home", "draw", "away"],
        "core": True,
    },
    {
        "market_id": "football_total_goals_regulation",
        "display": "Total goals regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["over", "under"],
        "line_required": True,
        "core": True,
    },
    {
        "market_id": "football_asian_handicap_regulation",
        "display": "Asian handicap regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["home", "away"],
        "line_required": True,
        "core": True,
    },
    {
        "market_id": "football_corners_regulation",
        "display": "Corners regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["over", "under", "team_over", "team_under"],
        "line_required": True,
        "core": True,
    },
    {
        "market_id": "football_cards_regulation",
        "display": "Cards regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["over", "under", "team_over", "team_under", "player_card"],
        "line_required": True,
        "core": True,
    },
    {
        "market_id": "football_player_shots_regulation",
        "display": "Player shots regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["player_over", "player_under"],
        "line_required": True,
        "player_required": True,
        "core": True,
    },
    {
        "market_id": "football_anytime_scorer_regulation",
        "display": "Anytime goalscorer regulation",
        "settlement_scope": "regulation_90_plus_stoppage",
        "selections": ["player_scores"],
        "player_required": True,
        "core": False,
    },
]

BET_BUILDER_LEG_SCHEMA = {
    "required_fields": [
        "leg_id",
        "market_id",
        "selection",
        "line",
        "team_id",
        "player_id",
        "settlement_scope",
        "decimal_odds",
        "provider_leg_id",
    ],
    "notes": [
        "line/team_id/player_id may be null if the market does not need them.",
        "decimal_odds is Romanian cota/cote normalized to decimal format.",
        "provider_leg_id preserves sportsbook identity when available.",
    ],
}

BET_BUILDER_SLIP_SCHEMA = {
    "required_fields": [
        "builder_id",
        "match_id",
        "bookmaker",
        "observed_at",
        "provider_event_id",
        "combined_decimal_odds",
        "legs",
        "payload_sha256",
    ],
    "critical_rule": "Do not estimate same-game combined odds by multiplying leg odds unless correlation is explicitly modeled or the result is tagged independent_approximation_only.",
}

SOURCE_POLICY = [
    {
        "source_id": "superbet_public_site_reference",
        "role": "manual_or_permissioned_bookmaker_reference",
        "allowed_in_ci": False,
        "notes": [
            "May be useful for Romanian odds vocabulary, 1X2, live offers, and Bet Builder market examples.",
            "Do not add automated website scraping unless terms/API/permission allow it.",
            "If used manually, store only user-provided snapshots or local/private cache outside Git.",
        ],
    },
    {
        "source_id": "flashscore_public_site_reference",
        "role": "manual_or_permissioned_score_status_reference",
        "allowed_in_ci": False,
        "notes": [
            "Useful as human-facing live score/status/stat reference.",
            "Terms restrict commercial use and automated scraping/aggregation without consent.",
            "Do not add a scraper to the repo unless permission/API route is confirmed.",
        ],
    },
    {
        "source_id": "official_api_or_paid_provider",
        "role": "preferred_production_route",
        "allowed_in_ci": False,
        "notes": [
            "Use API-Football, Sportmonks, The Odds API, or another licensed feed for automation.",
            "Keep API keys out of Git and CI.",
        ],
    },
]

EXAMPLE_1X2 = {
    "market_id": "football_1x2_regulation",
    "bookmaker": "example_bookmaker",
    "observed_at": "2026-06-16T18:00:00Z",
    "prices": {"home": 1.50, "draw": 4.50, "away": 6.50},
}

EXAMPLE_BUILDER = {
    "bookmaker": "example_bookmaker",
    "match_id": "example_france_senegal",
    "observed_at": "2026-06-16T18:00:00Z",
    "combined_decimal_odds": 2.90,
    "legs": [
        {"market_id": "football_1x2_regulation", "selection": "home", "decimal_odds": 1.50},
        {"market_id": "football_corners_regulation", "selection": "team_over", "team_id": "france", "line": 4.5, "decimal_odds": None},
        {"market_id": "football_player_shots_regulation", "selection": "player_over", "player_id": "example_player", "line": 1.5, "decimal_odds": None},
    ],
    "correlation_group": "same_match_correlated",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def implied_prob(decimal_odds: float) -> float:
    return 1.0 / decimal_odds if decimal_odds > 0 else 0.0


def no_vig_probs(prices: Dict[str, float]) -> Dict[str, float]:
    raw = {k: implied_prob(float(v)) for k, v in prices.items() if float(v) > 0}
    total = sum(raw.values())
    return {k: round(v / total, 8) for k, v in raw.items()} if total else {}


def overround(prices: Dict[str, float]) -> float:
    return round(sum(implied_prob(float(v)) for v in prices.values()) - 1.0, 8)


def independent_combo_odds(odds: List[float]) -> float:
    return round(prod(odds), 6) if odds else 0.0


def build_contract() -> Dict[str, Any]:
    combo_legs = [leg["decimal_odds"] for leg in EXAMPLE_BUILDER["legs"] if leg.get("decimal_odds")]
    return {
        "ok": True,
        "milestone": "v30_bookmaker_odds_and_bet_builder_market_contract",
        "created_at": utc_now(),
        "language_notes": {
            "romanian_cota": "decimal odds",
            "romanian_cote": "odds / prices",
            "bet_builder_english": ["Bet Builder", "same-game parlay", "same-match accumulator"],
        },
        "base_markets": BASE_MARKETS,
        "bet_builder": {
            "leg_schema": BET_BUILDER_LEG_SCHEMA,
            "slip_schema": BET_BUILDER_SLIP_SCHEMA,
            "correlation_policy": {
                "same_match_legs_are_correlated": True,
                "warning": "A Bet Builder price is not just multiplication of fair leg probabilities; books price correlation and margin into the combined quote.",
                "required_output_tags": ["bookmaker_quote", "model_joint_probability", "model_edge", "correlation_warning"],
            },
            "example": EXAMPLE_BUILDER,
            "example_independent_odds_for_known_leg_prices_only": independent_combo_odds(combo_legs),
        },
        "odds_math": {
            "example_1x2": EXAMPLE_1X2,
            "raw_implied_probability": {k: round(implied_prob(v), 8) for k, v in EXAMPLE_1X2["prices"].items()},
            "overround": overround(EXAMPLE_1X2["prices"]),
            "no_vig_probability": no_vig_probs(EXAMPLE_1X2["prices"]),
        },
        "live_odds_snapshot_contract": {
            "table": "live_odds_snapshots",
            "required_fields": [
                "snapshot_id",
                "observed_at",
                "provider_id",
                "bookmaker",
                "provider_event_id",
                "match_id",
                "market_id",
                "selection",
                "line",
                "player_id",
                "team_id",
                "decimal_odds",
                "suspended",
                "last_update",
                "payload_sha256",
            ],
            "rule": "append-only; never overwrite historical observed prices",
        },
        "source_policy": SOURCE_POLICY,
        "honesty": {
            "paper_only": True,
            "no_scraping_claim": True,
            "no_profit_claim": True,
            "no_staking_recommendation": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate OmniBet v30 bookmaker odds and Bet Builder market contract.")
    ap.add_argument("--out", default="../reports/ci_v30_bookmaker_market_contract.json")
    ap.add_argument("--write-config", default="")
    args = ap.parse_args()
    contract = build_contract()
    write_json(Path(args.out), contract)
    if args.write_config:
        write_json(Path(args.write_config), contract)
    print(json.dumps(contract, indent=2))


if __name__ == "__main__":
    main()
