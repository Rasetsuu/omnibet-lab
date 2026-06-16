#!/usr/bin/env python3
"""v32 CI-safe market snapshot warehouse smoke.

No provider calls. No scraping. Inserts deterministic sample raw markets into the
SQLite warehouse and reports coverage/unknown queue behavior.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect, register_default_sources, store_raw_market_snapshot, table_counts, utc_now


SAMPLE_SNAPSHOTS: List[Dict[str, Any]] = [
    {
        "provider_id": "the_odds_api",
        "bookmaker": "example_bookmaker",
        "provider_sport_key": "soccer_fifa_world_cup",
        "provider_event_id": "event_france_senegal_demo",
        "match_id": "demo_france_senegal",
        "raw_market_key": "h2h",
        "raw_market_name": "Head to Head",
        "raw_selection_key": "france",
        "raw_selection_name": "France",
        "decimal_odds": 1.50,
        "settlement_scope_guess": "regulation_90_plus_stoppage",
        "mapped_market_id": "football_1x2_regulation",
        "mapping_confidence": 0.99,
        "needs_mapping": False,
    },
    {
        "provider_id": "the_odds_api",
        "bookmaker": "example_bookmaker",
        "provider_sport_key": "soccer_fifa_world_cup",
        "provider_event_id": "event_france_senegal_demo",
        "match_id": "demo_france_senegal",
        "raw_market_key": "totals",
        "raw_market_name": "Total Goals",
        "raw_selection_key": "over_2_5",
        "raw_selection_name": "Over 2.5",
        "decimal_odds": 1.91,
        "line_raw": "2.5",
        "line_value": 2.5,
        "settlement_scope_guess": "regulation_90_plus_stoppage",
        "mapped_market_id": "football_total_goals_regulation",
        "mapping_confidence": 0.97,
        "needs_mapping": False,
    },
    {
        "provider_id": "manual_superbet_reference",
        "bookmaker": "superbet_reference",
        "provider_sport_key": "football",
        "provider_event_id": "manual_event_demo",
        "match_id": "demo_france_senegal",
        "raw_market_key": "raw_superbet_player_combo_demo",
        "raw_market_name": "Jucător șuturi pe poartă + echipă cornere",
        "raw_selection_key": "raw_leg_combo",
        "raw_selection_name": "Player 1+ SOT and France 5+ corners",
        "decimal_odds": 2.90,
        "line_raw": "combo",
        "settlement_scope_guess": "regulation_90_plus_stoppage",
        "mapped_market_id": None,
        "mapping_confidence": 0.0,
        "needs_mapping": True,
    },
]


def grouped(con, sql: str) -> List[Dict[str, Any]]:
    cur = con.execute(sql)
    cols = [d[0] for d in cur.description]
    return [{cols[i]: row[i] for i in range(len(cols))} for row in cur.fetchall()]


def build_report(db: Path) -> Dict[str, Any]:
    con = connect(db)
    try:
        register_default_sources(con)
        observed_at = utc_now()
        inserted = []
        for snap in SAMPLE_SNAPSHOTS:
            snap = dict(snap)
            snap["observed_at"] = observed_at
            snap["last_update"] = observed_at
            snap["raw_json"] = {"sample": True, **snap}
            inserted.append(store_raw_market_snapshot(con, snap))

        counts = table_counts(con)
        coverage = grouped(
            con,
            """
            SELECT provider_id, bookmaker,
                   COUNT(*) AS snapshots,
                   SUM(CASE WHEN needs_mapping=0 AND mapped_market_id IS NOT NULL AND mapped_market_id!='' THEN 1 ELSE 0 END) AS mapped,
                   SUM(CASE WHEN needs_mapping=1 OR mapped_market_id IS NULL OR mapped_market_id='' THEN 1 ELSE 0 END) AS unknown
            FROM raw_market_snapshots
            GROUP BY provider_id, bookmaker
            ORDER BY provider_id, bookmaker
            """,
        )
        unknown = grouped(
            con,
            """
            SELECT raw_market_name, raw_selection_name, provider_id, bookmaker, snapshot_count, example_match_id
            FROM unknown_market_queue
            ORDER BY snapshot_count DESC, raw_market_name, raw_selection_name
            """,
        )
        mapped_market_counts = grouped(
            con,
            """
            SELECT mapped_market_id, COUNT(*) AS snapshots
            FROM raw_market_snapshots
            WHERE mapped_market_id IS NOT NULL AND mapped_market_id!=''
            GROUP BY mapped_market_id
            ORDER BY snapshots DESC, mapped_market_id
            """,
        )
    finally:
        con.close()

    return {
        "ok": True,
        "milestone": "v32_raw_market_snapshot_warehouse",
        "db": str(db),
        "inserted_snapshot_ids": inserted,
        "counts": counts,
        "provider_market_coverage": coverage,
        "unknown_market_queue": unknown,
        "mapped_market_counts": mapped_market_counts,
        "acceptance": {
            "raw_market_snapshots_positive": counts.get("raw_market_snapshots", 0) >= 3,
            "unknown_queue_positive": counts.get("unknown_market_queue", 0) >= 1,
            "mapped_markets_positive": len(mapped_market_counts) >= 2,
            "no_provider_calls": True,
            "no_scraping": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v32 raw market snapshot warehouse smoke.")
    ap.add_argument("--db", default="../build/omnibet_v32_market_smoke.sqlite")
    ap.add_argument("--out", default="../reports/ci_v32_market_snapshot_smoke.json")
    args = ap.parse_args()
    result = build_report(Path(args.db))
    write_json(Path(args.out), result)
    print(json.dumps(result, indent=2))
    if not all(result["acceptance"].values()):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
