#!/usr/bin/env python3
"""v41 offline paper evaluation over settled mapped markets.

This consumes v39 feature snapshots and evaluates post-event settlement rows that
are already marked settled. It does not create a model-quality claim and does not
make staking recommendations.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect, sha_text
from feature_snapshot_smoke import build_report as build_feature_report

EVAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS offline_paper_evaluations (
    paper_eval_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    mapped_market_id TEXT NOT NULL,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    implied_probability REAL,
    baseline_probability REAL,
    settlement_result TEXT NOT NULL,
    paper_unit_result REAL NOT NULL,
    evaluation_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_offline_paper_eval_event
    ON offline_paper_evaluations(canonical_event_id, mapped_market_id, settlement_result);
"""


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def baseline_probability(mapped_market_id: str | None, raw_selection_name: str | None) -> float:
    if mapped_market_id == "football_1x2_regulation":
        return 1.0 / 3.0
    if mapped_market_id == "football_asian_handicap_regulation":
        return 0.5
    if mapped_market_id and ("total" in mapped_market_id or "corners" in mapped_market_id or "shots_on_target" in mapped_market_id):
        return 0.5
    return 0.5


def paper_unit_result(settlement_result: str, decimal_odds: Any) -> float:
    odds = float(decimal_odds or 0)
    if settlement_result == "win":
        return round(odds - 1.0, 6)
    if settlement_result == "loss":
        return -1.0
    if settlement_result == "push":
        return 0.0
    return 0.0


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    feature_report = build_feature_report(db, odds_input, state_input, link_input)
    canonical_event_id = feature_report["canonical_event_id"]
    con = connect(db)
    try:
        con.executescript(EVAL_SCHEMA)
        con.execute("DELETE FROM offline_paper_evaluations WHERE canonical_event_id=?", (canonical_event_id,))
        candidates = rows(
            con,
            """
            SELECT * FROM market_feature_snapshots
            WHERE canonical_event_id=? AND snapshot_stage='post_event_evaluation'
            ORDER BY source_ref
            """,
            (canonical_event_id,),
        )
        inserted = 0
        skipped = []
        for row in candidates:
            if not row.get("mapped_market_id"):
                skipped.append({"source_ref": row["source_ref"], "reason": "unmapped market"})
                continue
            if row.get("settlement_status") != "settled":
                skipped.append({"source_ref": row["source_ref"], "reason": row.get("settlement_status") or "not settled"})
                continue
            if row.get("settlement_result") not in {"win", "loss", "push"}:
                skipped.append({"source_ref": row["source_ref"], "reason": "unsupported settlement result"})
                continue
            implied = row.get("implied_probability")
            base_prob = baseline_probability(row.get("mapped_market_id"), row.get("raw_selection_name"))
            unit_result = paper_unit_result(row["settlement_result"], row.get("decimal_odds"))
            raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
            con.execute(
                """INSERT OR REPLACE INTO offline_paper_evaluations
                   (paper_eval_id, canonical_event_id, source_ref, mapped_market_id, raw_market_name,
                    raw_selection_name, line_value, decimal_odds, implied_probability, baseline_probability,
                    settlement_result, paper_unit_result, evaluation_status, reason, payload_sha256, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"paper_eval:{canonical_event_id}:{row['source_ref']}",
                    canonical_event_id,
                    row["source_ref"],
                    row["mapped_market_id"],
                    row.get("raw_market_name"),
                    row.get("raw_selection_name"),
                    row.get("line_value"),
                    row.get("decimal_odds"),
                    implied,
                    base_prob,
                    row["settlement_result"],
                    unit_result,
                    "evaluated_offline",
                    "settled mapped market; one paper unit accounting only",
                    sha_text(raw),
                    raw,
                ),
            )
            inserted += 1
        con.commit()
        result_counts = rows(con, "SELECT settlement_result, COUNT(*) AS rows, ROUND(SUM(paper_unit_result), 6) AS paper_units FROM offline_paper_evaluations WHERE canonical_event_id=? GROUP BY settlement_result ORDER BY settlement_result", (canonical_event_id,))
        market_counts = rows(con, "SELECT mapped_market_id, COUNT(*) AS rows FROM offline_paper_evaluations WHERE canonical_event_id=? GROUP BY mapped_market_id ORDER BY mapped_market_id", (canonical_event_id,))
        total_units = float(con.execute("SELECT COALESCE(SUM(paper_unit_result), 0) FROM offline_paper_evaluations WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    result_map = {row["settlement_result"]: row["rows"] for row in result_counts}
    acceptance = {
        "feature_report_ok": bool(feature_report.get("ok")),
        "evaluated_rows_positive": inserted >= 10,
        "skipped_rows_positive": len(skipped) >= 1,
        "has_win_loss_push": result_map.get("win", 0) >= 1 and result_map.get("loss", 0) >= 1 and result_map.get("push", 0) >= 1,
        "market_counts_positive": len(market_counts) >= 4,
        "no_unmapped_evaluated": all(row.get("mapped_market_id") for row in market_counts),
        "no_network": True,
        "no_api_key": True,
        "no_model_quality_claim": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v41_offline_paper_evaluation_over_settled_markets",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "evaluated_rows": inserted,
        "skipped_rows": skipped,
        "result_counts": result_counts,
        "market_counts": market_counts,
        "paper_units_total": round(total_units, 6),
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "mapped_settled_markets_only": True,
            "no_staking_recommendation": True,
            "no_model_quality_claim": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v41 offline paper evaluation smoke.")
    ap.add_argument("--db", default="../build/omnibet_v41_offline_paper_eval.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v41_offline_paper_eval.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
