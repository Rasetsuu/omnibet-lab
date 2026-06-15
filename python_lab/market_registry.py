#!/usr/bin/env python3
"""
OmniBet Lab v3B market registry.

This module is the long-term contract between data, models, GUI, and bet-builder.
Markets are not hardcoded only as "1X2 / Over 2.5"; each market declares:
- what sport it belongs to
- whether it needs team/player/minute/line input
- what data is required to train/predict it
- correlation tags for same-game builder risk

The registry is intentionally broad. Some markets are immediately supported by
v3B prototype probabilities; others are future-ready placeholders until event,
lineup, player, or live odds data is available.
"""
from __future__ import annotations

import argparse
import csv
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List


@dataclass(frozen=True)
class Market:
    market_id: str
    sport: str
    family: str
    display_name: str
    selections: List[str]
    requires_team: bool = False
    requires_player: bool = False
    requires_line: bool = False
    requires_minute: bool = False
    availability: str = "future"  # supported | prototype | future
    model_hint: str = ""
    data_requirements: List[str] = None
    correlation_tags: List[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["data_requirements"] = self.data_requirements or []
        d["correlation_tags"] = self.correlation_tags or []
        return d


FOOTBALL_MARKETS: List[Market] = [
    Market("football.1x2", "football", "core", "Full Time Result", ["home", "draw", "away"], availability="supported", model_hint="hybrid_1x2", data_requirements=["match_results"], correlation_tags=["result"]),
    Market("football.double_chance", "football", "core", "Double Chance", ["1X", "12", "X2"], availability="supported", model_hint="derived_1x2", data_requirements=["match_results"], correlation_tags=["result"]),
    Market("football.draw_no_bet", "football", "core", "Draw No Bet", ["home", "away"], availability="prototype", model_hint="derived_1x2", data_requirements=["match_results"], correlation_tags=["result"]),
    Market("football.correct_score", "football", "core", "Correct Score", ["0-0", "1-0", "1-1", "2-1", "2-0"], availability="prototype", model_hint="score_matrix", data_requirements=["score_matrix"], correlation_tags=["scoreline", "result", "goals"]),

    Market("football.total_goals", "football", "goals", "Total Goals", ["over", "under"], requires_line=True, availability="supported", model_hint="hybrid_over_goals", data_requirements=["match_results", "score_matrix"], correlation_tags=["goals"]),
    Market("football.team_goals", "football", "goals", "Team Goals", ["over", "under"], requires_team=True, requires_line=True, availability="prototype", model_hint="team_goal_lambda", data_requirements=["score_matrix", "team_attack"], correlation_tags=["team_attacking", "goals"]),
    Market("football.btts", "football", "goals", "Both Teams To Score", ["yes", "no"], availability="supported", model_hint="hybrid_btts", data_requirements=["match_results"], correlation_tags=["goals", "both_teams_score"]),
    Market("football.goal_interval", "football", "goal_timing", "Goal In Time Interval", ["yes", "no"], requires_minute=True, availability="future", model_hint="goal_hazard_by_minute", data_requirements=["goal_events", "event_timestamps"], correlation_tags=["goal_timing", "goals"]),
    Market("football.first_goal_time", "football", "goal_timing", "First Goal Time", ["before", "after", "no_goal"], requires_minute=True, availability="future", model_hint="first_goal_hazard", data_requirements=["goal_events", "event_timestamps"], correlation_tags=["goal_timing", "goals"]),
    Market("football.team_to_score_first", "football", "goal_timing", "Team To Score First", ["home", "away", "no_goal"], availability="future", model_hint="first_goal_team_model", data_requirements=["goal_events"], correlation_tags=["goal_timing", "team_attacking"]),

    Market("football.anytime_goalscorer", "football", "player_goals", "Anytime Goalscorer", ["yes", "no"], requires_player=True, availability="future", model_hint="player_goal_probability", data_requirements=["lineups", "player_goals", "shots", "xg", "expected_minutes"], correlation_tags=["player_attacking", "goals"]),
    Market("football.first_goalscorer", "football", "player_goals", "First Goalscorer", ["yes", "no"], requires_player=True, availability="future", model_hint="player_first_goal_hazard", data_requirements=["goal_events", "lineups", "expected_minutes"], correlation_tags=["player_attacking", "goal_timing"]),

    Market("football.total_corners", "football", "corners", "Total Corners", ["over", "under"], requires_line=True, availability="prototype", model_hint="corners_regression", data_requirements=["corners"], correlation_tags=["corners", "tempo"]),
    Market("football.team_corners", "football", "corners", "Team Corners", ["over", "under"], requires_team=True, requires_line=True, availability="future", model_hint="team_corners_model", data_requirements=["corners", "team_style"], correlation_tags=["corners", "team_attacking"]),
    Market("football.first_corner", "football", "corners", "First Corner Team", ["home", "away"], availability="future", model_hint="first_corner_model", data_requirements=["event_timestamps", "corners"], correlation_tags=["corners", "tempo"]),

    Market("football.total_cards", "football", "discipline", "Total Cards", ["over", "under"], requires_line=True, availability="prototype", model_hint="cards_regression", data_requirements=["cards", "referee"], correlation_tags=["cards", "physicality"]),
    Market("football.team_cards", "football", "discipline", "Team Cards", ["over", "under"], requires_team=True, requires_line=True, availability="future", model_hint="team_cards_model", data_requirements=["cards", "referee", "team_fouls"], correlation_tags=["cards", "team_discipline"]),
    Market("football.player_card", "football", "discipline", "Player To Be Carded", ["yes", "no"], requires_player=True, availability="future", model_hint="player_card_model", data_requirements=["lineups", "player_cards", "referee", "position"], correlation_tags=["cards", "player_discipline"]),
    Market("football.red_card", "football", "discipline", "Red Card", ["yes", "no"], availability="future", model_hint="rare_event_model", data_requirements=["red_cards", "referee", "derby_flag"], correlation_tags=["cards", "chaos"]),

    Market("football.player_shots", "football", "player_stats", "Player Shots", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_shot_volume", data_requirements=["lineups", "shots", "expected_minutes"], correlation_tags=["player_attacking", "shots", "tempo"]),
    Market("football.player_shots_on_target", "football", "player_stats", "Player Shots On Target", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_sot_model", data_requirements=["lineups", "shots", "xg", "expected_minutes"], correlation_tags=["player_attacking", "shots", "goals"]),
    Market("football.player_assist", "football", "player_stats", "Player Assist", ["yes", "no"], requires_player=True, availability="future", model_hint="player_assist_model", data_requirements=["lineups", "assists", "key_passes", "xA"], correlation_tags=["player_creativity", "team_attacking"]),

    Market("football.total_offsides", "football", "offsides", "Total Offsides", ["over", "under"], requires_line=True, availability="future", model_hint="offside_model", data_requirements=["offsides", "team_style", "defensive_line"], correlation_tags=["offsides", "tempo"]),
    Market("football.penalty_awarded", "football", "penalties", "Penalty Awarded", ["yes", "no"], availability="future", model_hint="rare_event_model", data_requirements=["penalties", "box_touches", "referee"], correlation_tags=["penalties", "chaos", "goals"]),

    Market("football.halftime_result", "football", "halves", "Half Time Result", ["home", "draw", "away"], availability="future", model_hint="first_half_model", data_requirements=["half_time_scores", "goal_events"], correlation_tags=["first_half", "result"]),
    Market("football.ht_ft", "football", "halves", "Half Time / Full Time", ["HH", "HD", "HA", "DH", "DD", "DA", "AH", "AD", "AA"], availability="future", model_hint="state_transition_model", data_requirements=["half_time_scores", "full_time_scores"], correlation_tags=["first_half", "result"]),
]

NBA_MARKETS: List[Market] = [
    Market("nba.moneyline", "nba", "core", "Moneyline", ["home", "away"], availability="future", model_hint="nba_moneyline", data_requirements=["games", "team_stats", "odds"], correlation_tags=["result"]),
    Market("nba.spread", "nba", "spread", "Point Spread", ["home", "away"], requires_line=True, availability="future", model_hint="nba_spread_model", data_requirements=["team_stats", "rest", "injuries", "odds"], correlation_tags=["spread", "result"]),
    Market("nba.total_points", "nba", "totals", "Total Points", ["over", "under"], requires_line=True, availability="future", model_hint="nba_total_model", data_requirements=["pace", "off_rating", "def_rating", "odds"], correlation_tags=["totals", "pace"]),
    Market("nba.player_points", "nba", "player_props", "Player Points", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_points_model", data_requirements=["lineups", "minutes", "usage", "defense_matchup"], correlation_tags=["player_usage", "totals"]),
]


ALL_MARKETS = FOOTBALL_MARKETS + NBA_MARKETS


def by_id() -> Dict[str, Market]:
    return {m.market_id: m for m in ALL_MARKETS}


def supported_markets(sport: str | None = None) -> List[Market]:
    xs = ALL_MARKETS
    if sport:
        xs = [m for m in xs if m.sport == sport]
    return xs


def export_json(path: Path, sport: str | None = None):
    xs = [m.to_dict() for m in supported_markets(sport)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(xs, indent=2), encoding="utf-8")


def export_csv(path: Path, sport: str | None = None):
    xs = [m.to_dict() for m in supported_markets(sport)]
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(xs[0].keys()) if xs else []
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in xs:
            row = dict(row)
            row["selections"] = "|".join(row["selections"])
            row["data_requirements"] = "|".join(row["data_requirements"])
            row["correlation_tags"] = "|".join(row["correlation_tags"])
            w.writerow(row)


def main():
    ap = argparse.ArgumentParser(description="Inspect/export OmniBet market registry.")
    ap.add_argument("--sport", default=None)
    ap.add_argument("--availability", default=None, choices=[None, "supported", "prototype", "future"])
    ap.add_argument("--json", default=None)
    ap.add_argument("--csv", default=None)
    args = ap.parse_args()

    xs = supported_markets(args.sport)
    if args.availability:
        xs = [m for m in xs if m.availability == args.availability]

    if args.json:
        Path(args.json).write_text(json.dumps([m.to_dict() for m in xs], indent=2), encoding="utf-8")
    if args.csv:
        export_csv(Path(args.csv), args.sport)

    print(json.dumps({
        "count": len(xs),
        "by_sport": {s: sum(1 for m in xs if m.sport == s) for s in sorted({m.sport for m in xs})},
        "by_availability": {a: sum(1 for m in xs if m.availability == a) for a in sorted({m.availability for m in xs})},
        "markets": [m.to_dict() for m in xs],
    }, indent=2))


if __name__ == "__main__":
    main()
