#!/usr/bin/env python3
"""OmniBet v31 provider matrix and dynamic market discovery schema.

This is CI-safe: no API keys, no website scraping, no network calls. It records
which providers are candidates, what they can provide, and how raw markets should
be discovered/mapped over time.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


SPORTSBOOK_REFERENCES: List[Dict[str, Any]] = [
    {"provider_id": "superbet", "type": "sportsbook_reference", "region_hint": "ro/eu", "automation_status": "manual_or_permissioned_only", "strengths": ["romanian odds vocabulary", "1x2", "live markets", "bet builder", "corners/cards/player props"]},
    {"provider_id": "betano", "type": "sportsbook_reference", "region_hint": "eu", "automation_status": "manual_or_permissioned_only", "strengths": ["sportsbook market reference", "bet builder style markets"]},
    {"provider_id": "unibet", "type": "sportsbook_reference", "region_hint": "eu", "automation_status": "manual_or_permissioned_only", "strengths": ["sportsbook market reference", "player props"]},
    {"provider_id": "bet365", "type": "sportsbook_reference", "region_hint": "global", "automation_status": "manual_or_permissioned_only", "strengths": ["broad market coverage", "in-play reference"]},
    {"provider_id": "fortuna", "type": "sportsbook_reference", "region_hint": "ro/eu", "automation_status": "manual_or_permissioned_only", "strengths": ["regional sportsbook market reference"]},
    {"provider_id": "casa_pariurilor", "type": "sportsbook_reference", "region_hint": "ro", "automation_status": "manual_or_permissioned_only", "strengths": ["romanian sportsbook market reference"]},
    {"provider_id": "mozzart", "type": "sportsbook_reference", "region_hint": "eu", "automation_status": "manual_or_permissioned_only", "strengths": ["sportsbook market reference"]},
    {"provider_id": "betfair", "type": "exchange_and_sportsbook_reference", "region_hint": "uk/global", "automation_status": "official_api_candidate", "strengths": ["exchange prices", "market efficiency", "historical data candidate"]},
    {"provider_id": "pinnacle", "type": "sharp_book_reference", "region_hint": "global_restricted", "automation_status": "restricted_or_partnership_only", "strengths": ["high-quality market baseline", "closing line reference"]},
]

OFFICIAL_API_CANDIDATES: List[Dict[str, Any]] = [
    {
        "provider_id": "the_odds_api",
        "type": "official_odds_api",
        "automation_status": "api_key_required",
        "priority": 1,
        "domains": ["sports", "odds", "scores", "events", "event_odds", "event_markets", "participants", "historical_odds", "historical_events", "historical_event_odds"],
        "market_discovery_value": "event-markets endpoint can discover available market keys per bookmaker/event",
        "notes": ["Supports decimal odds format", "Historical odds are paid", "Useful for dynamic market discovery and odds snapshots"],
    },
    {
        "provider_id": "api_football",
        "type": "official_football_api",
        "automation_status": "api_key_required",
        "priority": 2,
        "domains": ["fixtures", "events", "lineups", "statistics", "players", "standings", "odds", "top_scorers"],
        "market_discovery_value": "all-in-one football match/live/state candidate",
        "notes": ["Good candidate for match state and football context"],
    },
    {
        "provider_id": "sportmonks",
        "type": "official_football_api",
        "automation_status": "api_key_required",
        "priority": 3,
        "domains": ["fixtures", "livescores", "events", "players", "teams", "odds", "world_cup_docs"],
        "market_discovery_value": "structured football and live data candidate",
        "notes": ["Serious provider candidate for production-grade football coverage"],
    },
    {
        "provider_id": "betfair_exchange_api",
        "type": "official_exchange_api",
        "automation_status": "api_key_account_required",
        "priority": 4,
        "domains": ["exchange_market_catalogue", "market_book", "prices", "orders", "settlements", "historical_exchange_data"],
        "market_discovery_value": "exchange market catalog and market efficiency research",
        "notes": ["Not equivalent to sportsbook Bet Builder", "Useful for price movement and market-efficiency baselines"],
    },
    {
        "provider_id": "pinnacle_api",
        "type": "restricted_sharp_odds_api",
        "automation_status": "restricted_access_or_partnership",
        "priority": 5,
        "domains": ["sharp_odds", "closing_lines", "fixtures", "markets"],
        "market_discovery_value": "sharp-book baseline if access is granted",
        "notes": ["Do not assume access", "Keep as later possible benchmark"],
    },
    {
        "provider_id": "football_data_org",
        "type": "official_football_data_api",
        "automation_status": "api_key_plan_based",
        "priority": 6,
        "domains": ["fixtures", "results", "tables", "squads", "lineups_subs_where_plan_allows"],
        "market_discovery_value": "match truth/live fixture support rather than deep bookmaker markets",
        "notes": ["Useful safe alternative to public live-score website scraping"],
    },
    {
        "provider_id": "openligadb",
        "type": "open_football_json_api",
        "automation_status": "no_auth_for_public_data",
        "priority": 7,
        "domains": ["fixtures", "results", "league_data", "world_cup_pages"],
        "market_discovery_value": "open match truth support for selected competitions",
        "notes": ["Good for score/result truth where coverage fits"],
    },
]

MARKET_DISCOVERY_SCHEMA = {
    "table": "raw_market_snapshots",
    "required_fields": [
        "raw_market_snapshot_id",
        "observed_at",
        "provider_id",
        "bookmaker",
        "provider_sport_key",
        "provider_event_id",
        "match_id",
        "raw_market_key",
        "raw_market_name",
        "raw_selection_key",
        "raw_selection_name",
        "decimal_odds",
        "line_raw",
        "line_value",
        "team_name_raw",
        "team_id",
        "player_name_raw",
        "player_id",
        "period_raw",
        "settlement_scope_guess",
        "mapped_market_id",
        "mapping_confidence",
        "needs_mapping",
        "suspended",
        "last_update",
        "payload_sha256",
    ],
    "policy": "Store raw provider names and parsed guesses; never discard unmapped markets.",
}

KNOWN_MARKET_FAMILIES = [
    "1x2",
    "double_chance",
    "draw_no_bet",
    "totals",
    "team_totals",
    "handicap",
    "asian_handicap",
    "btts",
    "correct_score",
    "half_time_full_time",
    "corners",
    "team_corners",
    "cards",
    "team_cards",
    "offsides",
    "shots",
    "shots_on_target",
    "player_shots",
    "player_shots_on_target",
    "player_goalscorer",
    "player_assists",
    "player_cards",
    "goalkeeper_saves",
    "fouls",
    "bet_builder_same_game_combo",
    "boosted_odds_reference",
]

SAFE_AUTOMATION_RULES = [
    "Use official API/provider routes for automation.",
    "Use sportsbook websites only as manual/reference or with explicit permission/API access.",
    "Do not add website scraping to CI.",
    "Do not store API keys in Git.",
    "Every provider row must declare license/terms status before automated ingestion.",
    "Every odds row must preserve observed_at and provider last_update when available.",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_matrix() -> Dict[str, Any]:
    return {
        "ok": True,
        "milestone": "v31_provider_candidate_matrix_and_market_discovery_schema",
        "created_at": utc_now(),
        "sportsbook_references": SPORTSBOOK_REFERENCES,
        "official_api_candidates": sorted(OFFICIAL_API_CANDIDATES, key=lambda x: x["priority"]),
        "recommended_provider_route": {
            "odds_and_market_discovery": ["the_odds_api", "betfair_exchange_api", "pinnacle_api_if_access"],
            "football_live_state": ["api_football", "sportmonks", "football_data_org", "openligadb"],
            "manual_market_taxonomy_reference": ["superbet", "betano", "unibet", "bet365", "fortuna", "casa_pariurilor", "mozzart"],
        },
        "market_discovery_schema": MARKET_DISCOVERY_SCHEMA,
        "known_market_families": KNOWN_MARKET_FAMILIES,
        "mapping_lifecycle": [
            "ingest raw provider market snapshot",
            "parse line/team/player/period/selection guesses",
            "map to known_market_id when confidence is high",
            "otherwise keep needs_mapping=true",
            "review unknown_market_queue",
            "add parser/mapping rule",
            "rerun mapping without mutating original raw snapshot",
        ],
        "safe_automation_rules": SAFE_AUTOMATION_RULES,
        "honesty": {
            "paper_only": True,
            "no_scraping_claim": True,
            "no_profit_claim": True,
            "no_provider_integration_yet": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate OmniBet v31 provider matrix and market discovery schema.")
    ap.add_argument("--out", default="../reports/ci_v31_provider_market_discovery.json")
    ap.add_argument("--write-config", default="")
    args = ap.parse_args()
    matrix = build_matrix()
    write_json(Path(args.out), matrix)
    if args.write_config:
        write_json(Path(args.write_config), matrix)
    print(json.dumps(matrix, indent=2))


if __name__ == "__main__":
    main()
