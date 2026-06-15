#!/usr/bin/env python3
"""
OmniBet Lab v5 goal timing lab.

Analyzes gold_goal_timing_features and produces simple distributions:
- first goal minute buckets
- goal interval frequencies
- first half vs second half goals

Requires event data. With score-only data, this honestly reports insufficient data.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


BUCKETS = [
    ("goal_0_15", "0-15"),
    ("goal_16_30", "16-30"),
    ("goal_31_45", "31-45"),
    ("goal_46_60", "46-60"),
    ("goal_61_75", "61-75"),
    ("goal_76_90", "76-90"),
]


def analyze(db_path: Path) -> dict:
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        """SELECT first_goal_minute, first_goal_team, goal_0_15, goal_16_30, goal_31_45,
                  goal_46_60, goal_61_75, goal_76_90, first_half_goals, second_half_goals
           FROM gold_goal_timing_features"""
    ).fetchall()
    con.close()

    if not rows:
        return {
            "ok": False,
            "reason": "No gold_goal_timing_features rows. Import event data first, e.g. StatsBomb Open Data or TheStatsAPI events.",
            "matches": 0,
        }

    n = len(rows)
    first_goal_minutes = [r[0] for r in rows if r[0] is not None]
    first_goal_by_team = {}
    for r in rows:
        if r[1]:
            first_goal_by_team[r[1]] = first_goal_by_team.get(r[1], 0) + 1

    bucket_counts = {}
    for i, (_, label) in enumerate(BUCKETS, start=2):
        bucket_counts[label] = sum(int(r[i] or 0) for r in rows)

    fh = sum(int(r[8] or 0) for r in rows)
    sh = sum(int(r[9] or 0) for r in rows)

    return {
        "ok": True,
        "matches": n,
        "matches_with_first_goal": len(first_goal_minutes),
        "avg_first_goal_minute": (sum(first_goal_minutes) / len(first_goal_minutes)) if first_goal_minutes else None,
        "first_goal_by_team_side": first_goal_by_team,
        "goal_bucket_counts": bucket_counts,
        "first_half_goals": fh,
        "second_half_goals": sh,
        "second_half_goal_share": sh / (fh + sh) if (fh + sh) else None,
    }


def main():
    ap = argparse.ArgumentParser(description="Analyze goal timing features.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--out", default="../reports/v5_goal_timing_report.json")
    args = ap.parse_args()
    out = analyze(Path(args.db))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
