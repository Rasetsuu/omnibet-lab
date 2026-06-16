#!/usr/bin/env python3
"""
OmniBet Lab market registry.

This module is the long-term contract between data, models, GUI, and bet-builder.
Markets are not hardcoded only as "1X2 / Over 2.5"; each market declares:
- what sport it belongs to
- whether it needs team/player/minute/line input
- what data is required to train/predict it
- correlation tags for same-game builder risk
- settlement scope / phase scope

Football phase-awareness is critical: regulation-time markets, extra-time markets,
penalty shootout markets, and to-qualify markets must never share labels blindly.
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
    settlement_scope: str = "sport_default"
    phase_scope: List[str] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["data_requirements"] = self.data_requirements or []
        d["correlation_tags"] = self.correlation_tags or []
        d["phase_scope"] = self.phase_scope or []
        return d


REGULATION = ["regulation_first_half", "regulation_second_half", "regulation_stoppage"]
EXTRA_TIME = ["extra_time_first_half", "extra_time_first_half_stoppage", "extra_time_second_half", "extra_time_second_half_stoppage"]
PENALTIES = ["penalty_shootout"]

FOOTBALL_MARKETS: List[Market] = [
    Market("football.1x2", "football", "core", "90-Minute Result", ["home", "draw", "away"], availability="supported", model_hint="hybrid_1x2", data_requirements=["match_results_90"], correlation_tags=["result"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.double_chance", "football", "core", "90-Minute Double Chance", ["1X", "12", "X2"], availability="supported", model_hint="derived_1x2", data_requirements=["match_results_90"], correlation_tags=["result"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.draw_no_bet", "football", "core", "90-Minute Draw No Bet", ["home", "away"], availability="prototype", model_hint="derived_1x2", data_requirements=["match_results_90"], correlation_tags=["result"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.correct_score", "football", "core", "90-Minute Correct Score", ["0-0", "1-0", "1-1", "2-1", "2-0"], availability="prototype", model_hint="score_matrix", data_requirements=["score_matrix_90"], correlation_tags=["scoreline", "result", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.after_extra_time_winner", "football", "knockout", "Winner After Extra Time", ["home", "away"], availability="future", model_hint="knockout_state_model", data_requirements=["extra_time_events", "knockout_metadata"], correlation_tags=["result", "extra_time"], settlement_scope="after_extra_time", phase_scope=REGULATION + EXTRA_TIME),
    Market("football.to_qualify", "football", "knockout", "To Qualify / Advance", ["home", "away"], availability="future", model_hint="qualification_model", data_requirements=["knockout_metadata", "extra_time_events", "penalty_shootout"], correlation_tags=["result", "qualification"], settlement_scope="qualification", phase_scope=REGULATION + EXTRA_TIME + PENALTIES),
    Market("football.penalty_shootout_winner", "football", "knockout", "Penalty Shootout Winner", ["home", "away"], availability="future", model_hint="shootout_model", data_requirements=["penalty_shootout_events", "penalty_takers"], correlation_tags=["penalties", "qualification"], settlement_scope="penalty_shootout", phase_scope=PENALTIES),
    Market("football.extra_time_result", "football", "extra_time", "Extra Time Result", ["home", "draw", "away"], availability="future", model_hint="extra_time_state_model", data_requirements=["extra_time_events", "fatigue", "substitutions"], correlation_tags=["extra_time", "result"], settlement_scope="extra_time_only", phase_scope=EXTRA_TIME),
    Market("football.extra_time_total_goals", "football", "extra_time", "Extra Time Total Goals", ["over", "under"], requires_line=True, availability="future", model_hint="extra_time_goal_hazard", data_requirements=["extra_time_goal_events", "fatigue", "state_at_90"], correlation_tags=["extra_time", "goals"], settlement_scope="extra_time_only", phase_scope=EXTRA_TIME),
    Market("football.extra_time_goal_interval", "football", "extra_time", "Goal In Extra Time Interval", ["yes", "no"], requires_minute=True, availability="future", model_hint="extra_time_goal_hazard_by_minute", data_requirements=["extra_time_goal_events", "event_timestamps"], correlation_tags=["extra_time", "goal_timing", "goals"], settlement_scope="extra_time_only", phase_scope=EXTRA_TIME),

    Market("football.total_goals", "football", "goals", "90-Minute Total Goals", ["over", "under"], requires_line=True, availability="supported", model_hint="hybrid_over_goals", data_requirements=["match_results_90", "score_matrix_90"], correlation_tags=["goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.team_goals", "football", "goals", "90-Minute Team Goals", ["over", "under"], requires_team=True, requires_line=True, availability="prototype", model_hint="team_goal_lambda", data_requirements=["score_matrix_90", "team_attack"], correlation_tags=["team_attacking", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.btts", "football", "goals", "90-Minute Both Teams To Score", ["yes", "no"], availability="supported", model_hint="hybrid_btts", data_requirements=["match_results_90"], correlation_tags=["goals", "both_teams_score"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.goal_interval", "football", "goal_timing", "90-Minute Goal In Time Interval", ["yes", "no"], requires_minute=True, availability="future", model_hint="goal_hazard_by_minute", data_requirements=["goal_events", "event_timestamps"], correlation_tags=["goal_timing", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.first_goal_time", "football", "goal_timing", "90-Minute First Goal Time", ["before", "after", "no_goal"], requires_minute=True, availability="future", model_hint="first_goal_hazard", data_requirements=["goal_events", "event_timestamps"], correlation_tags=["goal_timing", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.team_to_score_first", "football", "goal_timing", "90-Minute Team To Score First", ["home", "away", "no_goal"], availability="future", model_hint="first_goal_team_model", data_requirements=["goal_events"], correlation_tags=["goal_timing", "team_attacking"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.anytime_goalscorer", "football", "player_goals", "90-Minute Anytime Goalscorer", ["yes", "no"], requires_player=True, availability="future", model_hint="player_goal_probability", data_requirements=["lineups", "player_goals", "shots", "xg", "expected_minutes"], correlation_tags=["player_attacking", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.first_goalscorer", "football", "player_goals", "90-Minute First Goalscorer", ["yes", "no"], requires_player=True, availability="future", model_hint="player_first_goal_hazard", data_requirements=["goal_events", "lineups", "expected_minutes"], correlation_tags=["player_attacking", "goal_timing"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.total_corners", "football", "corners", "90-Minute Total Corners", ["over", "under"], requires_line=True, availability="prototype", model_hint="corners_regression", data_requirements=["corners"], correlation_tags=["corners", "tempo"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.team_corners", "football", "corners", "90-Minute Team Corners", ["over", "under"], requires_team=True, requires_line=True, availability="future", model_hint="team_corners_model", data_requirements=["corners", "team_style"], correlation_tags=["corners", "team_attacking"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.first_corner", "football", "corners", "90-Minute First Corner Team", ["home", "away"], availability="future", model_hint="first_corner_model", data_requirements=["event_timestamps", "corners"], correlation_tags=["corners", "tempo"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.total_cards", "football", "discipline", "90-Minute Total Cards", ["over", "under"], requires_line=True, availability="prototype", model_hint="cards_regression", data_requirements=["cards", "referee"], correlation_tags=["cards", "physicality"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.team_cards", "football", "discipline", "90-Minute Team Cards", ["over", "under"], requires_team=True, requires_line=True, availability="future", model_hint="team_cards_model", data_requirements=["cards", "referee", "team_fouls"], correlation_tags=["cards", "team_discipline"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.player_card", "football", "discipline", "90-Minute Player To Be Carded", ["yes", "no"], requires_player=True, availability="future", model_hint="player_card_model", data_requirements=["lineups", "player_cards", "referee", "position"], correlation_tags=["cards", "player_discipline"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.red_card", "football", "discipline", "90-Minute Red Card", ["yes", "no"], availability="future", model_hint="rare_event_model", data_requirements=["red_cards", "referee", "derby_flag"], correlation_tags=["cards", "chaos"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.player_shots", "football", "player_stats", "90-Minute Player Shots", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_shot_volume", data_requirements=["lineups", "shots", "expected_minutes"], correlation_tags=["player_attacking", "shots", "tempo"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.player_shots_on_target", "football", "player_stats", "90-Minute Player Shots On Target", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_sot_model", data_requirements=["lineups", "shots", "xg", "expected_minutes"], correlation_tags=["player_attacking", "shots", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.player_assist", "football", "player_stats", "90-Minute Player Assist", ["yes", "no"], requires_player=True, availability="future", model_hint="player_assist_model", data_requirements=["lineups", "assists", "key_passes", "xA"], correlation_tags=["player_creativity", "team_attacking"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.total_offsides", "football", "offsides", "90-Minute Total Offsides", ["over", "under"], requires_line=True, availability="future", model_hint="offside_model", data_requirements=["offsides", "team_style", "defensive_line"], correlation_tags=["offsides", "tempo"], settlement_scope="regulation_time", phase_scope=REGULATION),
    Market("football.penalty_awarded", "football", "penalties", "90-Minute Penalty Awarded", ["yes", "no"], availability="future", model_hint="rare_event_model", data_requirements=["penalties", "box_touches", "referee"], correlation_tags=["penalties", "chaos", "goals"], settlement_scope="regulation_time", phase_scope=REGULATION),

    Market("football.halftime_result", "football", "halves", "Half Time Result", ["home", "draw", "away"], availability="future", model_hint="first_half_model", data_requirements=["half_time_scores", "goal_events"], correlation_tags=["first_half", "result"], settlement_scope="first_half", phase_scope=["regulation_first_half"]),
    Market("football.ht_ft", "football", "halves", "Half Time / 90-Minute Full Time", ["HH", "HD", "HA", "DH", "DD", "DA", "AH", "AD", "AA"], availability="future", model_hint="state_transition_model", data_requirements=["half_time_scores", "full_time_scores_90"], correlation_tags=["first_half", "result"], settlement_scope="regulation_time", phase_scope=REGULATION),
]

NBA_MARKETS: List[Market] = [
    Market("nba.moneyline", "nba", "core", "Moneyline", ["home", "away"], availability="future", model_hint="nba_moneyline", data_requirements=["games", "team_stats", "odds"], correlation_tags=["result"], settlement_scope="game_including_overtime"),
    Market("nba.spread", "nba", "spread", "Point Spread", ["home", "away"], requires_line=True, availability="future", model_hint="nba_spread_model", data_requirements=["team_stats", "rest", "injuries", "odds"], correlation_tags=["spread", "result"], settlement_scope="game_including_overtime"),
    Market("nba.total_points", "nba", "totals", "Total Points", ["over", "under"], requires_line=True, availability="future", model_hint="nba_total_model", data_requirements=["pace", "off_rating", "def_rating", "odds"], correlation_tags=["totals", "pace"], settlement_scope="game_including_overtime"),
    Market("nba.player_points", "nba", "player_props", "Player Points", ["over", "under"], requires_player=True, requires_line=True, availability="future", model_hint="player_points_model", data_requirements=["lineups", "minutes", "usage", "defense_matchup"], correlation_tags=["player_usage", "totals"], settlement_scope="game_including_overtime"),
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
            row["phase_scope"] = "|".join(row["phase_scope"])
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
        "by_settlement_scope": {a: sum(1 for m in xs if m.settlement_scope == a) for a in sorted({m.settlement_scope for m in xs})},
        "markets": [m.to_dict() for m in xs],
    }, indent=2))


if __name__ == "__main__":
    main()
