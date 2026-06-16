#!/usr/bin/env python3
"""v35 The Odds API offline adapter smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from adapters.the_odds_api_adapter import import_offline_event_markets
from adapters.warehouse import connect, table_counts


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(db: Path, input_path: Path) -> Dict[str, Any]:
    result = import_offline_event_markets(db, input_path)
    con = connect(db)
    try:
        counts = table_counts(con)
    finally:
        con.close()

    mapped_ids = {row["mapped_market_id"] for row in result["mapped_market_ids"]}
    unknown_names = {row["raw_market_name"] for row in result["unknown_market_queue"]}
    acceptance = {
        "events_seen": result["events_seen"] == 1,
        "bookmakers_seen": result["bookmakers_seen"] == 2,
        "raw_snapshots_inserted_positive": result["raw_snapshots_inserted"] >= 14,
        "h2h_maps_to_1x2": "football_1x2_regulation" in mapped_ids,
        "totals_maps": "football_total_goals_regulation" in mapped_ids,
        "corners_maps": "football_corners_total_regulation" in mapped_ids,
        "shots_on_target_maps_separately": "football_shots_on_target_total_regulation" in mapped_ids,
        "player_sot_maps_separately": "football_player_shots_on_target_regulation" in mapped_ids,
        "unknown_market_stays_unknown": "special combo unknown" in unknown_names,
        "resolver_decisions_written": counts.get("resolver_mapping_decisions", 0) >= 10,
        "no_provider_calls": result["safety"]["no_network"],
        "no_api_key": result["safety"]["no_api_key"],
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v35_the_odds_api_offline_event_market_adapter",
        "adapter_report": result,
        "counts": counts,
        "acceptance": acceptance,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v35 The Odds API offline adapter smoke.")
    ap.add_argument("--db", default="../build/omnibet_v35_the_odds_api_offline.sqlite")
    ap.add_argument("--input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--out", default="../reports/ci_v35_the_odds_api_offline.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
