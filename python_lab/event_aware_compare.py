#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-40.0, min(40.0, x))))


def softmax3(h: float, d: float, a: float) -> Tuple[float, float, float]:
    m = max(h, d, a)
    eh, ed, ea = math.exp(h - m), math.exp(d - m), math.exp(a - m)
    s = eh + ed + ea
    return eh / s, ed / s, ea / s


def num(obj: Dict[str, Any], path: str, default: float = 0.0) -> float:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return default
        cur = cur[part]
    try:
        x = float(cur)
        return x if math.isfinite(x) else default
    except Exception:
        return default


def actual_outcome(hg: int, ag: int) -> str:
    if hg > ag:
        return "H"
    if hg < ag:
        return "A"
    return "D"


def log_loss(probs: Tuple[float, float, float], actual: str) -> float:
    idx = {"H": 0, "D": 1, "A": 2}[actual]
    return -math.log(max(1e-12, probs[idx]))


def brier(probs: Tuple[float, float, float], actual: str) -> float:
    target = [1.0 if actual == x else 0.0 for x in ["H", "D", "A"]]
    return sum((p - t) ** 2 for p, t in zip(probs, target))


def pick(probs: Tuple[float, float, float]) -> str:
    labels = ["H", "D", "A"]
    return labels[max(range(3), key=lambda i: probs[i])]


def match_only_probs(f: Dict[str, Any]) -> Tuple[float, float, float]:
    strength = 0.18
    strength += 0.38 * num(f, "features.goals_for_avg_diff")
    strength -= 0.26 * num(f, "features.goals_against_avg_diff")
    strength += 0.15 * num(f, "features.points_avg_diff")
    strength += 0.01 * max(-14.0, min(14.0, num(f, "features.rest_days_diff")))
    draw = -0.14 - 0.30 * abs(strength)
    return softmax3(strength, draw, -strength)


def event_aware_probs(f: Dict[str, Any]) -> Tuple[float, float, float]:
    strength = 0.18
    strength += 0.30 * num(f, "features.goals_for_avg_diff")
    strength -= 0.20 * num(f, "features.goals_against_avg_diff")
    strength += 0.12 * num(f, "features.points_avg_diff")
    strength += 0.34 * num(f, "features.xg_for_avg_diff")
    strength -= 0.26 * num(f, "features.xg_against_avg_diff")
    strength += 0.012 * num(f, "features.shots_for_avg_diff")
    strength -= 0.008 * num(f, "features.shots_against_avg_diff")
    strength -= 0.035 * num(f, "features.cards_for_avg_diff")
    strength += 0.020 * num(f, "features.cards_against_avg_diff")
    strength += 0.01 * max(-14.0, min(14.0, num(f, "features.rest_days_diff")))
    draw = -0.14 - 0.30 * abs(strength)
    return softmax3(strength, draw, -strength)


def has_event_history(f: Dict[str, Any]) -> bool:
    keys = [
        "features.xg_for_avg_diff",
        "features.xg_against_avg_diff",
        "features.shots_for_avg_diff",
        "features.shots_against_avg_diff",
        "features.cards_for_avg_diff",
        "features.cards_against_avg_diff",
    ]
    return any(abs(num(f, k, 0.0)) > 1e-9 for k in keys)


def summarize(rows: List[dict], key: str) -> Dict[str, Any]:
    n = len(rows)
    if not rows:
        return {"rows": 0, "accuracy": None, "log_loss": None, "brier": None}
    return {
        "rows": n,
        "accuracy": sum(1 for r in rows if r[f"{key}_pick"] == r["actual"]) / n,
        "log_loss": sum(r[f"{key}_log_loss"] for r in rows) / n,
        "brier": sum(r[f"{key}_brier"] for r in rows) / n,
    }


def compare(db_path: Path, require_event_rows: int = 1) -> dict:
    con = sqlite3.connect(str(db_path))
    rows = con.execute(
        """SELECT match_id, match_date, home_team_name, away_team_name,
                  target_home_goals, target_away_goals, features_json
           FROM gold_match_features
           WHERE target_home_goals IS NOT NULL AND target_away_goals IS NOT NULL
           ORDER BY match_date, match_id"""
    ).fetchall()
    event_count = con.execute("SELECT COUNT(*) FROM match_events").fetchone()[0]
    lineup_count = con.execute("SELECT COUNT(*) FROM lineups").fetchone()[0]
    player_count = con.execute("SELECT COUNT(*) FROM players").fetchone()[0]
    con.close()

    evaluated = []
    eligible = []
    for mid, date, home, away, hg, ag, feature_json in rows:
        f = json.loads(feature_json)
        actual = actual_outcome(int(hg), int(ag))
        mp = match_only_probs(f)
        ep = event_aware_probs(f)
        rec = {
            "match_id": mid,
            "match_date": date,
            "home": home,
            "away": away,
            "score": [hg, ag],
            "actual": actual,
            "has_event_history": has_event_history(f),
            "match_only_pick": pick(mp),
            "match_only_log_loss": log_loss(mp, actual),
            "match_only_brier": brier(mp, actual),
            "event_aware_pick": pick(ep),
            "event_aware_log_loss": log_loss(ep, actual),
            "event_aware_brier": brier(ep, actual),
            "event_signal": {
                "xg_for_avg_diff": num(f, "features.xg_for_avg_diff"),
                "xg_against_avg_diff": num(f, "features.xg_against_avg_diff"),
                "shots_for_avg_diff": num(f, "features.shots_for_avg_diff"),
                "shots_against_avg_diff": num(f, "features.shots_against_avg_diff"),
                "cards_for_avg_diff": num(f, "features.cards_for_avg_diff"),
            },
        }
        evaluated.append(rec)
        if rec["has_event_history"]:
            eligible.append(rec)

    match_summary = summarize(eligible, "match_only")
    event_summary = summarize(eligible, "event_aware")
    delta = None
    if match_summary["log_loss"] is not None and event_summary["log_loss"] is not None:
        delta = event_summary["log_loss"] - match_summary["log_loss"]

    report = {
        "ok": len(eligible) >= require_event_rows,
        "warning": "Tiny public sample comparison. Do not treat as model proof; it validates event-aware evaluation plumbing.",
        "db": str(db_path),
        "warehouse_counts": {"match_events": event_count, "lineups": lineup_count, "players": player_count},
        "gold_rows": len(rows),
        "event_history_rows": len(eligible),
        "require_event_rows": require_event_rows,
        "match_only_on_event_rows": match_summary,
        "event_aware_on_event_rows": event_summary,
        "event_minus_match_log_loss": delta,
        "samples": eligible[:8],
    }
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Compare match-only vs event-aware heuristics on gold features.")
    ap.add_argument("--db", default="../build/omnibet_v14_statsbomb_sample.sqlite")
    ap.add_argument("--out", default="../reports/v15_event_aware_compare.json")
    ap.add_argument("--require-event-rows", type=int, default=1)
    args = ap.parse_args()
    out = compare(Path(args.db), require_event_rows=args.require_event_rows)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps(out, indent=2))
    if not out["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
