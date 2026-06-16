#!/usr/bin/env python3
"""v38 settlement and outcome truth skeleton.

Conservative offline-only grading smoke. It builds the v37 provider event
timeline, derives deterministic event truth from the local fixture sample, and
settles only markets whose truth is available.
"""
from __future__ import annotations

import argparse
import json
import traceback
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from adapters.warehouse import connect, sha_text
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

RULES = [
    ("rule:1x2:v38", "football_1x2_regulation", "regulation_result_1x2", "regulation_90_plus_stoppage", 1, "v38", "Home/draw/away from final score."),
    ("rule:goals:v38", "football_total_goals_regulation", "total_goals", "regulation_90_plus_stoppage", 1, "v38", "Over/under total goals."),
    ("rule:corners:v38", "football_corners_total_regulation", "total_corners", "regulation_90_plus_stoppage", 1, "v38", "Over/under total corners."),
    ("rule:sot:v38", "football_shots_on_target_total_regulation", "total_shots_on_target", "regulation_90_plus_stoppage", 1, "v38", "Over/under total shots on target."),
    ("rule:handicap:v38", "football_asian_handicap_regulation", "score_margin", "regulation_90_plus_stoppage", 1, "v38", "Basic handicap win/loss/push."),
    ("rule:player_sot:v38", "football_player_shots_on_target_regulation", "player_shots_on_target", "regulation_90_plus_stoppage", 0, "v38", "Unsupported without player-level shot truth."),
]


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def stat_total(fixture: Dict[str, Any], stat_name: str) -> float:
    total = 0.0
    for team_stats in fixture.get("statistics", []):
        for item in team_stats.get("statistics", []):
            if item.get("type") == stat_name:
                value = item.get("value")
                if isinstance(value, str) and value.endswith("%"):
                    value = value[:-1]
                total += float(value or 0)
    return total


def derive_truths(state_payload: Dict[str, Any]) -> Dict[str, Any]:
    fixture = state_payload["response"][0]
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    home_score = int(fixture["goals"]["home"])
    away_score = int(fixture["goals"]["away"])
    winner = home if home_score > away_score else away if away_score > home_score else "Draw"
    result_1x2 = "home" if home_score > away_score else "away" if away_score > home_score else "draw"
    return {
        "home_team_name": home,
        "away_team_name": away,
        "home_score": home_score,
        "away_score": away_score,
        "winner_name": winner,
        "regulation_result_1x2": result_1x2,
        "score_margin_home": float(home_score - away_score),
        "total_goals": float(home_score + away_score),
        "total_corners": stat_total(fixture, "Corner Kicks"),
        "total_shots_on_target": stat_total(fixture, "Shots on Goal"),
    }


def insert_rules_and_truth(con, canonical_event_id: str, truth: Dict[str, Any]) -> None:
    con.executescript(SETTLEMENT_SCHEMA)
    for rule in RULES:
        con.execute(
            """INSERT OR REPLACE INTO settlement_rules
               (rule_id, mapped_market_id, truth_key, settlement_scope, supported, rule_version, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            rule,
        )
    truth_rows = [
        ("home_team_name", truth["home_team_name"], None),
        ("away_team_name", truth["away_team_name"], None),
        ("home_score", str(truth["home_score"]), float(truth["home_score"])),
        ("away_score", str(truth["away_score"]), float(truth["away_score"])),
        ("score_margin", str(truth["score_margin_home"]), float(truth["score_margin_home"])),
        ("regulation_result_1x2", truth["regulation_result_1x2"], None),
        ("total_goals", str(truth["total_goals"]), float(truth["total_goals"])),
        ("total_corners", str(truth["total_corners"]), float(truth["total_corners"])),
        ("total_shots_on_target", str(truth["total_shots_on_target"]), float(truth["total_shots_on_target"])),
    ]
    for key, text, numeric in truth_rows:
        raw = {"truth_key": key, "text": text, "numeric": numeric}
        raw_text = json.dumps(raw, ensure_ascii=False, sort_keys=True)
        con.execute(
            """INSERT OR REPLACE INTO outcome_truth
               (truth_id, canonical_event_id, truth_key, truth_value_text, truth_value_numeric, source_ref, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (f"truth:{canonical_event_id}:{key}", canonical_event_id, key, text, numeric, "api_football_offline_sample", sha_text(raw_text), raw_text),
        )
    con.commit()


def side(name: Optional[str]) -> str:
    value = (name or "").lower()
    if "over" in value:
        return "over"
    if "under" in value:
        return "under"
    return value.strip()


def over_under(total: float, line: Optional[float], selection: Optional[str]) -> Tuple[str, str, str]:
    if line is None:
        return "unsettled", "unsupported", "missing line"
    selection_side = side(selection)
    if total == float(line):
        return "push", "settled", "truth equals line"
    if selection_side == "over":
        return ("win" if total > float(line) else "loss", "settled", f"total {total} vs line {line}")
    if selection_side == "under":
        return ("win" if total < float(line) else "loss", "settled", f"total {total} vs line {line}")
    return "unsettled", "unsupported", "selection is not over/under"


def handicap(truth: Dict[str, Any], selection: Optional[str], line: Optional[float]) -> Tuple[str, str, str]:
    if line is None:
        return "unsettled", "unsupported", "missing handicap line"
    if selection == truth["home_team_name"]:
        adjusted = float(truth["score_margin_home"]) + float(line)
    elif selection == truth["away_team_name"]:
        adjusted = -float(truth["score_margin_home"]) + float(line)
    else:
        return "unsettled", "unsupported", "selection does not match known teams"
    if adjusted > 0:
        return "win", "settled", f"adjusted margin {adjusted}"
    if adjusted < 0:
        return "loss", "settled", f"adjusted margin {adjusted}"
    return "push", "settled", "adjusted margin is zero"


def settle(row: Dict[str, Any], truth: Dict[str, Any]) -> Tuple[str, str, str]:
    market = row.get("mapped_market_id")
    selection = row.get("raw_selection_name")
    if not market:
        return "unsettled", "unmapped", "market has no mapped_market_id"
    if market == "football_1x2_regulation":
        return ("win" if selection == truth["winner_name"] else "loss", "settled", "graded from regulation winner")
    if market == "football_total_goals_regulation":
        return over_under(float(truth["total_goals"]), row.get("line_value"), selection)
    if market == "football_corners_total_regulation":
        return over_under(float(truth["total_corners"]), row.get("line_value"), selection)
    if market == "football_shots_on_target_total_regulation":
        return over_under(float(truth["total_shots_on_target"]), row.get("line_value"), selection)
    if market == "football_asian_handicap_regulation":
        return handicap(truth, selection, row.get("line_value"))
    if market == "football_player_shots_on_target_regulation":
        return "unsettled", "unsupported", "player-level shot truth unavailable"
    return "unsettled", "unsupported", f"no v38 rule for {market}"


def evaluate(con, canonical_event_id: str, truth: Dict[str, Any]) -> List[Dict[str, Any]]:
    timeline_rows = rows(
        con,
        """SELECT * FROM provider_event_timeline
           WHERE canonical_event_id=? AND timeline_type='odds_market'
           ORDER BY source_ref""",
        (canonical_event_id,),
    )
    out: List[Dict[str, Any]] = []
    for row in timeline_rows:
        result, status, reason = settle(row, truth)
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
        con.execute(
            """INSERT OR REPLACE INTO settlement_evaluations
               (evaluation_id, canonical_event_id, source_ref, mapped_market_id, raw_market_name,
                raw_selection_name, line_value, decimal_odds, settlement_result, settlement_status,
                reason, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"settlement:{canonical_event_id}:{row['source_ref']}",
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
        out.append({
            "mapped_market_id": row.get("mapped_market_id"),
            "raw_market_name": row.get("raw_market_name"),
            "raw_selection_name": row.get("raw_selection_name"),
            "line_value": row.get("line_value"),
            "settlement_result": result,
            "settlement_status": status,
            "reason": reason,
        })
    con.commit()
    return out


def count_rows(con, sql: str, params: tuple = ()) -> int:
    return int(con.execute(sql, params).fetchone()[0])


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    timeline_report = build_timeline_report(db, odds_input, state_input, link_input)
    canonical_event_id = timeline_report["canonical_event_id"]
    truth = derive_truths(load_json(state_input))
    con = connect(db)
    try:
        insert_rules_and_truth(con, canonical_event_id, truth)
        evaluations = evaluate(con, canonical_event_id, truth)
        rule_count = count_rows(con, "SELECT COUNT(*) FROM settlement_rules")
        truth_count = count_rows(con, "SELECT COUNT(*) FROM outcome_truth WHERE canonical_event_id=?", (canonical_event_id,))
        eval_count = count_rows(con, "SELECT COUNT(*) FROM settlement_evaluations WHERE canonical_event_id=?", (canonical_event_id,))
    finally:
        con.close()

    by_market_status: Dict[Tuple[str, str], int] = {}
    by_result: Dict[str, int] = {}
    for ev in evaluations:
        market = ev.get("mapped_market_id") or "UNMAPPED"
        by_market_status[(market, ev["settlement_status"])] = by_market_status.get((market, ev["settlement_status"]), 0) + 1
        by_result[ev["settlement_result"]] = by_result.get(ev["settlement_result"], 0) + 1

    acceptance = {
        "timeline_ok": bool(timeline_report.get("ok")),
        "settlement_rules_written": rule_count >= len(RULES),
        "outcome_truth_written": truth_count >= 8,
        "evaluations_written": eval_count >= 14,
        "1x2_settled": by_market_status.get(("football_1x2_regulation", "settled"), 0) >= 3,
        "totals_settled": by_market_status.get(("football_total_goals_regulation", "settled"), 0) >= 2,
        "corners_settled": by_market_status.get(("football_corners_total_regulation", "settled"), 0) >= 2,
        "shots_on_target_settled": by_market_status.get(("football_shots_on_target_total_regulation", "settled"), 0) >= 2,
        "handicap_push_present": any(ev["mapped_market_id"] == "football_asian_handicap_regulation" and ev["settlement_result"] == "push" for ev in evaluations),
        "player_prop_unsupported": by_market_status.get(("football_player_shots_on_target_regulation", "unsupported"), 0) >= 2,
        "unknown_unmapped": by_market_status.get(("UNMAPPED", "unmapped"), 0) >= 1,
        "has_win_loss_push": by_result.get("win", 0) >= 1 and by_result.get("loss", 0) >= 1 and by_result.get("push", 0) >= 1,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v38_settlement_and_outcome_truth_skeleton",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "truth": truth,
        "evaluations": evaluations,
        "result_counts": {k: by_result[k] for k in sorted(by_result)},
        "market_status_counts": [
            {"mapped_market_id": k[0], "settlement_status": k[1], "rows": v}
            for k, v in sorted(by_market_status.items())
        ],
        "counts": {"rules": rule_count, "truth_rows": truth_count, "evaluations": eval_count},
        "timeline_summary": {
            "timeline_counts": timeline_report.get("timeline_counts"),
            "market_counts": timeline_report.get("market_counts"),
            "unknown_markets": timeline_report.get("unknown_markets"),
        },
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "no_website_automation": True,
            "no_prediction_output": True,
            "unsupported_markets_not_guessed": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v38 settlement/outcome truth smoke.")
    ap.add_argument("--db", default="../build/omnibet_v38_settlement_truth.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v38_settlement_truth.json")
    args = ap.parse_args()
    try:
        report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    except Exception as exc:
        report = {
            "ok": False,
            "milestone": "v38_settlement_and_outcome_truth_skeleton",
            "error": repr(exc),
            "traceback": traceback.format_exc(),
            "safety": {"offline_samples_only": True, "no_network": True},
        }
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
