#!/usr/bin/env python3
"""
OmniBet Lab v13 synthetic event demo.

Purpose:
- Keep the normal database/pack clean.
- Create a separate demo DB copied from the current warehouse.
- Add small PUBLIC-SAFE synthetic football matches with events, lineups and players.
- Rebuild gold features so event/player/goal-timing tables become non-zero.
- Export a separate compressed demo pack.

This is not predictive data. It exists to prove the pipeline shape:
matches -> events/lineups -> gold_goal_timing_features/player_snapshots -> compressed pack.
"""
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from pathlib import Path
from datetime import datetime

from adapters.warehouse import connect, register_default_sources, table_counts
from gold_feature_builder import build_gold
from goal_timing_lab import analyze as analyze_goal_timing
from player_score_lab import build_player_scores
from export_data_pack import export_pack, DEFAULT_TABLES


TEAMS = {
    "ESP": "Spain",
    "CPV": "Cape Verde",
    "URU": "Uruguay",
    "KSA": "Saudi Arabia",
}

PLAYERS = {
    "ESP9": ("Spain Striker", "ESP", "Forward"),
    "ESP10": ("Spain Creator", "ESP", "Midfielder"),
    "ESP7": ("Spain Winger", "ESP", "Forward"),
    "CPV9": ("Cape Verde Forward", "CPV", "Forward"),
    "CPV11": ("Cape Verde Winger", "CPV", "Forward"),
    "URU9": ("Uruguay Striker", "URU", "Forward"),
    "URU10": ("Uruguay Creator", "URU", "Midfielder"),
    "KSA9": ("Saudi Arabia Forward", "KSA", "Forward"),
    "KSA8": ("Saudi Arabia Midfielder", "KSA", "Midfielder"),
}


MATCHES = [
    {
        "match_id": "synthetic:v13:900001",
        "date": "2026-06-15",
        "home": "ESP",
        "away": "CPV",
        "home_score": 3,
        "away_score": 0,
        "goals": [(12, "ESP", "ESP9", 0.31), (49, "ESP", "ESP7", 0.19), (77, "ESP", "ESP9", 0.42)],
        "shots": [("ESP", "ESP10", 22, 0.08), ("ESP", "ESP7", 63, 0.12), ("CPV", "CPV9", 31, 0.06), ("CPV", "CPV11", 71, 0.04)],
        "cards": [("CPV", "CPV11", 58), ("ESP", "ESP10", 81)],
    },
    {
        "match_id": "synthetic:v13:900002",
        "date": "2026-06-15",
        "home": "KSA",
        "away": "URU",
        "home_score": 1,
        "away_score": 2,
        "goals": [(23, "URU", "URU9", 0.28), (68, "KSA", "KSA9", 0.22), (85, "URU", "URU10", 0.14)],
        "shots": [("URU", "URU9", 9, 0.10), ("KSA", "KSA8", 39, 0.05), ("URU", "URU10", 55, 0.09), ("KSA", "KSA9", 72, 0.07)],
        "cards": [("KSA", "KSA8", 44)],
    },
    {
        "match_id": "synthetic:v13:900003",
        "date": "2026-06-20",
        "home": "ESP",
        "away": "URU",
        "home_score": 2,
        "away_score": 2,
        "goals": [(8, "ESP", "ESP7", 0.18), (41, "URU", "URU9", 0.33), (62, "ESP", "ESP10", 0.15), (88, "URU", "URU9", 0.29)],
        "shots": [("ESP", "ESP9", 18, 0.11), ("URU", "URU10", 24, 0.07), ("ESP", "ESP7", 70, 0.10), ("URU", "URU9", 79, 0.16)],
        "cards": [("ESP", "ESP10", 53), ("URU", "URU10", 60)],
    },
    {
        "match_id": "synthetic:v13:900004",
        "date": "2026-06-20",
        "home": "CPV",
        "away": "KSA",
        "home_score": 1,
        "away_score": 1,
        "goals": [(35, "CPV", "CPV9", 0.24), (79, "KSA", "KSA9", 0.21)],
        "shots": [("CPV", "CPV11", 15, 0.06), ("KSA", "KSA8", 52, 0.08), ("CPV", "CPV9", 69, 0.12), ("KSA", "KSA9", 86, 0.10)],
        "cards": [("CPV", "CPV11", 29), ("KSA", "KSA8", 73)],
    },
]


def insert_demo(con: sqlite3.Connection) -> dict:
    source_id = "synthetic_event_demo_v13"
    con.execute(
        """INSERT OR REPLACE INTO source_registry
           (source_id, sport, source_type, display_name, update_mode, url, api_key_env,
            enabled, min_interval_minutes, notes)
           VALUES (?, 'football', 'synthetic_demo', 'Synthetic Event Demo v13', 'manual', NULL, NULL, 1, 999999,
                   'Public-safe synthetic data only; proves events/lineups/goal-timing/player pipeline.')""",
        (source_id,),
    )

    for team_id, name in TEAMS.items():
        con.execute(
            """INSERT OR REPLACE INTO teams (team_id, source_id, sport, name, country, raw_json)
               VALUES (?, ?, 'football', ?, NULL, ?)""",
            (team_id, source_id, name, json.dumps({"synthetic": True})),
        )

    for player_id, (name, team_id, pos) in PLAYERS.items():
        con.execute(
            """INSERT OR REPLACE INTO players
               (player_id, source_id, sport, name, nationality, birth_date, position, current_team_id, raw_json)
               VALUES (?, ?, 'football', ?, NULL, NULL, ?, ?, ?)""",
            (player_id, source_id, name, pos, team_id, json.dumps({"synthetic": True})),
        )

    event_count = 0
    lineup_count = 0
    for m in MATCHES:
        home = m["home"]
        away = m["away"]
        con.execute(
            """INSERT OR REPLACE INTO matches_norm
               (match_id, source_id, sport, competition_id, season_id, match_date, status,
                home_team_id, away_team_id, home_team_name, away_team_name,
                home_score, away_score, venue, raw_json)
               VALUES (?, ?, 'football', 'SYN-V13', '2026', ?, 'finished',
                       ?, ?, ?, ?, ?, ?, 'Synthetic Stadium', ?)""",
            (
                m["match_id"], source_id, m["date"], home, away, TEAMS[home], TEAMS[away],
                m["home_score"], m["away_score"], json.dumps(m, ensure_ascii=False),
            ),
        )

        # Put all known team players in lineups for their match teams.
        match_players = [pid for pid, (_, tid, _) in PLAYERS.items() if tid in {home, away}]
        for pid in match_players:
            name, tid, pos = PLAYERS[pid]
            lineup_id = f"{m['match_id']}:{pid}"
            con.execute(
                """INSERT OR REPLACE INTO lineups
                   (lineup_id, match_id, team_id, player_id, player_name, started,
                    position, shirt_number, minutes_played, raw_json)
                   VALUES (?, ?, ?, ?, ?, 1, ?, NULL, 90.0, ?)""",
                (lineup_id, m["match_id"], tid, pid, name, pos, json.dumps({"synthetic": True})),
            )
            lineup_count += 1

        for idx, (minute, team_id, player_id, xg) in enumerate(m["goals"]):
            ev_id = f"{m['match_id']}:goal:{idx}"
            con.execute(
                """INSERT OR REPLACE INTO match_events
                   (event_id, match_id, source_id, event_type, minute, second, period,
                    team_id, player_id, related_player_id, x, y, outcome, xg, raw_json)
                   VALUES (?, ?, ?, 'Shot', ?, 0, ?, ?, ?, NULL, 100.0, 40.0, 'Goal', ?, ?)""",
                (
                    ev_id, m["match_id"], source_id, minute, "1H" if minute <= 45 else "2H",
                    team_id, player_id, xg, json.dumps({"synthetic": True, "kind": "goal"}),
                ),
            )
            event_count += 1

        for idx, (team_id, player_id, minute, xg) in enumerate(m["shots"]):
            ev_id = f"{m['match_id']}:shot:{idx}"
            con.execute(
                """INSERT OR REPLACE INTO match_events
                   (event_id, match_id, source_id, event_type, minute, second, period,
                    team_id, player_id, related_player_id, x, y, outcome, xg, raw_json)
                   VALUES (?, ?, ?, 'Shot', ?, 0, ?, ?, ?, NULL, 82.0, 36.0, 'Saved', ?, ?)""",
                (
                    ev_id, m["match_id"], source_id, minute, "1H" if minute <= 45 else "2H",
                    team_id, player_id, xg, json.dumps({"synthetic": True, "kind": "shot"}),
                ),
            )
            event_count += 1

        for idx, (team_id, player_id, minute) in enumerate(m["cards"]):
            ev_id = f"{m['match_id']}:card:{idx}"
            con.execute(
                """INSERT OR REPLACE INTO match_events
                   (event_id, match_id, source_id, event_type, minute, second, period,
                    team_id, player_id, related_player_id, x, y, outcome, xg, raw_json)
                   VALUES (?, ?, ?, 'Card', ?, 0, ?, ?, ?, NULL, NULL, NULL, 'Yellow Card', NULL, ?)""",
                (
                    ev_id, m["match_id"], source_id, minute, "1H" if minute <= 45 else "2H",
                    team_id, player_id, json.dumps({"synthetic": True, "kind": "card"}),
                ),
            )
            event_count += 1

    con.commit()
    return {"source_id": source_id, "matches_added": len(MATCHES), "events_added": event_count, "lineups_added": lineup_count, "players": len(PLAYERS), "teams": len(TEAMS)}


def run(base_db: Path, demo_db: Path, pack_dir: Path, reports_dir: Path) -> dict:
    demo_db.parent.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    if demo_db.exists():
        demo_db.unlink()
    shutil.copy2(base_db, demo_db)

    con = connect(demo_db)
    register_default_sources(con)
    inserted = insert_demo(con)
    counts_after_insert = table_counts(con)
    con.close()

    gold = build_gold(demo_db, rolling_n=10, reset=True)
    timing = analyze_goal_timing(demo_db)
    player = build_player_scores(demo_db)

    pack = export_pack(demo_db, pack_dir, DEFAULT_TABLES, sport="football", pack_name="football_event_demo_v1")

    con = connect(demo_db)
    counts_final = table_counts(con)
    con.close()

    report = {
        "ok": True,
        "warning": "Synthetic/public-safe event demo only. Not predictive real-world data.",
        "base_db": str(base_db),
        "demo_db": str(demo_db),
        "pack_dir": str(pack_dir),
        "inserted": inserted,
        "counts_after_insert": counts_after_insert,
        "gold": gold,
        "goal_timing": timing,
        "player_score": player,
        "pack_summary": {
            "pack_name": pack["pack_name"],
            "total_rows": pack["total_rows"],
            "total_compressed_bytes": pack["total_compressed_bytes"],
            "overall_compression_ratio": pack["overall_compression_ratio"],
        },
        "counts_final": counts_final,
    }
    (reports_dir / "v13_synthetic_event_pipeline.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main():
    ap = argparse.ArgumentParser(description="Create v13 synthetic event demo DB and pack.")
    ap.add_argument("--base-db", default="../build/omnibet.sqlite")
    ap.add_argument("--demo-db", default="../build/omnibet_v13_event_demo.sqlite")
    ap.add_argument("--pack-dir", default="../data_packs/football_event_demo_v1")
    ap.add_argument("--reports-dir", default="../reports")
    args = ap.parse_args()
    out = run(Path(args.base_db), Path(args.demo_db), Path(args.pack_dir), Path(args.reports_dir))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
