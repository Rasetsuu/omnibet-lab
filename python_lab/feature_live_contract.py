#!/usr/bin/env python3
"""OmniBet v29 feature-priority and live-data contract.

This is a CI-safe, dependency-free contract generator. It freezes the current
feature policy before more data is added:

- core = must-have + high-value + refined medium-value fields;
- experimental = full medium-value fields that need ablation proof;
- postponed = low-ROI fields such as weather unless later evidence says otherwise;
- live data = append-only point-in-time snapshots, never mutable future-known rows.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List


MUST_HAVE = [
    {"field": "match_id", "why": "primary identity key"},
    {"field": "source_id", "why": "source lineage and conflict resolution"},
    {"field": "competition_id", "why": "competition strength and market context"},
    {"field": "season_id", "why": "time partition and model drift control"},
    {"field": "match_date", "why": "walk-forward ordering and leakage prevention"},
    {"field": "home_team_id", "why": "team identity"},
    {"field": "away_team_id", "why": "team identity"},
    {"field": "home_away_neutral", "why": "home advantage and neutral tournament matches"},
    {"field": "regulation_score", "why": "90-minute market settlement"},
    {"field": "full_time_score", "why": "match result spine"},
    {"field": "extra_time_score", "why": "knockout market separation when present"},
    {"field": "penalty_shootout_result", "why": "qualification/lift-trophy settlement separation"},
    {"field": "market_id", "why": "1X2/O-U/cards/corners/props cannot share labels blindly"},
    {"field": "settlement_scope", "why": "regulation vs ET vs penalties vs qualify"},
    {"field": "opening_odds", "why": "market baseline and drift"},
    {"field": "closing_odds", "why": "CLV and market-efficiency benchmark"},
    {"field": "no_vig_implied_probability", "why": "fair market baseline"},
]

HIGH_VALUE = [
    {"field": "starting_lineups", "why": "team strength changes massively with personnel"},
    {"field": "substitutes", "why": "depth and tactical options"},
    {"field": "player_minutes", "why": "availability, load, role, and form"},
    {"field": "player_positions_roles", "why": "same player can matter differently by role"},
    {"field": "injuries_suspensions", "why": "availability shock when source is reliable"},
    {"field": "xg_xa", "why": "quality of chances beyond final score"},
    {"field": "shots_and_shots_on_target", "why": "attacking volume and pressure"},
    {"field": "corners", "why": "pressure and separate market target"},
    {"field": "cards_red_cards", "why": "discipline and game-state distortion"},
    {"field": "fouls", "why": "discipline and referee/card model input"},
    {"field": "substitution_events", "why": "tactics and injuries during match"},
    {"field": "goalkeeper_actions", "why": "keeper quality and shot-stopping"},
    {"field": "recent_form", "why": "rolling team/player state"},
    {"field": "rest_days_fixture_congestion", "why": "fatigue and rotation risk"},
    {"field": "rolling_team_player_strength", "why": "stable ability estimate before kickoff"},
]

REFINED_MEDIUM = [
    {"field": "referee", "why": "useful for cards/fouls/penalty tendencies, not every market"},
    {"field": "tournament_stage", "why": "group vs knockout vs final changes incentives"},
    {"field": "match_importance", "why": "qualification/elimination/rotation incentives"},
    {"field": "squad_rotation", "why": "actual selected XI can differ from team reputation"},
    {"field": "club_strength_of_national_team_players", "why": "international team strength proxy"},
    {"field": "national_team_chemistry_continuity", "why": "minutes together and repeat lineups matter"},
]

EXPERIMENTAL_MEDIUM = [
    {"field": "travel_distance_time_zone", "why": "can matter but needs reliable schedule/location data"},
    {"field": "crowd_attendance", "why": "possible home-pressure proxy but noisy and incomplete"},
    {"field": "pitch_condition", "why": "possible style impact but hard to source consistently"},
]

POSTPONED = [
    {"field": "weather", "why": "low early ROI, inconsistent historical availability, only extreme cases likely matter"},
    {"field": "social_media_sentiment", "why": "noisy and hard to validate point-in-time"},
    {"field": "vague_news_sentiment", "why": "high leakage/noise risk unless transformed into reliable injuries/lineups"},
    {"field": "rumors", "why": "not stable enough for audited model features"},
]

LIVE_PROVIDERS = [
    {
        "provider_id": "api_football_candidate",
        "role": "live_match_data_candidate",
        "domains": ["fixtures", "status", "events", "lineups", "statistics", "odds", "players"],
        "api_key_required": True,
        "ci_policy": "contract_only_no_key_no_network",
    },
    {
        "provider_id": "sportmonks_candidate",
        "role": "live_match_data_candidate",
        "domains": ["live_scores", "events", "fixtures", "odds_docs", "world_cup_app_support"],
        "api_key_required": True,
        "ci_policy": "contract_only_no_key_no_network",
    },
    {
        "provider_id": "the_odds_api_candidate",
        "role": "live_and_historical_odds_candidate",
        "domains": ["sports", "events", "odds", "event_odds", "scores", "historical_odds"],
        "api_key_required": True,
        "ci_policy": "contract_only_no_key_no_network",
    },
]

LIVE_SNAPSHOT_TABLES = [
    {
        "table": "live_fixture_snapshots",
        "required_fields": ["snapshot_id", "observed_at", "provider_id", "provider_fixture_id", "match_id", "status", "clock_minute", "home_score", "away_score", "payload_sha256"],
        "purpose": "append-only match state over time",
    },
    {
        "table": "live_event_snapshots",
        "required_fields": ["snapshot_id", "observed_at", "provider_id", "provider_event_id", "match_id", "event_type", "period", "clock_minute", "team_id", "player_id", "payload_sha256"],
        "purpose": "append-only event stream normalized from provider payloads",
    },
    {
        "table": "live_lineup_snapshots",
        "required_fields": ["snapshot_id", "observed_at", "provider_id", "match_id", "team_id", "player_id", "started", "position", "status", "payload_sha256"],
        "purpose": "lineups and availability as they become known",
    },
    {
        "table": "live_stat_snapshots",
        "required_fields": ["snapshot_id", "observed_at", "provider_id", "match_id", "team_id", "stat_name", "stat_value", "payload_sha256"],
        "purpose": "point-in-time team/player stats during match",
    },
    {
        "table": "live_odds_snapshots",
        "required_fields": ["snapshot_id", "observed_at", "provider_id", "provider_event_id", "match_id", "market_id", "selection", "bookmaker", "price", "last_update", "payload_sha256"],
        "purpose": "point-in-time odds stream for CLV and live market analysis",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def build_contract() -> Dict[str, Any]:
    return {
        "ok": True,
        "milestone": "v29_feature_priority_and_live_data_contract",
        "created_at": utc_now(),
        "feature_policy": {
            "core_engine": {
                "tiers": ["must_have", "high_value", "refined_medium"],
                "rule": "Only these tiers can be assumed for the serious core engine before ablation.",
            },
            "experimental": {
                "tiers": ["experimental_medium"],
                "rule": "Allowed only behind reports/ablation flags.",
            },
            "postponed": {
                "tiers": ["postponed"],
                "rule": "Do not spend storage/integration effort early unless later evidence justifies it.",
            },
            "tiers": {
                "must_have": MUST_HAVE,
                "high_value": HIGH_VALUE,
                "refined_medium": REFINED_MEDIUM,
                "experimental_medium": EXPERIMENTAL_MEDIUM,
                "postponed": POSTPONED,
            },
        },
        "live_data_policy": {
            "architecture": "append_only_point_in_time_snapshots",
            "no_future_leakage_rule": "Predictions/evaluations may use only snapshots with observed_at <= evaluation_time.",
            "provider_payload_policy": "Store payload hash and normalized fields; raw payload cache is local/bronze only.",
            "ci_policy": "contract and sample schema only; no API keys and no network calls in CI.",
            "providers": LIVE_PROVIDERS,
            "snapshot_tables": LIVE_SNAPSHOT_TABLES,
        },
        "runtime_loop": [
            "poll fixtures/status on a schedule appropriate to provider limits",
            "append normalized live snapshots with observed_at",
            "join latest point-in-time match/player/odds features",
            "run Rust model artifact inference over current snapshot",
            "write paper-only decision/report rows",
            "later evaluate against closing/final result without rewriting old snapshots",
        ],
        "honesty": {
            "paper_only": True,
            "no_model_quality_claim": True,
            "no_profit_claim": True,
            "weather_postponed_by_default": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate OmniBet v29 feature-priority and live-data contract.")
    ap.add_argument("--out", default="../reports/ci_v29_feature_live_contract.json")
    ap.add_argument("--write-config", default="")
    args = ap.parse_args()
    contract = build_contract()
    write_json(Path(args.out), contract)
    if args.write_config:
        write_json(Path(args.write_config), contract)
    print(json.dumps(contract, indent=2))


if __name__ == "__main__":
    main()
