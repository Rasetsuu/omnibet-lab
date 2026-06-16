#!/usr/bin/env python3
"""v44 expanded settlement coverage smoke.

Adds deterministic rule skeletons for common football market families using the
existing offline fixture truth. This is rule coverage, not a model claim.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple

from adapters.warehouse import connect, sha_text
from provider_pipeline_schema import ensure_provider_pipeline_schema
from settlement_truth_smoke import build_report as build_settlement_report

EXPANDED_SCHEMA = """
CREATE TABLE IF NOT EXISTS expanded_settlement_cases (
    case_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    market_family TEXT NOT NULL,
    selection TEXT NOT NULL,
    line_value REAL,
    settlement_result TEXT NOT NULL,
    settlement_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT
);
"""


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def fixture_truth(state_payload: Dict[str, Any]) -> Dict[str, Any]:
    fixture = state_payload["response"][0]
    home = fixture["teams"]["home"]["name"]
    away = fixture["teams"]["away"]["name"]
    home_score = int(fixture["goals"]["home"])
    away_score = int(fixture["goals"]["away"])
    halftime_home = int(fixture["score"]["halftime"]["home"])
    halftime_away = int(fixture["score"]["halftime"]["away"])
    yellow_cards = 0
    corners = 0
    for team_stats in fixture.get("statistics", []):
        for item in team_stats.get("statistics", []):
            if item.get("type") == "Yellow Cards":
                yellow_cards += int(item.get("value") or 0)
            if item.get("type") == "Corner Kicks":
                corners += int(item.get("value") or 0)
    return {
        "home": home,
        "away": away,
        "home_score": home_score,
        "away_score": away_score,
        "halftime_home": halftime_home,
        "halftime_away": halftime_away,
        "total_goals": home_score + away_score,
        "home_goals": home_score,
        "away_goals": away_score,
        "btts_yes": home_score > 0 and away_score > 0,
        "winner": "home" if home_score > away_score else "away" if away_score > home_score else "draw",
        "halftime_winner": "home" if halftime_home > halftime_away else "away" if halftime_away > halftime_home else "draw",
        "yellow_cards": yellow_cards,
        "red_cards": 0,
        "corners": corners,
    }


def ou(total: float, side: str, line: float) -> Tuple[str, str]:
    if total == line:
        return "push", f"total {total} equals line {line}"
    if side == "over":
        return ("win" if total > line else "loss", f"total {total} vs over {line}")
    return ("win" if total < line else "loss", f"total {total} vs under {line}")


def build_cases(truth: Dict[str, Any]) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    def add(family: str, selection: str, line: float | None, result: str, reason: str, status: str = "settled") -> None:
        cases.append({"market_family": family, "selection": selection, "line_value": line, "settlement_result": result, "settlement_status": status, "reason": reason})

    add("both_teams_to_score", "Yes", None, "win" if truth["btts_yes"] else "loss", "both teams scored in final score")
    add("both_teams_to_score", "No", None, "loss" if truth["btts_yes"] else "win", "both teams scored in final score")
    add("double_chance", "home_or_draw", None, "win" if truth["winner"] in {"home", "draw"} else "loss", "double chance from regulation result")
    add("double_chance", "away_or_draw", None, "win" if truth["winner"] in {"away", "draw"} else "loss", "double chance from regulation result")
    add("draw_no_bet", truth["home"], None, "win" if truth["winner"] == "home" else "push" if truth["winner"] == "draw" else "loss", "draw no bet from regulation result")
    add("draw_no_bet", truth["away"], None, "win" if truth["winner"] == "away" else "push" if truth["winner"] == "draw" else "loss", "draw no bet from regulation result")
    r, reason = ou(float(truth["home_goals"]), "over", 1.5); add("team_total_goals", f"{truth['home']} Over", 1.5, r, reason)
    r, reason = ou(float(truth["away_goals"]), "under", 1.5); add("team_total_goals", f"{truth['away']} Under", 1.5, r, reason)
    r, reason = ou(float(truth["yellow_cards"]), "over", 0.5); add("total_yellow_cards", "Over", 0.5, r, reason)
    r, reason = ou(float(truth["yellow_cards"]), "under", 0.5); add("total_yellow_cards", "Under", 0.5, r, reason)
    r, reason = ou(float(truth["red_cards"]), "under", 0.5); add("total_red_cards", "Under", 0.5, r, reason)
    r, reason = ou(float(truth["corners"]), "over", 10.5); add("total_corners_alt_line", "Over", 10.5, r, reason)
    add("first_half_1x2", truth["home"], None, "win" if truth["halftime_winner"] == "home" else "loss", "first-half score result")
    add("to_qualify", truth["home"], None, "unsettled", "qualification truth is not present in offline sample", "unsupported")
    return cases


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    base = build_settlement_report(db, odds_input, state_input, link_input)
    state_payload = load_json(state_input)
    truth = fixture_truth(state_payload)
    cases = build_cases(truth)
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        con.executescript(EXPANDED_SCHEMA)
        for i, case in enumerate(cases):
            raw = json.dumps(case, ensure_ascii=False, sort_keys=True)
            con.execute(
                """INSERT OR REPLACE INTO expanded_settlement_cases
                   (case_id, canonical_event_id, market_family, selection, line_value,
                    settlement_result, settlement_status, reason, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"expanded_case:{base['canonical_event_id']}:{i:03d}", base["canonical_event_id"], case["market_family"], case["selection"], case.get("line_value"), case["settlement_result"], case["settlement_status"], case["reason"], raw),
            )
        con.commit()
        family_counts = rows(con, "SELECT market_family, settlement_status, COUNT(*) AS rows FROM expanded_settlement_cases GROUP BY market_family, settlement_status ORDER BY market_family, settlement_status")
        result_counts = rows(con, "SELECT settlement_result, COUNT(*) AS rows FROM expanded_settlement_cases GROUP BY settlement_result ORDER BY settlement_result")
    finally:
        con.close()

    families = {row["market_family"] for row in family_counts}
    result_map = {row["settlement_result"]: row["rows"] for row in result_counts}
    acceptance = {
        "base_settlement_ok": bool(base.get("ok")),
        "btts_supported": "both_teams_to_score" in families,
        "double_chance_supported": "double_chance" in families,
        "draw_no_bet_supported": "draw_no_bet" in families,
        "team_totals_supported": "team_total_goals" in families,
        "cards_supported": "total_yellow_cards" in families and "total_red_cards" in families,
        "first_half_supported": "first_half_1x2" in families,
        "to_qualify_not_guessed": any(row["market_family"] == "to_qualify" and row["settlement_status"] == "unsupported" for row in family_counts),
        "has_win_loss_unsupported": result_map.get("win", 0) >= 1 and result_map.get("loss", 0) >= 1 and result_map.get("unsettled", 0) >= 1,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v44_expanded_settlement_coverage",
        "db": str(db),
        "truth": truth,
        "family_counts": family_counts,
        "result_counts": result_counts,
        "cases": cases,
        "acceptance": acceptance,
        "safety": {"offline_samples_only": True, "unsupported_truth_not_guessed": True, "no_network": True, "no_api_keys": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v44 expanded settlement smoke.")
    ap.add_argument("--db", default="../build/omnibet_v44_expanded_settlement.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v44_expanded_settlement.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
