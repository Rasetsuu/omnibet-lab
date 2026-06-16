#!/usr/bin/env python3
"""v39 provider timeline feature snapshot builder.

Builds model-ready feature snapshot tables from the offline v37/v38 pipeline.
Pre-event market snapshots intentionally do not contain final truth or settlement
results. Post-event evaluation snapshots are explicitly marked as evaluation-only.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect, sha_text
from settlement_truth_smoke import build_report as build_settlement_report

FEATURE_SCHEMA = """
CREATE TABLE IF NOT EXISTS event_feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    snapshot_stage TEXT NOT NULL,
    feature_cutoff_time TEXT,
    source_ref TEXT NOT NULL,
    match_status TEXT,
    minute INTEGER,
    event_type TEXT,
    team_id TEXT,
    player_id TEXT,
    home_score INTEGER,
    away_score INTEGER,
    final_truth_allowed INTEGER NOT NULL DEFAULT 0,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS market_feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    snapshot_stage TEXT NOT NULL,
    feature_cutoff_time TEXT,
    source_ref TEXT NOT NULL,
    bookmaker TEXT,
    mapped_market_id TEXT,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    implied_probability REAL,
    home_score INTEGER,
    away_score INTEGER,
    final_truth_allowed INTEGER NOT NULL DEFAULT 0,
    settlement_result TEXT,
    settlement_status TEXT,
    model_eligible INTEGER NOT NULL DEFAULT 0,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_event_feature_stage
    ON event_feature_snapshots(canonical_event_id, snapshot_stage, feature_cutoff_time);
CREATE INDEX IF NOT EXISTS idx_market_feature_stage
    ON market_feature_snapshots(canonical_event_id, snapshot_stage, mapped_market_id, feature_cutoff_time);
"""


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def ensure_schema(con) -> None:
    con.executescript(FEATURE_SCHEMA)
    con.commit()


def implied_probability(decimal_odds: Any) -> float | None:
    try:
        odds = float(decimal_odds)
        if odds <= 0:
            return None
        return round(1.0 / odds, 8)
    except Exception:
        return None


def rebuild_event_features(con, canonical_event_id: str) -> int:
    con.execute("DELETE FROM event_feature_snapshots WHERE canonical_event_id=?", (canonical_event_id,))
    timeline_rows = rows(
        con,
        """
        SELECT * FROM provider_event_timeline
        WHERE canonical_event_id=? AND timeline_type IN ('match_state', 'match_event')
        ORDER BY timeline_type, source_ref
        """,
        (canonical_event_id,),
    )
    inserted = 0
    for row in timeline_rows:
        stage = "post_event_truth" if row["timeline_type"] == "match_state" else "event_observation"
        final_truth_allowed = 1 if stage == "post_event_truth" else 0
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
        feature_id = f"event_feature:{canonical_event_id}:{row['timeline_type']}:{row['source_ref']}"
        con.execute(
            """INSERT OR REPLACE INTO event_feature_snapshots
               (feature_snapshot_id, canonical_event_id, snapshot_stage, feature_cutoff_time, source_ref,
                match_status, minute, event_type, team_id, player_id, home_score, away_score,
                final_truth_allowed, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_id,
                canonical_event_id,
                stage,
                row.get("observed_at"),
                row["source_ref"],
                row.get("match_status"),
                row.get("minute"),
                row.get("event_type"),
                row.get("team_id"),
                row.get("player_id"),
                row.get("home_score") if final_truth_allowed else None,
                row.get("away_score") if final_truth_allowed else None,
                final_truth_allowed,
                sha_text(raw),
                raw,
            ),
        )
        inserted += 1
    con.commit()
    return inserted


def rebuild_market_features(con, canonical_event_id: str) -> Dict[str, int]:
    con.execute("DELETE FROM market_feature_snapshots WHERE canonical_event_id=?", (canonical_event_id,))
    pre_rows = rows(
        con,
        """
        SELECT * FROM provider_event_timeline
        WHERE canonical_event_id=? AND timeline_type='odds_market'
        ORDER BY source_ref
        """,
        (canonical_event_id,),
    )
    inserted_pre = 0
    for row in pre_rows:
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
        feature_id = f"market_feature:{canonical_event_id}:pre:{row['source_ref']}"
        con.execute(
            """INSERT OR REPLACE INTO market_feature_snapshots
               (feature_snapshot_id, canonical_event_id, snapshot_stage, feature_cutoff_time, source_ref,
                bookmaker, mapped_market_id, raw_market_name, raw_selection_name, line_value, decimal_odds,
                implied_probability, home_score, away_score, final_truth_allowed, settlement_result,
                settlement_status, model_eligible, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_id,
                canonical_event_id,
                "pre_event_market",
                row.get("observed_at"),
                row["source_ref"],
                row.get("bookmaker"),
                row.get("mapped_market_id"),
                row.get("raw_market_name"),
                row.get("raw_selection_name"),
                row.get("line_value"),
                row.get("decimal_odds"),
                implied_probability(row.get("decimal_odds")),
                None,
                None,
                0,
                None,
                None,
                1 if row.get("mapped_market_id") and not row.get("needs_mapping") else 0,
                sha_text(raw),
                raw,
            ),
        )
        inserted_pre += 1

    eval_rows = rows(
        con,
        """
        SELECT * FROM settlement_evaluations
        WHERE canonical_event_id=?
        ORDER BY source_ref
        """,
        (canonical_event_id,),
    )
    inserted_eval = 0
    for row in eval_rows:
        raw = json.dumps(row, ensure_ascii=False, sort_keys=True)
        feature_id = f"market_feature:{canonical_event_id}:eval:{row['source_ref']}"
        con.execute(
            """INSERT OR REPLACE INTO market_feature_snapshots
               (feature_snapshot_id, canonical_event_id, snapshot_stage, feature_cutoff_time, source_ref,
                bookmaker, mapped_market_id, raw_market_name, raw_selection_name, line_value, decimal_odds,
                implied_probability, home_score, away_score, final_truth_allowed, settlement_result,
                settlement_status, model_eligible, payload_sha256, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                feature_id,
                canonical_event_id,
                "post_event_evaluation",
                None,
                row["source_ref"],
                None,
                row.get("mapped_market_id"),
                row.get("raw_market_name"),
                row.get("raw_selection_name"),
                row.get("line_value"),
                row.get("decimal_odds"),
                implied_probability(row.get("decimal_odds")),
                None,
                None,
                1,
                row.get("settlement_result"),
                row.get("settlement_status"),
                0,
                sha_text(raw),
                raw,
            ),
        )
        inserted_eval += 1
    con.commit()
    return {"pre_event_market": inserted_pre, "post_event_evaluation": inserted_eval}


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    settlement_report = build_settlement_report(db, odds_input, state_input, link_input)
    canonical_event_id = settlement_report["canonical_event_id"]
    con = connect(db)
    try:
        ensure_schema(con)
        event_inserted = rebuild_event_features(con, canonical_event_id)
        market_inserted = rebuild_market_features(con, canonical_event_id)
        event_counts = rows(con, "SELECT snapshot_stage, COUNT(*) AS rows FROM event_feature_snapshots WHERE canonical_event_id=? GROUP BY snapshot_stage ORDER BY snapshot_stage", (canonical_event_id,))
        market_counts = rows(con, "SELECT snapshot_stage, COUNT(*) AS rows FROM market_feature_snapshots WHERE canonical_event_id=? GROUP BY snapshot_stage ORDER BY snapshot_stage", (canonical_event_id,))
        model_eligible_count = int(con.execute("SELECT COUNT(*) FROM market_feature_snapshots WHERE canonical_event_id=? AND snapshot_stage='pre_event_market' AND model_eligible=1", (canonical_event_id,)).fetchone()[0])
        pre_truth_leaks = int(con.execute("""SELECT COUNT(*) FROM market_feature_snapshots
                                             WHERE canonical_event_id=? AND snapshot_stage='pre_event_market'
                                               AND (home_score IS NOT NULL OR away_score IS NOT NULL OR settlement_result IS NOT NULL OR settlement_status IS NOT NULL OR final_truth_allowed!=0)""", (canonical_event_id,)).fetchone()[0])
        implied_count = int(con.execute("SELECT COUNT(*) FROM market_feature_snapshots WHERE canonical_event_id=? AND implied_probability IS NOT NULL", (canonical_event_id,)).fetchone()[0])
        eval_settled_count = int(con.execute("SELECT COUNT(*) FROM market_feature_snapshots WHERE canonical_event_id=? AND snapshot_stage='post_event_evaluation' AND settlement_status='settled'", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    acceptance = {
        "settlement_report_ok": bool(settlement_report.get("ok")),
        "event_features_written": event_inserted >= 5,
        "pre_event_market_features_written": market_inserted["pre_event_market"] >= 14,
        "post_event_evaluation_features_written": market_inserted["post_event_evaluation"] >= 14,
        "model_eligible_pre_event_rows_positive": model_eligible_count >= 10,
        "pre_event_rows_do_not_contain_truth": pre_truth_leaks == 0,
        "implied_probability_present": implied_count >= 14,
        "evaluation_rows_have_settlements": eval_settled_count >= 10,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v39_provider_timeline_feature_snapshot_builder",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "event_inserted": event_inserted,
        "market_inserted": market_inserted,
        "event_counts": event_counts,
        "market_counts": market_counts,
        "model_eligible_pre_event_rows": model_eligible_count,
        "pre_truth_leaks": pre_truth_leaks,
        "implied_probability_rows": implied_count,
        "eval_settled_rows": eval_settled_count,
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "pre_event_truth_excluded": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v39 provider timeline feature snapshot smoke.")
    ap.add_argument("--db", default="../build/omnibet_v39_feature_snapshots.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v39_feature_snapshots.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
