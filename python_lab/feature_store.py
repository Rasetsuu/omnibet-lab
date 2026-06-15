#!/usr/bin/env python3
"""
OmniBet Lab feature store.

Creates a small SQLite feature store inspired by the NBA_Betting architecture:
- games: canonical fixture/results table
- team_snapshots: rolling point-in-time team features
- features_json: one JSON blob per match, safe for model training
- model_runs/predictions/bets/bankroll_events: future-ready betting workflow tables

The important rule: no leakage. For each fixture, rolling features only use matches
played strictly before that fixture date.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sqlite3
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    source TEXT,
    sport TEXT NOT NULL DEFAULT 'football',
    competition TEXT,
    match_date TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    neutral INTEGER DEFAULT 1,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS team_aliases (
    raw_name TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    sport TEXT NOT NULL DEFAULT 'football',
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_snapshots (
    snapshot_id TEXT PRIMARY KEY,
    team TEXT NOT NULL,
    match_date TEXT NOT NULL,
    rolling_n INTEGER NOT NULL,
    games_played INTEGER NOT NULL,
    gf_avg REAL,
    ga_avg REAL,
    shots_for_avg REAL,
    shots_against_avg REAL,
    corners_for_avg REAL,
    corners_against_avg REAL,
    fouls_for_avg REAL,
    fouls_against_avg REAL,
    rest_days REAL,
    form_points_avg REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS features_json (
    game_id TEXT PRIMARY KEY,
    feature_version TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    data TEXT NOT NULL,
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS model_runs (
    run_id TEXT PRIMARY KEY,
    model_name TEXT NOT NULL,
    sport TEXT NOT NULL,
    train_from TEXT,
    train_to TEXT,
    params_json TEXT,
    metrics_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id TEXT PRIMARY KEY,
    run_id TEXT,
    game_id TEXT,
    market TEXT NOT NULL,
    selection TEXT NOT NULL,
    probability REAL NOT NULL,
    fair_odds REAL,
    model_version TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(run_id) REFERENCES model_runs(run_id),
    FOREIGN KEY(game_id) REFERENCES games(game_id)
);

CREATE TABLE IF NOT EXISTS bets (
    bet_id TEXT PRIMARY KEY,
    prediction_id TEXT,
    bookmaker TEXT,
    market TEXT,
    selection TEXT,
    odds REAL,
    stake REAL,
    kelly_fraction REAL,
    result TEXT,
    profit_loss REAL,
    placed_at TEXT,
    settled_at TEXT,
    FOREIGN KEY(prediction_id) REFERENCES predictions(prediction_id)
);

CREATE TABLE IF NOT EXISTS bankroll_events (
    event_id TEXT PRIMARY KEY,
    event_time TEXT NOT NULL,
    event_type TEXT NOT NULL,
    amount REAL NOT NULL,
    balance_after REAL,
    note TEXT
);
"""


ALIASES = {
    "USA": "United States",
    "United States of America": "United States",
    "U.S.A.": "United States",
    "Czech Republic": "Czechia",
    "Turkey": "Turkiye",
    "Türkiye": "Turkiye",
    "Ivory Coast": "Côte d'Ivoire",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Curacao": "Curaçao",
    "DR Congo": "Congo DR",
    "Democratic Republic of Congo": "Congo DR",
    "South Korea": "Korea Republic",
    "Cape Verde Islands": "Cape Verde",
    "UAE": "United Arab Emirates",
}


def canonical(name: str) -> str:
    return ALIASES.get((name or "").strip(), (name or "").strip())


def parse_date(s: str) -> datetime:
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def safe_float(v) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def avg(vals: List[float]) -> Optional[float]:
    vals = [float(v) for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def points_for(team_goals: int, opp_goals: int) -> int:
    if team_goals > opp_goals:
        return 3
    if team_goals == opp_goals:
        return 1
    return 0


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA)
    for raw, can in ALIASES.items():
        con.execute(
            "INSERT OR REPLACE INTO team_aliases(raw_name, canonical_name, sport) VALUES (?, ?, 'football')",
            (raw, can),
        )
    con.commit()
    return con


def load_csv_rows(path: Path) -> List[dict]:
    with path.open("r", encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    rows = [r for r in rows if r.get("date") and r.get("home_team") and r.get("away_team")]
    rows.sort(key=lambda r: (r["date"], canonical(r["home_team"]), canonical(r["away_team"])))
    return rows


def make_game_id(row: dict, idx: int) -> str:
    date = row["date"][:10]
    home = canonical(row["home_team"]).replace(" ", "_")
    away = canonical(row["away_team"]).replace(" ", "_")
    comp = (row.get("league") or "unknown").replace(" ", "_")
    return f"football:{date}:{comp}:{home}:{away}:{idx}"


def build_snapshot(team: str, history: deque, match_date: datetime, rolling_n: int) -> dict:
    hist = list(history)[-rolling_n:]
    if not hist:
        return {
            "team": team,
            "games_played": 0,
            "gf_avg": None,
            "ga_avg": None,
            "shots_for_avg": None,
            "shots_against_avg": None,
            "corners_for_avg": None,
            "corners_against_avg": None,
            "fouls_for_avg": None,
            "fouls_against_avg": None,
            "rest_days": None,
            "form_points_avg": None,
        }
    last_date = hist[-1]["date"]
    return {
        "team": team,
        "games_played": len(hist),
        "gf_avg": avg([x["gf"] for x in hist]),
        "ga_avg": avg([x["ga"] for x in hist]),
        "shots_for_avg": avg([x.get("shots_for") for x in hist]),
        "shots_against_avg": avg([x.get("shots_against") for x in hist]),
        "corners_for_avg": avg([x.get("corners_for") for x in hist]),
        "corners_against_avg": avg([x.get("corners_against") for x in hist]),
        "fouls_for_avg": avg([x.get("fouls_for") for x in hist]),
        "fouls_against_avg": avg([x.get("fouls_against") for x in hist]),
        "rest_days": (match_date - last_date).days if last_date else None,
        "form_points_avg": avg([x["points"] for x in hist]),
    }


def diff(a: Optional[float], b: Optional[float]) -> Optional[float]:
    if a is None or b is None:
        return None
    return float(a) - float(b)


def ingest(csv_path: Path, db_path: Path, rolling_n: int = 10, feature_version: str = "v2_rolling10") -> dict:
    con = init_db(db_path)
    rows = load_csv_rows(csv_path)

    # Reset import tables for deterministic rebuilds.
    for table in ["games", "team_snapshots", "features_json"]:
        con.execute(f"DELETE FROM {table}")
    con.commit()

    history: Dict[str, deque] = defaultdict(lambda: deque(maxlen=200))
    imported = 0
    features = 0

    for idx, row in enumerate(rows):
        match_date = parse_date(row["date"])
        home = canonical(row["home_team"])
        away = canonical(row["away_team"])
        hg = int(float(row["home_goals"]))
        ag = int(float(row["away_goals"]))
        game_id = make_game_id(row, idx)

        raw = dict(row)
        raw["canonical_home"] = home
        raw["canonical_away"] = away

        con.execute(
            """INSERT OR REPLACE INTO games
               (game_id, source, sport, competition, match_date, home_team, away_team, home_score, away_score, neutral, raw_json)
               VALUES (?, ?, 'football', ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                game_id,
                row.get("source"),
                row.get("league"),
                row["date"][:10],
                home,
                away,
                hg,
                ag,
                1,
                json.dumps(raw, ensure_ascii=False),
            ),
        )
        imported += 1

        h_snap = build_snapshot(home, history[home], match_date, rolling_n)
        a_snap = build_snapshot(away, history[away], match_date, rolling_n)
        for snap in [h_snap, a_snap]:
            sid = f"{game_id}:{snap['team']}"
            con.execute(
                """INSERT OR REPLACE INTO team_snapshots
                   (snapshot_id, team, match_date, rolling_n, games_played, gf_avg, ga_avg, shots_for_avg,
                    shots_against_avg, corners_for_avg, corners_against_avg, fouls_for_avg, fouls_against_avg,
                    rest_days, form_points_avg, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    sid,
                    snap["team"],
                    row["date"][:10],
                    rolling_n,
                    snap["games_played"],
                    snap["gf_avg"],
                    snap["ga_avg"],
                    snap["shots_for_avg"],
                    snap["shots_against_avg"],
                    snap["corners_for_avg"],
                    snap["corners_against_avg"],
                    snap["fouls_for_avg"],
                    snap["fouls_against_avg"],
                    snap["rest_days"],
                    snap["form_points_avg"],
                    json.dumps(snap, ensure_ascii=False),
                ),
            )

        feature_blob = {
            "game_id": game_id,
            "date": row["date"][:10],
            "competition": row.get("league"),
            "home_team": home,
            "away_team": away,
            "target": {
                "home_goals": hg,
                "away_goals": ag,
                "outcome": "H" if hg > ag else ("A" if ag > hg else "D"),
                "over_25": 1 if (hg + ag) >= 3 else 0,
                "btts": 1 if hg > 0 and ag > 0 else 0,
            },
            "home_snapshot": h_snap,
            "away_snapshot": a_snap,
            "features": {
                "gf_avg_diff": diff(h_snap["gf_avg"], a_snap["gf_avg"]),
                "ga_avg_diff": diff(h_snap["ga_avg"], a_snap["ga_avg"]),
                "shots_for_avg_diff": diff(h_snap["shots_for_avg"], a_snap["shots_for_avg"]),
                "shots_against_avg_diff": diff(h_snap["shots_against_avg"], a_snap["shots_against_avg"]),
                "corners_for_avg_diff": diff(h_snap["corners_for_avg"], a_snap["corners_for_avg"]),
                "corners_against_avg_diff": diff(h_snap["corners_against_avg"], a_snap["corners_against_avg"]),
                "fouls_for_avg_diff": diff(h_snap["fouls_for_avg"], a_snap["fouls_for_avg"]),
                "rest_days_diff": diff(h_snap["rest_days"], a_snap["rest_days"]),
                "form_points_avg_diff": diff(h_snap["form_points_avg"], a_snap["form_points_avg"]),
                "home_games_played": h_snap["games_played"],
                "away_games_played": a_snap["games_played"],
            },
        }
        con.execute(
            "INSERT OR REPLACE INTO features_json(game_id, feature_version, data) VALUES (?, ?, ?)",
            (game_id, feature_version, json.dumps(feature_blob, ensure_ascii=False)),
        )
        features += 1

        # Update history AFTER snapshot construction to avoid leakage.
        history[home].append(
            {
                "date": match_date,
                "gf": hg,
                "ga": ag,
                "shots_for": safe_float(row.get("home_shots")),
                "shots_against": safe_float(row.get("away_shots")),
                "corners_for": safe_float(row.get("home_corners")),
                "corners_against": safe_float(row.get("away_corners")),
                "fouls_for": safe_float(row.get("home_fouls")),
                "fouls_against": safe_float(row.get("away_fouls")),
                "points": points_for(hg, ag),
            }
        )
        history[away].append(
            {
                "date": match_date,
                "gf": ag,
                "ga": hg,
                "shots_for": safe_float(row.get("away_shots")),
                "shots_against": safe_float(row.get("home_shots")),
                "corners_for": safe_float(row.get("away_corners")),
                "corners_against": safe_float(row.get("home_corners")),
                "fouls_for": safe_float(row.get("away_fouls")),
                "fouls_against": safe_float(row.get("home_fouls")),
                "points": points_for(ag, hg),
            }
        )

    con.commit()
    counts = {}
    for table in ["games", "team_aliases", "team_snapshots", "features_json"]:
        counts[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    con.close()
    return {"db_path": str(db_path), "imported_games": imported, "feature_rows": features, "counts": counts}


def inspect_db(db_path: Path) -> dict:
    con = sqlite3.connect(str(db_path))
    out = {}
    for table in ["games", "team_aliases", "team_snapshots", "features_json", "model_runs", "predictions", "bets"]:
        out[table] = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    samples = con.execute(
        "SELECT game_id, json_extract(data, '$.features.gf_avg_diff'), json_extract(data, '$.features.form_points_avg_diff') FROM features_json LIMIT 5"
    ).fetchall()
    con.close()
    return {"counts": out, "feature_samples": samples}


def main():
    ap = argparse.ArgumentParser(description="Build/inspect the OmniBet SQLite feature store.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    init = sub.add_parser("init", help="Create SQLite feature store from CSV.")
    init.add_argument("--data", default="../data/unified_intl_matches.csv")
    init.add_argument("--db", default="../build/omnibet.sqlite")
    init.add_argument("--rolling", type=int, default=10)

    ins = sub.add_parser("inspect", help="Inspect feature store counts.")
    ins.add_argument("--db", default="../build/omnibet.sqlite")

    args = ap.parse_args()
    if args.cmd == "init":
        res = ingest(Path(args.data), Path(args.db), rolling_n=args.rolling)
    else:
        res = inspect_db(Path(args.db))
    print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
