#!/usr/bin/env python3
"""v49 dashboard data smoke.

Builds a compact offline dashboard payload from the already-tested v37-v41
pipeline. This is used by CI to verify the GUI-facing sections without requiring
Tauri to run in CI.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect
from offline_paper_eval_smoke import build_report as build_result_report

REQUIRED_SECTIONS = [
    "events",
    "market_snapshots",
    "unknown_market_queue",
    "feature_snapshot_preview",
    "settlement_report",
    "result_accounting_report",
]


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_dashboard_payload(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    result_report = build_result_report(db, odds_input, state_input, link_input)
    canonical_event_id = result_report["canonical_event_id"]
    con = connect(db)
    try:
        event_links = rows(
            con,
            """
            SELECT canonical_event_id, provider_id, provider_event_id, provider_match_id,
                   sport, competition, commence_time, home_team_name, away_team_name, confidence
            FROM provider_event_links
            WHERE canonical_event_id=?
            ORDER BY provider_id
            """,
            (canonical_event_id,),
        )
        match_state = rows(
            con,
            """
            SELECT match_status, home_score, away_score, observed_at
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='match_state'
            ORDER BY observed_at
            """,
            (canonical_event_id,),
        )
        market_snapshots = rows(
            con,
            """
            SELECT bookmaker, raw_market_name, raw_selection_name, mapped_market_id,
                   line_value, decimal_odds, needs_mapping
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='odds_market'
            ORDER BY bookmaker, raw_market_name, raw_selection_name
            LIMIT 12
            """,
            (canonical_event_id,),
        )
        unknowns = rows(
            con,
            """
            SELECT raw_market_name, raw_selection_name, bookmaker, decimal_odds
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='odds_market' AND needs_mapping=1
            ORDER BY raw_market_name, raw_selection_name
            """,
            (canonical_event_id,),
        )
        feature_counts = rows(
            con,
            """
            SELECT snapshot_stage, COUNT(*) AS rows,
                   SUM(CASE WHEN model_eligible=1 THEN 1 ELSE 0 END) AS model_eligible_rows
            FROM market_feature_snapshots
            WHERE canonical_event_id=?
            GROUP BY snapshot_stage
            ORDER BY snapshot_stage
            """,
            (canonical_event_id,),
        )
        feature_preview = rows(
            con,
            """
            SELECT snapshot_stage, mapped_market_id, raw_selection_name, line_value,
                   decimal_odds, implied_probability, model_eligible
            FROM market_feature_snapshots
            WHERE canonical_event_id=?
            ORDER BY snapshot_stage, source_ref
            LIMIT 8
            """,
            (canonical_event_id,),
        )
        settlement_counts = rows(
            con,
            """
            SELECT settlement_status, settlement_result, COUNT(*) AS rows
            FROM settlement_evaluations
            WHERE canonical_event_id=?
            GROUP BY settlement_status, settlement_result
            ORDER BY settlement_status, settlement_result
            """,
            (canonical_event_id,),
        )
        settlement_preview = rows(
            con,
            """
            SELECT mapped_market_id, raw_selection_name, line_value,
                   settlement_result, settlement_status, reason
            FROM settlement_evaluations
            WHERE canonical_event_id=?
            ORDER BY source_ref
            LIMIT 10
            """,
            (canonical_event_id,),
        )
        result_counts = rows(
            con,
            """
            SELECT settlement_result, COUNT(*) AS rows, ROUND(SUM(paper_unit_result), 6) AS paper_units
            FROM offline_paper_evaluations
            WHERE canonical_event_id=?
            GROUP BY settlement_result
            ORDER BY settlement_result
            """,
            (canonical_event_id,),
        )
        result_preview = rows(
            con,
            """
            SELECT mapped_market_id, raw_selection_name, decimal_odds,
                   implied_probability, baseline_probability, settlement_result, paper_unit_result
            FROM offline_paper_evaluations
            WHERE canonical_event_id=?
            ORDER BY source_ref
            LIMIT 10
            """,
            (canonical_event_id,),
        )
    finally:
        con.close()

    events = [
        {
            "canonical_event_id": canonical_event_id,
            "home_team_name": event_links[0]["home_team_name"] if event_links else None,
            "away_team_name": event_links[0]["away_team_name"] if event_links else None,
            "competition": event_links[0]["competition"] if event_links else None,
            "commence_time": event_links[0]["commence_time"] if event_links else None,
            "provider_links": event_links,
            "match_state": match_state,
        }
    ]
    return {
        "ok": True,
        "version": "omnibet.dashboard.v49",
        "mode": "offline_dashboard_preview",
        "source": "v49 dashboard_data_smoke.py",
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "no_recommendation_output": True,
        },
        "sections": {
            "events": events,
            "market_snapshots": market_snapshots,
            "unknown_market_queue": unknowns,
            "feature_snapshot_preview": {
                "counts": feature_counts,
                "rows": feature_preview,
            },
            "settlement_report": {
                "counts": settlement_counts,
                "rows": settlement_preview,
            },
            "result_accounting_report": {
                "counts": result_counts,
                "rows": result_preview,
                "note": "Offline accounting over mapped settled sample rows only; no recommendation output.",
            },
        },
        "upstream_reports": {
            "v41_result_report_ok": result_report.get("ok"),
            "evaluated_rows": result_report.get("evaluated_rows"),
            "skipped_rows": result_report.get("skipped_rows"),
        },
    }


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path, dashboard_out: Path, ui_path: Path) -> Dict[str, Any]:
    payload = build_dashboard_payload(db, odds_input, state_input, link_input)
    write_json(dashboard_out, payload)
    html = ui_path.read_text(encoding="utf-8") if ui_path.exists() else ""
    sections = payload["sections"]
    html_required_markers = [
        "dashboard-events",
        "dashboard-markets",
        "dashboard-unknowns",
        "dashboard-features",
        "dashboard-settlement",
        "dashboard-accounting",
    ]
    acceptance = {
        "dashboard_payload_ok": payload.get("ok") is True,
        "all_required_sections_present": all(section in sections for section in REQUIRED_SECTIONS),
        "event_rows_present": len(sections["events"]) >= 1,
        "market_rows_present": len(sections["market_snapshots"]) >= 10,
        "unknown_rows_present": len(sections["unknown_market_queue"]) >= 1,
        "feature_rows_present": len(sections["feature_snapshot_preview"]["rows"]) >= 5,
        "settlement_rows_present": len(sections["settlement_report"]["rows"]) >= 5,
        "accounting_rows_present": len(sections["result_accounting_report"]["rows"]) >= 5,
        "ui_file_exists": ui_path.exists(),
        "ui_contains_dashboard_markers": all(marker in html for marker in html_required_markers),
        "no_network": payload["safety"]["no_network"],
        "no_api_key": payload["safety"]["no_api_keys"],
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v49_gui_dashboard_skeleton",
        "db": str(db),
        "dashboard_out": str(dashboard_out),
        "ui_path": str(ui_path),
        "required_sections": REQUIRED_SECTIONS,
        "section_counts": {
            "events": len(sections["events"]),
            "market_snapshots": len(sections["market_snapshots"]),
            "unknown_market_queue": len(sections["unknown_market_queue"]),
            "feature_snapshot_preview": len(sections["feature_snapshot_preview"]["rows"]),
            "settlement_report": len(sections["settlement_report"]["rows"]),
            "result_accounting_report": len(sections["result_accounting_report"]["rows"]),
        },
        "acceptance": acceptance,
        "safety": payload["safety"],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v49 dashboard data smoke.")
    ap.add_argument("--db", default="../build/omnibet_v49_dashboard.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--dashboard-out", default="../build/v49_dashboard_data.json")
    ap.add_argument("--ui-path", default="../tauri-app/src/index.html")
    ap.add_argument("--out", default="../reports/ci_v49_dashboard_data.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input), Path(args.dashboard_out), Path(args.ui_path))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
