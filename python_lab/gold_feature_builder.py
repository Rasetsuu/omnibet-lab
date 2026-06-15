#!/usr/bin/env python3
"""
OmniBet Lab v5 gold feature builder.

v4 created the warehouse and adapters.
v5 starts the "gold" layer: model-ready, leakage-safe features.

Inputs:
- matches_norm
- match_events
- lineups
- odds_snapshots

Outputs:
- gold_team_snapshots
- gold_match_features
- gold_goal_timing_features
- gold_player_snapshots
- gold_market_features

This works even when only match-score data exists. Event/player features become
active automatically once StatsBomb/TheStatsAPI event/lineup/player data exists.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict, deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


GOLD_SCHEMA = """
CREATE TABLE IF NOT EXISTS gold_team_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    team_id TEXT,
    team_name TEXT NOT NULL,
    opponent_id TEXT,
    opponent_name TEXT,
    snapshot_date TEXT,
    rolling_n INTEGER NOT NULL,
    prior_matches INTEGER NOT NULL,
    goals_for_avg REAL,
    goals_against_avg REAL,
    xg_for_avg REAL,
    xg_against_avg REAL,
    shots_for_avg REAL,
    shots_against_avg REAL,
    cards_for_avg REAL,
    cards_against_avg REAL,
    corners_for_avg REAL,
    corners_against_avg REAL,
    first_half_goals_for_avg REAL,
    second_half_goals_for_avg REAL,
    points_avg REAL,
    rest_days REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS gold_match_features (
    feature_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    source_id TEXT,
    sport TEXT NOT NULL,
    match_date TEXT,
    competition_id TEXT,
    season_id TEXT,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    target_home_goals INTEGER,
    target_away_goals INTEGER,
    target_outcome TEXT,
    target_over_25 INTEGER,
    target_btts INTEGER,
    feature_version TEXT NOT NULL,
    features_json TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gold_goal_timing_features (
    row_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    source_id TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    match_date TEXT,
    first_goal_minute INTEGER,
    first_goal_team TEXT,
    home_goal_0_15 INTEGER,
    away_goal_0_15 INTEGER,
    goal_0_15 INTEGER,
    goal_16_30 INTEGER,
    goal_31_45 INTEGER,
    goal_46_60 INTEGER,
    goal_61_75 INTEGER,
    goal_76_90 INTEGER,
    first_half_goals INTEGER,
    second_half_goals INTEGER,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS gold_player_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    player_id TEXT NOT NULL,
    player_name TEXT,
    team_id TEXT,
    snapshot_date TEXT,
    prior_matches INTEGER,
    expected_minutes REAL,
    goals_90 REAL,
    shots_90 REAL,
    xg_90 REAL,
    cards_90 REAL,
    player_score REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS gold_market_features (
    row_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    bookmaker TEXT,
    odds_decimal REAL,
    implied_probability REAL,
    captured_at TEXT,
    is_live INTEGER,
    features_json TEXT
);
"""


def parse_date(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.strptime(str(s)[:10], "%Y-%m-%d")
    except Exception:
        return None


def avg(vals: List[Optional[float]]) -> Optional[float]:
    xs = [float(v) for v in vals if v is not None and math.isfinite(float(v))]
    return sum(xs) / len(xs) if xs else None


def points_for(gf: Optional[int], ga: Optional[int]) -> Optional[int]:
    if gf is None or ga is None:
        return None
    if gf > ga:
        return 3
    if gf == ga:
        return 1
    return 0


def outcome(hg: Optional[int], ag: Optional[int]) -> Optional[str]:
    if hg is None or ag is None:
        return None
    if hg > ag:
        return "H"
    if hg < ag:
        return "A"
    return "D"


def safe_div(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None or b == 0:
        return None
    return a / b


def connect(db: Path) -> sqlite3.Connection:
    con = sqlite3.connect(str(db))
    con.executescript(GOLD_SCHEMA)
    return con


def event_summary_for_match(con: sqlite3.Connection, match_id: str, home_id: Optional[str], away_id: Optional[str]) -> Dict[str, Any]:
    rows = con.execute(
        """SELECT event_type, minute, second, team_id, player_id, outcome, xg, raw_json
           FROM match_events WHERE match_id=?""",
        (match_id,),
    ).fetchall()
    out = {
        "has_events": bool(rows),
        "home_shots": 0, "away_shots": 0,
        "home_xg": 0.0, "away_xg": 0.0,
        "home_cards": 0, "away_cards": 0,
        "home_corners": 0, "away_corners": 0,
        "home_first_half_goals": 0, "away_first_half_goals": 0,
        "home_second_half_goals": 0, "away_second_half_goals": 0,
        "goals": [],
    }
    for etype, minute, second, team_id, player_id, ev_outcome, xg, raw_json in rows:
        et = (etype or "").lower()
        team_side = "home" if team_id and home_id and team_id == home_id else ("away" if team_id and away_id and team_id == away_id else None)
        if team_side is None:
            continue
        if "shot" in et:
            out[f"{team_side}_shots"] += 1
            if xg is not None:
                out[f"{team_side}_xg"] += float(xg)
            if (ev_outcome or "").lower() == "goal":
                goal = {"minute": minute, "second": second, "team_side": team_side, "team_id": team_id, "player_id": player_id}
                out["goals"].append(goal)
                if minute is not None and int(minute) <= 45:
                    out[f"{team_side}_first_half_goals"] += 1
                else:
                    out[f"{team_side}_second_half_goals"] += 1
        if "card" in et or "bad behaviour" in et:
            out[f"{team_side}_cards"] += 1
        # StatsBomb corners usually appear as a pass/corner subtype in raw JSON.
        if raw_json and "Corner" in raw_json:
            out[f"{team_side}_corners"] += 1
    out["goals"].sort(key=lambda g: (g["minute"] if g["minute"] is not None else 999, g["second"] if g["second"] is not None else 999))
    return out


def match_rows(con: sqlite3.Connection) -> List[dict]:
    rows = con.execute(
        """SELECT match_id, source_id, sport, competition_id, season_id, match_date, status,
                  home_team_id, away_team_id, home_team_name, away_team_name, home_score, away_score, raw_json
           FROM matches_norm
           WHERE sport='football'
           ORDER BY match_date, match_id"""
    ).fetchall()
    keys = [
        "match_id", "source_id", "sport", "competition_id", "season_id", "match_date", "status",
        "home_team_id", "away_team_id", "home_team_name", "away_team_name", "home_score", "away_score", "raw_json",
    ]
    return [dict(zip(keys, r)) for r in rows]


def build_team_snapshot(team_name: str, team_id: Optional[str], opponent_name: str, opponent_id: Optional[str], history: deque, match_date: Optional[datetime], rolling_n: int) -> Dict[str, Any]:
    hist = list(history)[-rolling_n:]
    if not hist:
        return {
            "team_id": team_id,
            "team_name": team_name,
            "opponent_id": opponent_id,
            "opponent_name": opponent_name,
            "prior_matches": 0,
            "goals_for_avg": None,
            "goals_against_avg": None,
            "xg_for_avg": None,
            "xg_against_avg": None,
            "shots_for_avg": None,
            "shots_against_avg": None,
            "cards_for_avg": None,
            "cards_against_avg": None,
            "corners_for_avg": None,
            "corners_against_avg": None,
            "first_half_goals_for_avg": None,
            "second_half_goals_for_avg": None,
            "points_avg": None,
            "rest_days": None,
        }
    last_date = hist[-1].get("date")
    return {
        "team_id": team_id,
        "team_name": team_name,
        "opponent_id": opponent_id,
        "opponent_name": opponent_name,
        "prior_matches": len(hist),
        "goals_for_avg": avg([x.get("gf") for x in hist]),
        "goals_against_avg": avg([x.get("ga") for x in hist]),
        "xg_for_avg": avg([x.get("xg_for") for x in hist]),
        "xg_against_avg": avg([x.get("xg_against") for x in hist]),
        "shots_for_avg": avg([x.get("shots_for") for x in hist]),
        "shots_against_avg": avg([x.get("shots_against") for x in hist]),
        "cards_for_avg": avg([x.get("cards_for") for x in hist]),
        "cards_against_avg": avg([x.get("cards_against") for x in hist]),
        "corners_for_avg": avg([x.get("corners_for") for x in hist]),
        "corners_against_avg": avg([x.get("corners_against") for x in hist]),
        "first_half_goals_for_avg": avg([x.get("fh_gf") for x in hist]),
        "second_half_goals_for_avg": avg([x.get("sh_gf") for x in hist]),
        "points_avg": avg([x.get("points") for x in hist]),
        "rest_days": (match_date - last_date).days if match_date is not None and last_date is not None else None,
    }


def diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return float(a) - float(b)


def insert_snapshot(con: sqlite3.Connection, match_id: str, side: str, snapshot_date: str, rolling_n: int, snap: Dict[str, Any]) -> None:
    sid = f"{match_id}:{side}:{rolling_n}"
    con.execute(
        """INSERT OR REPLACE INTO gold_team_snapshots
           (snapshot_id, match_id, team_id, team_name, opponent_id, opponent_name, snapshot_date, rolling_n,
            prior_matches, goals_for_avg, goals_against_avg, xg_for_avg, xg_against_avg, shots_for_avg,
            shots_against_avg, cards_for_avg, cards_against_avg, corners_for_avg, corners_against_avg,
            first_half_goals_for_avg, second_half_goals_for_avg, points_avg, rest_days, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            sid, match_id, snap["team_id"], snap["team_name"], snap["opponent_id"], snap["opponent_name"],
            snapshot_date, rolling_n, snap["prior_matches"], snap["goals_for_avg"], snap["goals_against_avg"],
            snap["xg_for_avg"], snap["xg_against_avg"], snap["shots_for_avg"], snap["shots_against_avg"],
            snap["cards_for_avg"], snap["cards_against_avg"], snap["corners_for_avg"], snap["corners_against_avg"],
            snap["first_half_goals_for_avg"], snap["second_half_goals_for_avg"], snap["points_avg"], snap["rest_days"],
            json.dumps(snap, ensure_ascii=False),
        ),
    )


def insert_goal_timing(con: sqlite3.Connection, m: dict, ev: dict) -> None:
    goals = ev["goals"]
    first = goals[0] if goals else None
    buckets = {"0_15": 0, "16_30": 0, "31_45": 0, "46_60": 0, "61_75": 0, "76_90": 0}
    for g in goals:
        minute = g.get("minute")
        if minute is None:
            continue
        minute = int(minute)
        if minute <= 15:
            buckets["0_15"] += 1
        elif minute <= 30:
            buckets["16_30"] += 1
        elif minute <= 45:
            buckets["31_45"] += 1
        elif minute <= 60:
            buckets["46_60"] += 1
        elif minute <= 75:
            buckets["61_75"] += 1
        else:
            buckets["76_90"] += 1
    con.execute(
        """INSERT OR REPLACE INTO gold_goal_timing_features
           (row_id, match_id, source_id, home_team_name, away_team_name, match_date, first_goal_minute, first_goal_team,
            home_goal_0_15, away_goal_0_15, goal_0_15, goal_16_30, goal_31_45, goal_46_60, goal_61_75, goal_76_90,
            first_half_goals, second_half_goals, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            f"{m['match_id']}:goal_timing", m["match_id"], m["source_id"], m["home_team_name"], m["away_team_name"], m["match_date"],
            first.get("minute") if first else None,
            first.get("team_side") if first else None,
            1 if any(g.get("team_side") == "home" and g.get("minute") is not None and int(g["minute"]) <= 15 for g in goals) else 0,
            1 if any(g.get("team_side") == "away" and g.get("minute") is not None and int(g["minute"]) <= 15 for g in goals) else 0,
            buckets["0_15"], buckets["16_30"], buckets["31_45"], buckets["46_60"], buckets["61_75"], buckets["76_90"],
            ev["home_first_half_goals"] + ev["away_first_half_goals"], ev["home_second_half_goals"] + ev["away_second_half_goals"],
            json.dumps({"goals": goals, "buckets": buckets}, ensure_ascii=False),
        ),
    )


def build_gold(db_path: Path, rolling_n: int = 10, reset: bool = True) -> dict:
    con = connect(db_path)
    if reset:
        for t in ["gold_team_snapshots", "gold_match_features", "gold_goal_timing_features", "gold_player_snapshots", "gold_market_features"]:
            con.execute(f"DELETE FROM {t}")
        con.commit()

    matches = match_rows(con)
    history = defaultdict(lambda: deque(maxlen=500))
    rows_written = 0
    event_matches = 0

    for m in matches:
        match_date = parse_date(m["match_date"])
        home = m["home_team_name"] or m["home_team_id"] or "HOME"
        away = m["away_team_name"] or m["away_team_id"] or "AWAY"
        home_id = m["home_team_id"]
        away_id = m["away_team_id"]

        ev = event_summary_for_match(con, m["match_id"], home_id, away_id)
        if ev["has_events"]:
            event_matches += 1
            insert_goal_timing(con, m, ev)

        hs = build_team_snapshot(home, home_id, away, away_id, history[home_id or home], match_date, rolling_n)
        aas = build_team_snapshot(away, away_id, home, home_id, history[away_id or away], match_date, rolling_n)

        insert_snapshot(con, m["match_id"], "home", m["match_date"], rolling_n, hs)
        insert_snapshot(con, m["match_id"], "away", m["match_date"], rolling_n, aas)

        hg = m["home_score"]
        ag = m["away_score"]
        feat = {
            "home_prior_matches": hs["prior_matches"],
            "away_prior_matches": aas["prior_matches"],
            "goals_for_avg_diff": diff(hs["goals_for_avg"], aas["goals_for_avg"]),
            "goals_against_avg_diff": diff(hs["goals_against_avg"], aas["goals_against_avg"]),
            "xg_for_avg_diff": diff(hs["xg_for_avg"], aas["xg_for_avg"]),
            "xg_against_avg_diff": diff(hs["xg_against_avg"], aas["xg_against_avg"]),
            "shots_for_avg_diff": diff(hs["shots_for_avg"], aas["shots_for_avg"]),
            "shots_against_avg_diff": diff(hs["shots_against_avg"], aas["shots_against_avg"]),
            "cards_for_avg_diff": diff(hs["cards_for_avg"], aas["cards_for_avg"]),
            "cards_against_avg_diff": diff(hs["cards_against_avg"], aas["cards_against_avg"]),
            "corners_for_avg_diff": diff(hs["corners_for_avg"], aas["corners_for_avg"]),
            "corners_against_avg_diff": diff(hs["corners_against_avg"], aas["corners_against_avg"]),
            "first_half_goals_for_avg_diff": diff(hs["first_half_goals_for_avg"], aas["first_half_goals_for_avg"]),
            "second_half_goals_for_avg_diff": diff(hs["second_half_goals_for_avg"], aas["second_half_goals_for_avg"]),
            "points_avg_diff": diff(hs["points_avg"], aas["points_avg"]),
            "rest_days_diff": diff(hs["rest_days"], aas["rest_days"]),
            "has_event_data": ev["has_events"],
        }

        con.execute(
            """INSERT OR REPLACE INTO gold_match_features
               (feature_id, match_id, source_id, sport, match_date, competition_id, season_id,
                home_team_id, away_team_id, home_team_name, away_team_name, target_home_goals, target_away_goals,
                target_outcome, target_over_25, target_btts, feature_version, features_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"{m['match_id']}:v5_gold", m["match_id"], m["source_id"], m["sport"], m["match_date"],
                m["competition_id"], m["season_id"], home_id, away_id, home, away, hg, ag,
                outcome(hg, ag), 1 if hg is not None and ag is not None and hg + ag >= 3 else None,
                1 if hg is not None and ag is not None and hg > 0 and ag > 0 else None,
                f"v5_gold_rolling{rolling_n}", json.dumps({"features": feat, "home_snapshot": hs, "away_snapshot": aas}, ensure_ascii=False),
            ),
        )
        rows_written += 1

        # Update team histories after features (leakage-safe).
        if hg is not None and ag is not None:
            history[home_id or home].append({
                "date": match_date, "gf": hg, "ga": ag, "points": points_for(hg, ag),
                "xg_for": ev["home_xg"] if ev["has_events"] else None,
                "xg_against": ev["away_xg"] if ev["has_events"] else None,
                "shots_for": ev["home_shots"] if ev["has_events"] else None,
                "shots_against": ev["away_shots"] if ev["has_events"] else None,
                "cards_for": ev["home_cards"] if ev["has_events"] else None,
                "cards_against": ev["away_cards"] if ev["has_events"] else None,
                "corners_for": ev["home_corners"] if ev["has_events"] else None,
                "corners_against": ev["away_corners"] if ev["has_events"] else None,
                "fh_gf": ev["home_first_half_goals"] if ev["has_events"] else None,
                "sh_gf": ev["home_second_half_goals"] if ev["has_events"] else None,
            })
            history[away_id or away].append({
                "date": match_date, "gf": ag, "ga": hg, "points": points_for(ag, hg),
                "xg_for": ev["away_xg"] if ev["has_events"] else None,
                "xg_against": ev["home_xg"] if ev["has_events"] else None,
                "shots_for": ev["away_shots"] if ev["has_events"] else None,
                "shots_against": ev["home_shots"] if ev["has_events"] else None,
                "cards_for": ev["away_cards"] if ev["has_events"] else None,
                "cards_against": ev["home_cards"] if ev["has_events"] else None,
                "corners_for": ev["away_corners"] if ev["has_events"] else None,
                "corners_against": ev["home_corners"] if ev["has_events"] else None,
                "fh_gf": ev["away_first_half_goals"] if ev["has_events"] else None,
                "sh_gf": ev["away_second_half_goals"] if ev["has_events"] else None,
            })

    # Market odds features.
    odds_rows = con.execute(
        """SELECT odds_id, match_id, bookmaker, market_id, selection, line, odds_decimal, captured_at, is_live
           FROM odds_snapshots ORDER BY captured_at, odds_id"""
    ).fetchall()
    odds_written = 0
    for odds_id, match_id, bookmaker, market_id, selection, line, odds_decimal, captured_at, is_live in odds_rows:
        implied = 1.0 / odds_decimal if odds_decimal and odds_decimal > 1 else None
        con.execute(
            """INSERT OR REPLACE INTO gold_market_features
               (row_id, match_id, market_id, selection, bookmaker, odds_decimal, implied_probability, captured_at, is_live, features_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"{odds_id}:gold", match_id, market_id, selection, bookmaker, odds_decimal, implied,
                captured_at, is_live, json.dumps({"line": line}, ensure_ascii=False),
            ),
        )
        odds_written += 1

    con.commit()
    counts = {}
    for t in ["gold_team_snapshots", "gold_match_features", "gold_goal_timing_features", "gold_player_snapshots", "gold_market_features"]:
        counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()

    return {
        "db": str(db_path),
        "matches_seen": len(matches),
        "gold_match_features_written": rows_written,
        "event_matches_seen": event_matches,
        "gold_market_features_written": odds_written,
        "counts": counts,
        "note": "Event/player features activate when match_events/lineups/player data exist in the warehouse.",
    }


def inspect_gold(db_path: Path, limit: int = 5) -> dict:
    con = connect(db_path)
    counts = {}
    for t in ["gold_team_snapshots", "gold_match_features", "gold_goal_timing_features", "gold_player_snapshots", "gold_market_features"]:
        counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    samples = con.execute(
        """SELECT match_id, home_team_name, away_team_name, target_outcome, target_over_25,
                  json_extract(features_json, '$.features.goals_for_avg_diff'),
                  json_extract(features_json, '$.features.points_avg_diff')
           FROM gold_match_features LIMIT ?""",
        (limit,),
    ).fetchall()
    con.close()
    return {"counts": counts, "samples": samples}


def main():
    ap = argparse.ArgumentParser(description="Build/inspect v5 gold model features.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_build = sub.add_parser("build")
    p_build.add_argument("--db", default="../build/omnibet.sqlite")
    p_build.add_argument("--rolling", type=int, default=10)
    p_build.add_argument("--no-reset", action="store_true")

    p_inspect = sub.add_parser("inspect")
    p_inspect.add_argument("--db", default="../build/omnibet.sqlite")
    p_inspect.add_argument("--limit", type=int, default=5)

    args = ap.parse_args()
    if args.cmd == "build":
        out = build_gold(Path(args.db), rolling_n=args.rolling, reset=not args.no_reset)
    else:
        out = inspect_gold(Path(args.db), limit=args.limit)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
