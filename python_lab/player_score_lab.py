#!/usr/bin/env python3
"""
OmniBet Lab v5 player score lab.

Prototype player-score builder from lineups + events.

This is intentionally simple:
- counts prior events by player
- estimates goals/shots/xG/cards per 90 when minutes are known
- stores gold_player_snapshots when enough data exists

If player/event/minute data is missing, it reports insufficient data instead of
creating fake player scores.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from collections import defaultdict
from pathlib import Path


def build_player_scores(db_path: Path) -> dict:
    con = sqlite3.connect(str(db_path))
    # Ensure table exists via gold_feature_builder schema if it was run.
    con.execute(
        """CREATE TABLE IF NOT EXISTS gold_player_snapshots (
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
        )"""
    )

    lineup_rows = con.execute(
        "SELECT match_id, player_id, player_name, team_id, minutes_played FROM lineups WHERE player_id IS NOT NULL"
    ).fetchall()
    event_rows = con.execute(
        "SELECT match_id, player_id, event_type, outcome, xg FROM match_events WHERE player_id IS NOT NULL"
    ).fetchall()

    if not lineup_rows or not event_rows:
        con.close()
        return {
            "ok": False,
            "reason": "Not enough player lineup/event data. Import StatsBomb or TheStatsAPI lineups/events first.",
            "lineup_rows": len(lineup_rows),
            "event_rows": len(event_rows),
            "snapshots_written": 0,
        }

    minutes = defaultdict(float)
    names = {}
    teams = {}
    matches = defaultdict(set)
    for match_id, pid, name, tid, mins in lineup_rows:
        names[pid] = name
        teams[pid] = tid
        matches[pid].add(match_id)
        # If minutes missing, assume squad appearance placeholder 60.
        minutes[pid] += float(mins) if mins is not None else 60.0

    stats = defaultdict(lambda: {"shots": 0, "goals": 0, "xg": 0.0, "cards": 0})
    for match_id, pid, etype, outcome, xg in event_rows:
        et = (etype or "").lower()
        if "shot" in et:
            stats[pid]["shots"] += 1
            if (outcome or "").lower() == "goal":
                stats[pid]["goals"] += 1
            if xg is not None:
                stats[pid]["xg"] += float(xg)
        if "card" in et or "bad behaviour" in et:
            stats[pid]["cards"] += 1

    written = 0
    con.execute("DELETE FROM gold_player_snapshots")
    for pid, st in stats.items():
        mins = max(minutes.get(pid, 0.0), 1.0)
        goals90 = st["goals"] * 90.0 / mins
        shots90 = st["shots"] * 90.0 / mins
        xg90 = st["xg"] * 90.0 / mins
        cards90 = st["cards"] * 90.0 / mins
        # Simple interpretable score, capped lightly. Later this becomes position-specific.
        score = 50.0 + 18.0 * xg90 + 3.0 * shots90 + 12.0 * goals90 - 6.0 * cards90
        score = max(0.0, min(100.0, score))
        raw = {"minutes": mins, "stats": st, "matches": len(matches[pid])}
        con.execute(
            """INSERT OR REPLACE INTO gold_player_snapshots
               (snapshot_id, player_id, player_name, team_id, snapshot_date, prior_matches, expected_minutes,
                goals_90, shots_90, xg_90, cards_90, player_score, raw_json)
               VALUES (?, ?, ?, ?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"{pid}:v5_player_score", pid, names.get(pid), teams.get(pid), len(matches[pid]), mins / max(len(matches[pid]), 1),
                goals90, shots90, xg90, cards90, score, json.dumps(raw, ensure_ascii=False),
            ),
        )
        written += 1

    con.commit()
    con.close()
    return {"ok": True, "lineup_rows": len(lineup_rows), "event_rows": len(event_rows), "snapshots_written": written}


def main():
    ap = argparse.ArgumentParser(description="Build prototype player scores.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--out", default="../reports/v5_player_score_report.json")
    args = ap.parse_args()
    out = build_player_scores(Path(args.db))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
