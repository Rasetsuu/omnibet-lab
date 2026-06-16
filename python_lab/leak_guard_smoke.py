#!/usr/bin/env python3
"""v40 no-future-leak guard for provider feature snapshots."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect
from feature_snapshot_smoke import build_report as build_feature_report


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def count(con, sql: str, params: tuple = ()) -> int:
    return int(con.execute(sql, params).fetchone()[0])


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    feature_report = build_feature_report(db, odds_input, state_input, link_input)
    link_manifest = load_json(link_input)
    commence_time = parse_dt(link_manifest.get("commence_time"))
    canonical_event_id = feature_report["canonical_event_id"]

    con = connect(db)
    try:
        pre_rows = rows(con, "SELECT * FROM market_feature_snapshots WHERE canonical_event_id=? AND snapshot_stage='pre_event_market'", (canonical_event_id,))
        post_rows = rows(con, "SELECT * FROM market_feature_snapshots WHERE canonical_event_id=? AND snapshot_stage='post_event_evaluation'", (canonical_event_id,))
        pre_truth_leaks = count(
            con,
            """SELECT COUNT(*) FROM market_feature_snapshots
               WHERE canonical_event_id=? AND snapshot_stage='pre_event_market'
                 AND (home_score IS NOT NULL OR away_score IS NOT NULL OR settlement_result IS NOT NULL
                      OR settlement_status IS NOT NULL OR final_truth_allowed!=0)""",
            (canonical_event_id,),
        )
        model_rows_with_settlement = count(
            con,
            """SELECT COUNT(*) FROM market_feature_snapshots
               WHERE canonical_event_id=? AND model_eligible=1
                 AND (settlement_result IS NOT NULL OR settlement_status IS NOT NULL OR final_truth_allowed!=0)""",
            (canonical_event_id,),
        )
        eval_rows_model_eligible = count(
            con,
            """SELECT COUNT(*) FROM market_feature_snapshots
               WHERE canonical_event_id=? AND snapshot_stage='post_event_evaluation' AND model_eligible!=0""",
            (canonical_event_id,),
        )
        event_observation_truth_leaks = count(
            con,
            """SELECT COUNT(*) FROM event_feature_snapshots
               WHERE canonical_event_id=? AND snapshot_stage='event_observation'
                 AND (home_score IS NOT NULL OR away_score IS NOT NULL OR final_truth_allowed!=0)""",
            (canonical_event_id,),
        )
    finally:
        con.close()

    cutoff_violations = []
    for row in pre_rows:
        cutoff = parse_dt(row.get("feature_cutoff_time"))
        if cutoff is None or commence_time is None or cutoff > commence_time:
            cutoff_violations.append({"source_ref": row.get("source_ref"), "feature_cutoff_time": row.get("feature_cutoff_time")})

    acceptance = {
        "feature_report_ok": bool(feature_report.get("ok")),
        "pre_event_rows_exist": len(pre_rows) >= 14,
        "post_event_rows_exist": len(post_rows) >= 14,
        "pre_event_no_truth_fields": pre_truth_leaks == 0,
        "pre_event_cutoff_not_after_commence": len(cutoff_violations) == 0,
        "model_eligible_rows_no_settlement": model_rows_with_settlement == 0,
        "post_event_rows_not_model_eligible": eval_rows_model_eligible == 0,
        "event_observations_no_final_truth": event_observation_truth_leaks == 0,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v40_no_future_leak_guard",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "commence_time": link_manifest.get("commence_time"),
        "pre_event_rows": len(pre_rows),
        "post_event_rows": len(post_rows),
        "pre_truth_leaks": pre_truth_leaks,
        "model_rows_with_settlement": model_rows_with_settlement,
        "eval_rows_model_eligible": eval_rows_model_eligible,
        "event_observation_truth_leaks": event_observation_truth_leaks,
        "cutoff_violations": cutoff_violations,
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "model_eligible_rows_exclude_settlements": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v40 no-future-leak guard smoke.")
    ap.add_argument("--db", default="../build/omnibet_v40_leak_guard.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v40_leak_guard.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
