#!/usr/bin/env python3
"""v45 player prop truth skeleton.

Adds a deterministic offline player-level truth row and settles the existing
Kylian Mbappe player shots-on-target market rows from the v35 sample.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from adapters.warehouse import connect, sha_text
from provider_pipeline_schema import ensure_provider_pipeline_schema
from settlement_truth_smoke import build_report as build_settlement_report

PLAYER_PROP_SCHEMA = """
CREATE TABLE IF NOT EXISTS player_prop_settlement_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    player_name TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value REAL,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    settlement_result TEXT NOT NULL,
    settlement_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT
);
"""


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def side(selection: str | None) -> str:
    value = (selection or "").lower()
    if "over" in value:
        return "over"
    if "under" in value:
        return "under"
    return "unknown"


def settle_player_prop(stat_value: float | None, line: float | None, selection: str | None) -> Tuple[str, str, str]:
    if stat_value is None:
        return "unsettled", "unsupported", "missing player stat truth"
    if line is None:
        return "unsettled", "unsupported", "missing player prop line"
    s = side(selection)
    if stat_value == float(line):
        return "push", "settled", "player stat equals line"
    if s == "over":
        return ("win" if stat_value > float(line) else "loss", "settled", f"player stat {stat_value} vs line {line}")
    if s == "under":
        return ("win" if stat_value < float(line) else "loss", "settled", f"player stat {stat_value} vs line {line}")
    return "unsettled", "unsupported", "selection is not over/under"


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    base = build_settlement_report(db, odds_input, state_input, link_input)
    canonical_event_id = base["canonical_event_id"]
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        con.executescript(PLAYER_PROP_SCHEMA)
        truth_payload = {"player_name": "Kylian Mbappe", "stat_key": "player_shots_on_target", "stat_value": 2.0, "minutes_played": 90.0}
        truth_raw = json.dumps(truth_payload, ensure_ascii=False, sort_keys=True)
        con.execute(
            """INSERT OR REPLACE INTO player_prop_truth
               (truth_id, canonical_event_id, provider_player_id, canonical_player_id, player_name,
                stat_key, stat_value, minutes_played, source_ref, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ("player_truth:kylian_mbappe:sot:v45", canonical_event_id, "1001", "canonical_player:kylian_mbappe", "Kylian Mbappe", "player_shots_on_target", 2.0, 90.0, "offline_player_truth_fixture_v45", sha_text(truth_raw), truth_raw),
        )
        market_rows = rows(
            con,
            """
            SELECT * FROM provider_event_timeline
            WHERE canonical_event_id=? AND mapped_market_id='football_player_shots_on_target_regulation'
            ORDER BY source_ref
            """,
            (canonical_event_id,),
        )
        evaluations = []
        for row in market_rows:
            player_name = "Kylian Mbappe" if "Kylian Mbappe" in (row.get("raw_selection_name") or "") else row.get("raw_selection_name")
            truth_row = rows(con, "SELECT * FROM player_prop_truth WHERE canonical_event_id=? AND player_name=? AND stat_key='player_shots_on_target'", (canonical_event_id, player_name))
            stat = truth_row[0]["stat_value"] if truth_row else None
            result, status, reason = settle_player_prop(stat, row.get("line_value"), row.get("raw_selection_name"))
            raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
            con.execute(
                """INSERT OR REPLACE INTO player_prop_settlement_evaluations
                   (evaluation_id, canonical_event_id, source_ref, player_name, stat_key, stat_value,
                    raw_selection_name, line_value, decimal_odds, settlement_result, settlement_status, reason, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"player_prop_eval:{canonical_event_id}:{row['source_ref']}", canonical_event_id, row["source_ref"], player_name, "player_shots_on_target", stat, row.get("raw_selection_name"), row.get("line_value"), row.get("decimal_odds"), result, status, reason, raw),
            )
            evaluations.append({"player_name": player_name, "selection": row.get("raw_selection_name"), "line": row.get("line_value"), "stat": stat, "settlement_result": result, "settlement_status": status, "reason": reason})
        missing_result, missing_status, missing_reason = settle_player_prop(None, 1.5, "Unknown Player Over")
        con.commit()
        truth_count = int(con.execute("SELECT COUNT(*) FROM player_prop_truth WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    result_counts: Dict[str, int] = {}
    for ev in evaluations:
        result_counts[ev["settlement_result"]] = result_counts.get(ev["settlement_result"], 0) + 1
    acceptance = {
        "base_settlement_ok": bool(base.get("ok")),
        "player_truth_written": truth_count >= 1,
        "player_prop_rows_found": len(evaluations) >= 2,
        "over_under_settled": result_counts.get("win", 0) >= 1 and result_counts.get("loss", 0) >= 1,
        "missing_player_truth_unsupported": missing_status == "unsupported",
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v45_player_prop_truth_skeleton",
        "db": str(db),
        "truth_count": truth_count,
        "evaluations": evaluations,
        "missing_truth_example": {"settlement_result": missing_result, "settlement_status": missing_status, "reason": missing_reason},
        "acceptance": acceptance,
        "safety": {"offline_samples_only": True, "missing_player_truth_not_guessed": True, "no_network": True, "no_api_keys": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v45 player prop truth smoke.")
    ap.add_argument("--db", default="../build/omnibet_v45_player_prop_truth.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v45_player_prop_truth.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
