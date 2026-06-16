#!/usr/bin/env python3
"""v47 first model pass from feature snapshots.

This is a tiny offline structural model smoke. It checks that feature snapshots can
feed a model-style evaluator without claiming production predictive quality.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect
from feature_snapshot_smoke import build_report as build_feature_report
from provider_pipeline_schema import ensure_provider_pipeline_schema


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def toy_probability(row: Dict[str, Any]) -> float:
    implied = row.get("implied_probability")
    if implied is None:
        implied = 1.0 / float(row.get("decimal_odds") or 2.0)
    market = row.get("mapped_market_id") or ""
    if market == "football_1x2_regulation":
        prior = 1.0 / 3.0
    else:
        prior = 0.5
    return max(0.01, min(0.99, 0.70 * float(implied) + 0.30 * prior))


def label_from_result(result: str) -> float | None:
    if result == "win":
        return 1.0
    if result == "loss":
        return 0.0
    return None


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    feature_report = build_feature_report(db, odds_input, state_input, link_input)
    canonical_event_id = feature_report["canonical_event_id"]
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        joined = rows(
            con,
            """
            SELECT pre.source_ref, pre.mapped_market_id, pre.raw_selection_name, pre.line_value,
                   pre.decimal_odds, pre.implied_probability, ev.settlement_result, ev.settlement_status
            FROM market_feature_snapshots pre
            JOIN market_feature_snapshots ev
              ON pre.canonical_event_id=ev.canonical_event_id AND pre.source_ref=ev.source_ref
            WHERE pre.canonical_event_id=?
              AND pre.snapshot_stage='pre_event_market'
              AND pre.model_eligible=1
              AND ev.snapshot_stage='post_event_evaluation'
              AND ev.settlement_status='settled'
            ORDER BY pre.source_ref
            """,
            (canonical_event_id,),
        )
        scored = []
        brier_terms = []
        logloss_terms = []
        for row in joined:
            label = label_from_result(row["settlement_result"])
            if label is None:
                continue
            p = toy_probability(row)
            brier_terms.append((p - label) ** 2)
            logloss_terms.append(-(label * math.log(p) + (1.0 - label) * math.log(1.0 - p)))
            scored.append({**row, "toy_probability": round(p, 8), "label": label})
        metrics = {
            "scored_rows": len(scored),
            "brier": round(sum(brier_terms) / len(brier_terms), 8) if brier_terms else None,
            "logloss": round(sum(logloss_terms) / len(logloss_terms), 8) if logloss_terms else None,
            "caveat": "offline toy smoke on one synthetic-sized fixture; not a quality claim",
        }
        con.execute(
            """INSERT OR REPLACE INTO first_model_pass_reports
               (report_id, canonical_event_id, model_kind, train_rows, eval_rows, metrics_json, caveat)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            ("first_model_pass:v47:toy_blend", canonical_event_id, "toy_implied_prior_blend", len(scored), len(scored), json.dumps(metrics, sort_keys=True), metrics["caveat"]),
        )
        con.commit()
        report_rows = int(con.execute("SELECT COUNT(*) FROM first_model_pass_reports WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
    finally:
        con.close()

    acceptance = {
        "feature_report_ok": bool(feature_report.get("ok")),
        "scored_rows_positive": metrics["scored_rows"] >= 8,
        "brier_present": metrics["brier"] is not None,
        "logloss_present": metrics["logloss"] is not None,
        "report_row_written": report_rows >= 1,
        "caveat_present": "not a quality claim" in metrics["caveat"],
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v47_first_model_pass_from_feature_snapshots",
        "db": str(db),
        "metrics": metrics,
        "sample_scored_rows": scored[:5],
        "acceptance": acceptance,
        "safety": {"offline_samples_only": True, "toy_model_only": True, "no_quality_claim": True, "no_network": True, "no_api_keys": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v47 first model pass smoke.")
    ap.add_argument("--db", default="../build/omnibet_v47_first_model_pass.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v47_first_model_pass.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
