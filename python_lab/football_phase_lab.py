#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, Optional

PHASES = [
    "regulation_first_half",
    "regulation_first_half_stoppage",
    "regulation_second_half",
    "regulation_second_half_stoppage",
    "extra_time_first_half",
    "extra_time_first_half_stoppage",
    "extra_time_second_half",
    "extra_time_second_half_stoppage",
    "penalty_shootout",
    "unknown",
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS gold_match_phase_features (
    match_id TEXT PRIMARY KEY,
    regulation_event_count INTEGER NOT NULL,
    regulation_stoppage_event_count INTEGER NOT NULL,
    extra_time_event_count INTEGER NOT NULL,
    extra_time_stoppage_event_count INTEGER NOT NULL,
    penalty_shootout_event_count INTEGER NOT NULL,
    max_minute INTEGER,
    has_extra_time INTEGER NOT NULL,
    has_penalties INTEGER NOT NULL,
    phase_counts_json TEXT NOT NULL,
    settlement_scopes_json TEXT NOT NULL
);
"""


def norm_period(period: Any) -> str:
    p = str(period or "").strip().lower()
    aliases = {
        "1": "first_half",
        "first half": "first_half",
        "2": "second_half",
        "second half": "second_half",
        "3": "extra_time_first_half",
        "first period of extra time": "extra_time_first_half",
        "extra time first half": "extra_time_first_half",
        "4": "extra_time_second_half",
        "second period of extra time": "extra_time_second_half",
        "extra time second half": "extra_time_second_half",
        "5": "penalty_shootout",
        "penalty shootout": "penalty_shootout",
    }
    return aliases.get(p, p.replace(" ", "_"))


def classify_phase(minute: Optional[int], second: Optional[int], period: Any, event_type: str = "") -> str:
    m = int(minute or 0)
    p = norm_period(period)
    et = (event_type or "").lower()
    if "penalty shootout" in p or "penalty shootout" in et or p == "penalty_shootout":
        return "penalty_shootout"
    if p == "first_half":
        return "regulation_first_half_stoppage" if m >= 45 else "regulation_first_half"
    if p == "second_half":
        return "regulation_second_half_stoppage" if m >= 90 else "regulation_second_half"
    if p == "extra_time_first_half":
        return "extra_time_first_half_stoppage" if m >= 105 else "extra_time_first_half"
    if p == "extra_time_second_half":
        return "extra_time_second_half_stoppage" if m >= 120 else "extra_time_second_half"

    # Fallback when a source lacks period names but carries absolute minutes.
    if m < 45:
        return "regulation_first_half"
    if m < 90:
        return "regulation_second_half"
    if m < 105:
        return "extra_time_first_half"
    if m < 120:
        return "extra_time_second_half"
    if "penalty" in et and m >= 120:
        return "penalty_shootout"
    return "extra_time_second_half_stoppage" if m >= 120 else "unknown"


def settlement_scopes_from_counts(counts: Counter) -> Dict[str, bool]:
    has_reg = any(counts[p] for p in ["regulation_first_half", "regulation_first_half_stoppage", "regulation_second_half", "regulation_second_half_stoppage"])
    has_et = any(counts[p] for p in ["extra_time_first_half", "extra_time_first_half_stoppage", "extra_time_second_half", "extra_time_second_half_stoppage"])
    has_pen = counts["penalty_shootout"] > 0
    return {
        "regulation_time": has_reg,
        "extra_time_only": has_et,
        "after_extra_time": has_reg and has_et,
        "penalty_shootout": has_pen,
        "qualification": has_reg and (has_et or has_pen),
    }


def selftest() -> dict:
    cases = [
        (10, 0, "1", "Pass", "regulation_first_half"),
        (45, 30, "1", "Shot", "regulation_first_half_stoppage"),
        (89, 59, "2", "Pass", "regulation_second_half"),
        (90, 1, "2", "Shot", "regulation_second_half_stoppage"),
        (94, 0, "3", "Pass", "extra_time_first_half"),
        (105, 0, "3", "Shot", "extra_time_first_half_stoppage"),
        (110, 0, "4", "Pass", "extra_time_second_half"),
        (120, 0, "4", "Shot", "extra_time_second_half_stoppage"),
        (121, 0, "5", "Penalty Shootout", "penalty_shootout"),
    ]
    rows = []
    ok = True
    for minute, second, period, etype, expected in cases:
        got = classify_phase(minute, second, period, etype)
        rows.append({"minute": minute, "second": second, "period": period, "event_type": etype, "expected": expected, "got": got, "ok": got == expected})
        ok = ok and got == expected
    return {"ok": ok, "cases": rows}


def analyze(db_path: Path, out_path: Path) -> dict:
    st = selftest()
    con = sqlite3.connect(str(db_path))
    con.executescript(SCHEMA)
    con.execute("DELETE FROM gold_match_phase_features")

    per_match: Dict[str, Counter] = defaultdict(Counter)
    max_minute: Dict[str, int] = defaultdict(int)
    rows = con.execute("SELECT match_id, minute, second, period, event_type FROM match_events").fetchall()
    for match_id, minute, second, period, event_type in rows:
        phase = classify_phase(minute, second, period, event_type)
        per_match[match_id][phase] += 1
        if minute is not None:
            max_minute[match_id] = max(max_minute[match_id], int(minute))

    for match_id, counts in per_match.items():
        reg = counts["regulation_first_half"] + counts["regulation_first_half_stoppage"] + counts["regulation_second_half"] + counts["regulation_second_half_stoppage"]
        reg_stop = counts["regulation_first_half_stoppage"] + counts["regulation_second_half_stoppage"]
        et = counts["extra_time_first_half"] + counts["extra_time_first_half_stoppage"] + counts["extra_time_second_half"] + counts["extra_time_second_half_stoppage"]
        et_stop = counts["extra_time_first_half_stoppage"] + counts["extra_time_second_half_stoppage"]
        pen = counts["penalty_shootout"]
        full_counts = {p: int(counts[p]) for p in PHASES}
        scopes = settlement_scopes_from_counts(counts)
        con.execute(
            """INSERT OR REPLACE INTO gold_match_phase_features
               (match_id, regulation_event_count, regulation_stoppage_event_count,
                extra_time_event_count, extra_time_stoppage_event_count, penalty_shootout_event_count,
                max_minute, has_extra_time, has_penalties, phase_counts_json, settlement_scopes_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                match_id, reg, reg_stop, et, et_stop, pen, max_minute.get(match_id),
                1 if et > 0 else 0, 1 if pen > 0 else 0,
                json.dumps(full_counts, sort_keys=True), json.dumps(scopes, sort_keys=True),
            ),
        )
    con.commit()

    out_rows = con.execute("SELECT COUNT(*), COALESCE(SUM(has_extra_time),0), COALESCE(SUM(has_penalties),0), COALESCE(MAX(max_minute),0) FROM gold_match_phase_features").fetchone()
    con.close()

    report = {
        "ok": bool(st["ok"] and out_rows[0] > 0),
        "db": str(db_path),
        "selftest": st,
        "phase_feature_rows": int(out_rows[0]),
        "matches_with_extra_time": int(out_rows[1]),
        "matches_with_penalties": int(out_rows[2]),
        "max_minute_seen": int(out_rows[3] or 0),
        "note": "Extra-time and penalty examples may be zero in a league smoke dataset; selftest guarantees 105+/120+/penalty classification logic is active.",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Build football phase-aware features for regulation/extra-time/penalty scopes.")
    ap.add_argument("--db", default="../build/omnibet_v20_statsbomb_scale.sqlite")
    ap.add_argument("--out", default="../reports/ci_v21_phase_lab.json")
    args = ap.parse_args()
    analyze(Path(args.db), Path(args.out))


if __name__ == "__main__":
    main()
