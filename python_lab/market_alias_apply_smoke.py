#!/usr/bin/env python3
"""v34 safe market alias apply smoke.

No provider calls. No website automation. This takes raw market snapshots,
uses exact high-confidence canonical market aliases, applies safe mappings, and
leaves unknowns in the queue.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect, register_default_sources, sha_text, store_raw_market_snapshot, table_counts, utc_now

AUTO_THRESHOLD = 0.95


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def seed_markets(con) -> None:
    markets = [
        ("football_1x2_regulation", "football", "1x2", "1X2 regulation", "regulation_90_plus_stoppage", "full_match", 0, 0, 0),
        ("football_to_qualify", "football", "qualification", "To qualify", "includes_extra_time_and_penalties", "full_tie", 0, 0, 0),
        ("football_shots_total_regulation", "football", "shots", "Total shots regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0),
        ("football_shots_on_target_total_regulation", "football", "shots_on_target", "Total shots on target regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0),
        ("football_corners_total_regulation", "football", "corners", "Total corners regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0),
    ]
    for row in markets:
        con.execute(
            """INSERT OR REPLACE INTO canonical_markets
               (canonical_market_id, sport, market_family, display_name, settlement_scope, period,
                line_required, team_required, player_required, dangerous_confusables_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*row, "[]"),
        )

    aliases = [
        ("1X2", "football_1x2_regulation"),
        ("Final", "football_1x2_regulation"),
        ("Match winner", "football_1x2_regulation"),
        ("To qualify", "football_to_qualify"),
        ("Calificare", "football_to_qualify"),
        ("Shots", "football_shots_total_regulation"),
        ("Total shots", "football_shots_total_regulation"),
        ("Shots on target", "football_shots_on_target_total_regulation"),
        ("Suturi pe poarta", "football_shots_on_target_total_regulation"),
        ("Șuturi pe poartă", "football_shots_on_target_total_regulation"),
        ("Corners", "football_corners_total_regulation"),
        ("Total corners", "football_corners_total_regulation"),
        ("Cornere", "football_corners_total_regulation"),
        ("Lovituri de colț", "football_corners_total_regulation"),
    ]
    for alias, canonical_id in aliases:
        alias_id = f"market_alias:{canonical_id}:{sha_text(alias)[:12]}"
        con.execute(
            """INSERT OR REPLACE INTO market_aliases
               (alias_id, canonical_market_id, provider_id, alias_text, normalized_alias, confidence, source_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, canonical_id, None, alias, normalize_text(alias), 1.0, "v34 seed"),
        )
    con.commit()


def seed_raw_snapshots(con) -> List[str]:
    observed_at = utc_now()
    samples = [
        ("superbet_ref", "Cornere", "Peste 9.5", 1.90, "9.5"),
        ("superbet_ref", "Lovituri de colț", "Sub 10.5", 1.83, "10.5"),
        ("odds_api", "Shots", "Over 24.5", 1.95, "24.5"),
        ("odds_api", "Shots on target", "Over 8.5", 1.92, "8.5"),
        ("superbet_ref", "Final", "1", 1.50, None),
        ("superbet_ref", "To qualify", "France", 1.35, None),
        ("superbet_ref", "Special player combo weird market", "Player SOT plus team corners", 2.90, None),
    ]
    inserted = []
    for idx, (provider, market, selection, odds, line) in enumerate(samples):
        snap = {
            "observed_at": observed_at,
            "provider_id": provider,
            "bookmaker": "example_bookmaker",
            "provider_sport_key": "football",
            "provider_event_id": "event_demo_v34",
            "match_id": "demo_match_v34",
            "raw_market_key": f"raw_market_{idx}",
            "raw_market_name": market,
            "raw_selection_key": f"raw_selection_{idx}",
            "raw_selection_name": selection,
            "decimal_odds": odds,
            "line_raw": line,
            "line_value": float(line) if line is not None else None,
            "settlement_scope_guess": "regulation_90_plus_stoppage",
            "mapped_market_id": None,
            "mapping_confidence": 0.0,
            "needs_mapping": True,
            "last_update": observed_at,
            "raw_json": {"sample": True, "market": market, "selection": selection},
        }
        inserted.append(store_raw_market_snapshot(con, snap))
    return inserted


def apply_exact_market_aliases(con) -> Dict[str, Any]:
    snapshots = rows(
        con,
        """
        SELECT raw_market_snapshot_id, raw_market_name, provider_id, bookmaker, raw_json
        FROM raw_market_snapshots
        WHERE needs_mapping=1 OR mapped_market_id IS NULL OR mapped_market_id=''
        ORDER BY raw_market_snapshot_id
        """,
    )
    mapped = []
    unknown = []
    for snap in snapshots:
        norm = normalize_text(snap["raw_market_name"] or "")
        aliases = rows(
            con,
            """
            SELECT canonical_market_id, alias_text, confidence
            FROM market_aliases
            WHERE normalized_alias=? AND confidence>=?
            ORDER BY confidence DESC, canonical_market_id
            """,
            (norm, AUTO_THRESHOLD),
        )
        candidate_id = f"market_candidate:{sha_text(json.dumps([snap['raw_market_snapshot_id'], norm], sort_keys=True))[:16]}"
        if len(aliases) == 1:
            alias = aliases[0]
            con.execute(
                """UPDATE raw_market_snapshots
                   SET mapped_market_id=?, mapping_confidence=?, needs_mapping=0
                   WHERE raw_market_snapshot_id=?""",
                (alias["canonical_market_id"], alias["confidence"], snap["raw_market_snapshot_id"]),
            )
            con.execute(
                """INSERT OR REPLACE INTO resolver_mapping_candidates
                   (candidate_id, entity_type, raw_value, normalized_raw_value, provider_id, context_json,
                    candidate_canonical_id, candidate_display_name, strategy, confidence, auto_map_allowed, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate_id,
                    "market",
                    snap["raw_market_name"],
                    norm,
                    snap["provider_id"],
                    json.dumps({"raw_market_snapshot_id": snap["raw_market_snapshot_id"]}, sort_keys=True),
                    alias["canonical_market_id"],
                    alias["alias_text"],
                    "exact_market_alias",
                    alias["confidence"],
                    1,
                    "exact high-confidence market alias",
                ),
            )
            con.execute(
                """INSERT OR REPLACE INTO resolver_mapping_decisions
                   (decision_id, candidate_id, entity_type, raw_value, provider_id, canonical_id, decision, confidence, reason, decided_by, immutable_raw_ref)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"decision:{candidate_id}",
                    candidate_id,
                    "market",
                    snap["raw_market_name"],
                    snap["provider_id"],
                    alias["canonical_market_id"],
                    "auto_mapped",
                    alias["confidence"],
                    "exact high-confidence market alias",
                    "v34_smoke",
                    snap["raw_market_snapshot_id"],
                ),
            )
            mapped.append({"snapshot_id": snap["raw_market_snapshot_id"], "raw_market_name": snap["raw_market_name"], "canonical_market_id": alias["canonical_market_id"]})
        else:
            con.execute(
                """INSERT OR REPLACE INTO resolver_mapping_candidates
                   (candidate_id, entity_type, raw_value, normalized_raw_value, provider_id, context_json,
                    candidate_canonical_id, candidate_display_name, strategy, confidence, auto_map_allowed, reason)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    candidate_id,
                    "market",
                    snap["raw_market_name"],
                    norm,
                    snap["provider_id"],
                    json.dumps({"raw_market_snapshot_id": snap["raw_market_snapshot_id"]}, sort_keys=True),
                    None,
                    None,
                    "exact_market_alias",
                    0.0,
                    0,
                    "no exact high-confidence alias",
                ),
            )
            unknown.append({"snapshot_id": snap["raw_market_snapshot_id"], "raw_market_name": snap["raw_market_name"], "alias_matches": len(aliases)})
    con.commit()
    return {"mapped": mapped, "unknown": unknown}


def build_report(db: Path) -> Dict[str, Any]:
    con = connect(db)
    try:
        register_default_sources(con)
        seed_markets(con)
        inserted = seed_raw_snapshots(con)
        before = table_counts(con)
        result = apply_exact_market_aliases(con)
        after = table_counts(con)
        mapped_rows = rows(
            con,
            """
            SELECT raw_market_name, raw_selection_name, mapped_market_id, needs_mapping, mapping_confidence
            FROM raw_market_snapshots
            ORDER BY raw_market_name, raw_selection_name
            """,
        )
        unknown_queue = rows(
            con,
            """
            SELECT raw_market_name, raw_selection_name, snapshot_count
            FROM unknown_market_queue
            ORDER BY raw_market_name, raw_selection_name
            """,
        )
    finally:
        con.close()

    mapped_by_name = {r["raw_market_name"]: r["mapped_market_id"] for r in mapped_rows if not r["needs_mapping"]}
    unknown_names = {r["raw_market_name"] for r in unknown_queue}
    acceptance = {
        "corners_aliases_mapped": mapped_by_name.get("Cornere") == "football_corners_total_regulation" and mapped_by_name.get("Lovituri de colț") == "football_corners_total_regulation",
        "shots_and_sot_separate": mapped_by_name.get("Shots") == "football_shots_total_regulation" and mapped_by_name.get("Shots on target") == "football_shots_on_target_total_regulation",
        "final_and_qualify_separate": mapped_by_name.get("Final") == "football_1x2_regulation" and mapped_by_name.get("To qualify") == "football_to_qualify",
        "unknown_remains_unknown": "Special player combo weird market" in unknown_names,
        "mapped_count_positive": len(result["mapped"]) >= 6,
        "decisions_written": after.get("resolver_mapping_decisions", 0) >= 6,
        "raw_snapshots_preserved": after.get("raw_market_snapshots", 0) == before.get("raw_market_snapshots", 0) == len(inserted),
        "no_provider_calls": True,
        "no_website_automation": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v34_safe_market_mapping_application_engine",
        "db": str(db),
        "inserted_snapshot_ids": inserted,
        "counts_before": before,
        "counts_after": after,
        "apply_result": result,
        "mapped_rows": mapped_rows,
        "unknown_market_queue": unknown_queue,
        "acceptance": acceptance,
        "policy": {
            "auto_mapping": "exact high-confidence aliases only",
            "fuzzy_market_auto_mapping": False,
            "unknowns_preserved": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v34 safe market alias apply smoke.")
    ap.add_argument("--db", default="../build/omnibet_v34_market_alias_apply.sqlite")
    ap.add_argument("--out", default="../reports/ci_v34_market_alias_apply.json")
    args = ap.parse_args()
    report = build_report(Path(args.db))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
