#!/usr/bin/env python3
"""v36 API-Football offline adapter smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from adapters.api_football_adapter import import_offline_live_state
from adapters.warehouse import connect, table_counts


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(db: Path, input_path: Path) -> Dict[str, Any]:
    result = import_offline_live_state(db, input_path)
    con = connect(db)
    try:
        counts = table_counts(con)
    finally:
        con.close()

    db_counts = result["db_counts"]
    event_types = {row["event_type"] for row in result["imported_events"]}
    acceptance = {
        "fixture_imported": db_counts["matches_norm"] == 1,
        "teams_imported": db_counts["teams"] >= 2,
        "players_imported": db_counts["players"] >= 8,
        "lineups_imported": db_counts["lineups"] >= 8,
        "events_imported": db_counts["match_events"] >= 4,
        "goal_and_card_events_present": "Goal" in event_types and "Card" in event_types,
        "bronze_payload_preserved": db_counts["bronze_blobs"] >= 1,
        "statistics_summary_present": result["coverage"]["statistics_team_rows"] == 2,
        "no_provider_calls": result["safety"]["no_network"],
        "no_api_key": result["safety"]["no_api_key"],
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v36_api_football_offline_live_state_adapter",
        "adapter_report": result,
        "warehouse_counts": counts,
        "acceptance": acceptance,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v36 API-Football offline live-state adapter smoke.")
    ap.add_argument("--db", default="../build/omnibet_v36_api_football_offline.sqlite")
    ap.add_argument("--input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--out", default="../reports/ci_v36_api_football_offline.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
