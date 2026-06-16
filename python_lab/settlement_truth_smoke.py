#!/usr/bin/env python3
"""v38 settlement and outcome truth skeleton.

This is deliberately conservative. It reuses the v37 offline provider event
timeline, derives deterministic truth from the offline API-Football-style sample,
and evaluates only mapped markets with available truth.

No live APIs, API keys, staking output, or model-quality claims are involved.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from adapters.warehouse import connect, sha_text, table_counts
from provider_event_timeline_smoke import build_report as build_timeline_report

SETTLEMENT_SCHEMA = """
CREATE TABLE IF NOT EXISTS settlement_rules (
    rule_id TEXT PRIMARY KEY,
    mapped_market_id TEXT NOT NULL,
    truth_key TEXT NOT NULL,
    settlement_scope TEXT NOT NULL,
    supported INTEGER NOT NULL,
    rule_version TEXT NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outcome_truth (
    truth_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    truth_key TEXT NOT NULL,
    truth_value_text TEXT,
    truth_value_numeric REAL,
    source_ref TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS settlement_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    mapped_market_id TEXT,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    settlement_result TEXT NOT NULL,
    settlement_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_settlement_eval_event_market
    ON settlement_evaluations(canonical_event_id, mapped_market_id, settlement_status);
CREATE INDEX IF NOT EXISTS idx_outcome_truth_event_key
    ON outcome_truth(canonical_event_id, truth_key);
"""

SUPPORTED_RULES = [
    ("rule:football_1x2_regulation:v38", "football_1x2_regulation", "regulation_result_1x2", "regulation_90_plus_stoppage", 1, "v38", "Home/draw/away from regulation full-time score."),
    ("rule:football_total_goals_regulation:v38", "football_total_goals_regulation", "total_goals", "regulation_90_plus_stoppage", 1, "v38", "Over/under total goals from full-time score."),
    ("rule:football_corners_total_regulation:v38", "football_corners_total_regulation", "total_corners", "regulation_90_plus_stoppage", 1, "v38", "Over/under total corners from team statistics."),
    ("rule:football_shots_on_target_total_regulation:v38", "football_shots_on_target_total_regulation", "total_shots_on_target", "regulation_90_plus_stoppage", 1, "v38", "Over/under total shots on target from team statistics."),
    ("rule:football_asian_handicap_regulation:v38", "football_asian_handicap_regulation", "score_margin", "regulation_90_plus_stoppage", 1, "v38", "Basic handicap win/loss/push skeleton from full-time score."),
    ("rule:football_player_shots_on_target_regulation:v38", "football_player_shots_on_target_regulation", "player_shots_on_target", "regulation_90_plus_stoppage", 0, "v38", "Unsupported until player-level shot-on-target truth is imported."),
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def ensure_schema(con) -> None:
    con.executescript(SETTLEMENT_SCHEMA)
    con.commit()


def seed_rules(con) -> None:
    for rule in SUPPORTED_RULES:
        con.execute(
            """INSERT OR REPLACE INTO settlement_rules
               (rule_id, mapped_market_id, truth_key, settlement_scope, supported, rule_version, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rule,
        )
    con.commit()


def stat_value(fixture_obj: Dict[str, Any], stat_name: str) -> float:
    total = 0.0
    for team_row in fixture_obj.get("statistics", []):
        for item in team_row.get("statistics", []):
            if item.get("type") == stat_name:
                value = item.get("value")
                if isinstance(value, str) and value.endswith("%"):
                    value = value[:-1]
                total += float(value or 0)
    return total


def derive_truths(state_payload: Dict[str, Any], canonical_event_id: str) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    fixture_obj = state_payload["response"][0]
    teams = fixture_obj["teams"]
    goals = fixture_obj["goals"]
    home_team = teams["home"]["name"]
    away_team = teams["away"]["name"]
    home_score = int(goals["home"])
    away_score = int(goals["away"])
    if home_score > away_score:
        result_1x2 = "home"
        winner_name = home_team
    elif home_score < away_score:
        result_1x2 = "away"
        winner_name = away_team
    else:
        result_1x2 = "draw"
        winner_name = "Draw"

    truth_map: Dict[str, Any] = {
        "home_team_name": home_team,
        "away_team_name": away_team,
        "home_score": home_score,
        "away_score": away_score,
        "score_margin_home": home_score - away_score,
        "regulation_result_1x2": result_1x2,
        "winner_name": winner_name,
        "total_goals": float(home_score + away_score),
        "total_corners": stat_value(fixture_obj, "Corner Kicks"),
        "total_shots_on_target": stat_value(fixture_obj, "Shots on Goal"),
    }

    truth_rows = [
        {"truth_key": "home_team_name", "text": home_team, "numeric": None},
        {"truth_key": "away_team_name", "text": away_team, "numeric": None},
        {"truth_key": "home_score", "text": str(home_score), "numeric": float(home_score)},
        {"truth_key": "away_score", "text": str(away_score), "numeric": float(away_score)},
        {"truth_key": "score_margin", "text": str(home_score - away_score), "numeric": float(home_score - away_score)},
        {"truth_key": "regulation_result_1x2", "text": result_1x2, "numeric": None},
        {"truth_key": "total_goals", "text": str(home_score + away_score), "numeric": float(home_score + away_score)},
        {"truth_key": "total_corners", "text": str(truth_map["total_corners"]), "numeric": float(truth_map["total_corners"])},
        {"truth_key": "total_shots_on_target", "text": str(truth_map["total_shots_on_target"]), "numeric": float(truth_map["total_shots_on_target"])},
    ]
    return truth_map, truth_rows


def insert_truth_rows(con, canonical_event_id: str, truth_rows: List[Dict[str, Any]], source_ref: str) -> None:
    for truth in truth_rows:
        raw = json.dumps(truth, ensure_ascii=False, sort_keys=True)
        truth_id = f"truth:{canonical_event_id}:{truth['truth_key']}"
        con.execute(
            """INSERT OR REPLACE INTO outcome_truth
               (truth_id, canonical_event_id, truth_key, truth_value_text, truth_value_numeric, source_ref, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                truth_id,
                canonical_event_id,
                truth["truth_key"],
                truth.get("text"),
                truth.get("numeric"),
                source_ref,
                sha_text(raw),
                raw,
            ),
        )
    con.commit()


def selection_side(raw_selection_name: Optional[str]) -> str:
    value = (raw_selection_name or "").lower()
    if "over" in value:
        return "over"
    if "under" in value:
        return "under"
    return value.strip()


def over_under_result(total: float, line: Optional[float], raw_selection_name: Optional[str]) -> Tuple[str, str, str]:
    if line is None:
        return "unsettled", "unsupported", "missing line for over/under market"
    side = selection_side(raw_selection_name)
    if total == float(line):
        return "push", "settled", "truth equals line"
    if side == "over":
        return ("win" if total > float(line) else "loss", "settled", f"total {total} vs line {line}")
    if side == "under":
        return ("win" if total < float(line) else "loss", "settled", f"total {total} vs line {line}")
    return "unsettled", "unsupported", "selection is not over/under"


def handicap_result(truth_map: Dict[str, Any], raw_selection_name: Optional[str], line: Optional[float]) -> Tuple[str, str, str]:
    if line is None:
        return "unsettled", "unsupported", "missing handicap line"
    selection = raw_selection_name or ""
    margin_home = float(truth_map["score_margin_home"])
    home = truth_map["home_team_name"]
    away = truth_map["away_team_name"]
    if selection == home:
        adjusted = margin_home + float(line)
    elif selection == away:
        adjusted = -margin_home + float(line)
    else:
        return "unsettled", "unsupported", "selection does not match home/away team"
    if adjusted > 0:
        return "win", "settled", f"adjusted handicap margin {adjusted}"
    if adjusted < 0:
        return "loss", "settled", f"adjusted handicap margin {adjusted}"
    return "push", "settled", "adjusted handicap margin is zero"


def evaluate_market_row(row: Dict[str, Any], truth_map: Dict[str, Any]) -> Tuple[str, str, str]:
    market_id = row.get("mapped_market_id")
    if not market_id:
        return "unsettled", "unmapped", "market has no mapped_market_id"
    if market_id == "football_1x2_regulation":
        selection = row.get("raw_selection_name")
        if selection == truth_map["winner_name"]:
            return "win", "settled", "selection matches regulation winner"
        return "loss", "settled", "selection does not match regulation winner"
    if market_id == "football_total_goals_regulation":
        return over_under_result(float(truth_map["total_goals"]), row.get("line_value"), row.get("raw_selection_name"))
    if market_id == "football_corners_total_regulation":
        return over_under_result(float(truth_map["total_corners"]), row.get("line_value"), row.get("raw_selection_name"))
    if market_id == "football_shots_on_target_total_regulation":
        return over_under_result(float(truth_map["total_shots_on_target"]), row.get("line_value"), row.get("raw_selection_name"))
    if market_id == "football_asian_handicap_regulation":
        return handicap_result(truth_map, row.get("raw_selection_name"), row.get("line_value"))
    if market_id == "football_player_shots_on_target_regulation":
        return "unsettled", "unsupported", "player-level shots on target truth is unavailable in v38 sample"
    return "unsettled", "unsupported", f"no v38 settlement rule for {market_id}"


def evaluate_settlements(con, canonical_event_id: str, truth_map: Dict[str, Any]) -> List[Dict[str, Any]]:
    odds_rows = rows(
        con,
        """
        SELECT * FROM provider_event_timeline
        WHERE canonical_event_id=? AND timeline_type='odds_market'
        ORDER BY source_ref
        """,
        (canonical_event_id,),
    )
    evaluations = []
    for row in odds_rows:
        result, status, reason = evaluate_market_row(row, truth_map)
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
        eval_id = f"settlement:{canonical_event_id}:{row['source_ref']}"
        con.execute(
            """INSERT OR REPLACE INTO settlement_evaluations
               (evaluation_id, canonical_event_id, source_ref, mapped_market_id, raw_market_name,
                raw_selection_name, line_value, decimal_odds, settlement_result, settlement_status,
                reason, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                eval_id,
                canonical_event_id,
                row["source_ref"],
                row.get("mapped_market_id"),
                row.get("raw_market_name"),
                row.get("raw_selection_name"),
                row.get("line_value"),
                row.get("decimal_odds"),
                result,
                status,
                reason,
                sha_text(raw),
                raw,
            ),
        )
        evaluations.append({
            "source_ref": row["source_ref"],
            "mapped_market_id": row.get("mapped_market_id"),
            "raw_market_name": row.get("raw_market_name"),
            "raw_selection_name": row.get("raw_selection_name"),
            "line_value": row.get("line_value"),
            "settlement_result": result,
            "settlement_status": status,
            "reason": reason,
        })
    con.commit()
    return evaluations


def grouped_counts(con, table: str, group_col: str) -> List[Dict[str, Any]]:
    return rows(con, f"SELECT {group_col} AS key, COUNT(*) AS rows FROM {table} GROUP BY {group_col} ORDER BY {group_col}")


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    timeline_report = build_timeline_report(db, odds_input, state_input, link_input)
    state_payload = load_json(state_input)
    canonical_event_id = timeline_report["canonical_event_id"]
    truth_map, truth_rows = derive_truths(state_payload, canonical_event_id)

    con = connect(db)
    try:
        ensure_schema(con)
        seed_rules(con)
        insert_truth_rows(con, canonical_event_id, truth_rows, "api_football_offline_sample")
        evaluations = evaluate_settlements(con, canonical_event_id, truth_map)
        counts = table_counts(con)
        settlement_result_counts = grouped_counts(con, "settlement_evaluations", "settlement_result")
        settlement_status_counts = grouped_counts(con, "settlement_evaluations", "settlement_status")
        market_status_counts = rows(
            con,
            """
            SELECT COALESCE(mapped_market_id, 'UNMAPPED') AS mapped_market_id,
                   settlement_status,
                   COUNT(*) AS rows
            FROM settlement_evaluations
            GROUP BY COALESCE(mapped_market_id, 'UNMAPPED'), settlement_status
            ORDER BY mapped_market_id, settlement_status
            """,
        )
        rule_count = int(con.execute("SELECT COUNT(*) FROM settlement_rules").fetchone()[0])
        truth_count = int(con.execute("SELECT COUNT(*) FROM outcome_truth WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
        eval_count = int(con.execute("SELECT COUNT(*) FROM settlement_evaluations WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    statuses_by_market = {(row["mapped_market_id"], row["settlement_status"]): row["rows"] for row in market_status_counts}
    results = {row["settlement_result"]: row["rows"] for row in settlement_result_counts}
    acceptance = {
        "timeline_ok": bool(timeline_report.get("ok")),
        "settlement_rules_written": rule_count >= len(SUPPORTED_RULES),
        "outcome_truth_written": truth_count >= 8,
        "evaluations_written": eval_count >= 14,
        "1x2_settled": statuses_by_market.get(("football_1x2_regulation", "settled"), 0) >= 3,
        "totals_settled": statuses_by_market.get(("football_total_goals_regulation", "settled"), 0) >= 2,
        "corners_settled": statuses_by_market.get(("football_corners_total_regulation", "settled"), 0) >= 2,
        "shots_on_target_settled": statuses_by_market.get(("football_shots_on_target_total_regulation", "settled"), 0) >= 2,
        "handicap_push_present": any(ev["mapped_market_id"] == "football_asian_handicap_regulation" and ev["settlement_result"] == "push" for ev in evaluations),
        "player_prop_unsupported": statuses_by_market.get(("football_player_shots_on_target_regulation", "unsupported"), 0) >= 2,
        "unknown_unmapped": statuses_by_market.get(("UNMAPPED", "unmapped"), 0) >= 1,
        "has_win_loss_push": results.get("win", 0) >= 1 and results.get("loss", 0) >= 1 and results.get("push", 0) >= 1,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v38_settlement_and_outcome_truth_skeleton",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "timeline_summary": {
            "timeline_counts": timeline_report.get("timeline_counts"),
            "market_counts": timeline_report.get("market_counts"),
            "unknown_markets": timeline_report.get("unknown_markets"),
        },
        "truth_map": truth_map,
        "truth_rows": truth_rows,
        "evaluations": evaluations,
        "settlement_result_counts": settlement_result_counts,
        "settlement_status_counts": settlement_status_counts,
        "market_status_counts": market_status_counts,
        "warehouse_counts": counts,
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "no_website_automation": True,
            "no_betting_output": True,
            "unsupported_markets_not_guessed": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v38 settlement/outcome truth smoke.")
    ap.add_argument("--db", default="../build/omnibet_v38_settlement_truth.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v38_settlement_truth.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
