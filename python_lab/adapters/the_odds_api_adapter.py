#!/usr/bin/env python3
"""Offline The Odds API-style adapter.

This adapter is intentionally network-free. It consumes local sample JSON shaped
like The Odds API event odds/markets responses and writes raw market snapshots to
OmniBet's warehouse.
"""
from __future__ import annotations

import json
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from adapters.warehouse import connect, register_default_sources, sha_text, store_raw_market_snapshot, utc_now

AUTO_THRESHOLD = 0.95

MARKET_KEY_ALIASES = {
    "h2h": "1X2",
    "totals": "Total goals",
    "spreads": "Asian handicap",
    "corners": "Corners",
    "shots_on_target": "Shots on target",
    "player_shots_on_target": "Player shots on target",
}

SEED_MARKETS = [
    ("football_1x2_regulation", "football", "1x2", "1X2 regulation", "regulation_90_plus_stoppage", "full_match", 0, 0, 0, ["football_to_qualify"]),
    ("football_total_goals_regulation", "football", "totals", "Total goals regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, []),
    ("football_asian_handicap_regulation", "football", "asian_handicap", "Asian handicap regulation", "regulation_90_plus_stoppage", "full_match", 1, 1, 0, []),
    ("football_corners_total_regulation", "football", "corners", "Total corners regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, []),
    ("football_shots_total_regulation", "football", "shots", "Total shots regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, ["football_shots_on_target_total_regulation"]),
    ("football_shots_on_target_total_regulation", "football", "shots_on_target", "Total shots on target regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 0, ["football_shots_total_regulation"]),
    ("football_player_shots_on_target_regulation", "football", "player_shots_on_target", "Player shots on target regulation", "regulation_90_plus_stoppage", "full_match", 1, 0, 1, []),
]

SEED_ALIASES = [
    ("1X2", "football_1x2_regulation"),
    ("Head to Head", "football_1x2_regulation"),
    ("h2h", "football_1x2_regulation"),
    ("Final", "football_1x2_regulation"),
    ("Total goals", "football_total_goals_regulation"),
    ("Totals", "football_total_goals_regulation"),
    ("Asian handicap", "football_asian_handicap_regulation"),
    ("Spreads", "football_asian_handicap_regulation"),
    ("Corners", "football_corners_total_regulation"),
    ("Total corners", "football_corners_total_regulation"),
    ("Cornere", "football_corners_total_regulation"),
    ("Shots", "football_shots_total_regulation"),
    ("Total shots", "football_shots_total_regulation"),
    ("Shots on target", "football_shots_on_target_total_regulation"),
    ("Player shots on target", "football_player_shots_on_target_regulation"),
]


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value or "")
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = value.lower()
    value = value.replace("&", " and ")
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def rows(con: sqlite3.Connection, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def load_payload(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def seed_canonical_market_aliases(con: sqlite3.Connection) -> None:
    for row in SEED_MARKETS:
        con.execute(
            """INSERT OR REPLACE INTO canonical_markets
               (canonical_market_id, sport, market_family, display_name, settlement_scope, period,
                line_required, team_required, player_required, dangerous_confusables_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (*row[:-1], json.dumps(row[-1])),
        )
    for alias, canonical_id in SEED_ALIASES:
        alias_id = f"market_alias:{canonical_id}:{sha_text(alias)[:12]}"
        con.execute(
            """INSERT OR REPLACE INTO market_aliases
               (alias_id, canonical_market_id, provider_id, alias_text, normalized_alias, confidence, source_note)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (alias_id, canonical_id, None, alias, normalize_text(alias), 1.0, "v35 The Odds API offline seed"),
        )
    con.commit()


def provider_market_name(market_key: str) -> str:
    return MARKET_KEY_ALIASES.get(market_key, market_key.replace("_", " "))


def iter_market_snapshots(payload: Dict[str, Any], provider_id: str) -> Iterable[Dict[str, Any]]:
    event_id = payload.get("id") or payload.get("event_id") or "unknown_event"
    sport_key = payload.get("sport_key")
    home_team = payload.get("home_team")
    away_team = payload.get("away_team")
    observed_default = utc_now()
    for bookmaker in payload.get("bookmakers", []):
        bookmaker_key = bookmaker.get("key") or bookmaker.get("title") or "unknown_bookmaker"
        bookmaker_title = bookmaker.get("title") or bookmaker_key
        bookmaker_update = bookmaker.get("last_update") or observed_default
        for market in bookmaker.get("markets", []):
            market_key = market.get("key") or "unknown_market"
            market_name = provider_market_name(market_key)
            market_update = market.get("last_update") or bookmaker_update
            for idx, outcome in enumerate(market.get("outcomes", [])):
                selection_name = outcome.get("name") or f"outcome_{idx}"
                point = outcome.get("point")
                player_name = outcome.get("description") if "player" in market_key else None
                team_name = selection_name if selection_name in {home_team, away_team} else None
                raw = {
                    "event": payload,
                    "bookmaker": bookmaker,
                    "market": market,
                    "outcome": outcome,
                }
                yield {
                    "observed_at": market_update,
                    "provider_id": provider_id,
                    "bookmaker": bookmaker_title,
                    "provider_sport_key": sport_key,
                    "provider_event_id": event_id,
                    "match_id": f"{provider_id}:{event_id}",
                    "raw_market_key": market_key,
                    "raw_market_name": market_name,
                    "raw_selection_key": f"{market_key}:{idx}:{normalize_text(selection_name)}",
                    "raw_selection_name": selection_name,
                    "decimal_odds": outcome.get("price"),
                    "line_raw": str(point) if point is not None else None,
                    "line_value": float(point) if point is not None else None,
                    "team_name_raw": team_name,
                    "player_name_raw": player_name,
                    "period_raw": "full_match",
                    "settlement_scope_guess": "regulation_90_plus_stoppage",
                    "mapped_market_id": None,
                    "mapping_confidence": 0.0,
                    "needs_mapping": True,
                    "suspended": False,
                    "last_update": market_update,
                    "raw_json": raw,
                }


def apply_exact_market_aliases(con: sqlite3.Connection, provider_id: str) -> Dict[str, Any]:
    snapshots = rows(
        con,
        """
        SELECT raw_market_snapshot_id, raw_market_name, provider_id, bookmaker
        FROM raw_market_snapshots
        WHERE provider_id=? AND (needs_mapping=1 OR mapped_market_id IS NULL OR mapped_market_id='')
        ORDER BY raw_market_snapshot_id
        """,
        (provider_id,),
    )
    mapped: List[Dict[str, Any]] = []
    unknown: List[Dict[str, Any]] = []
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
        candidate_id = f"toa_candidate:{sha_text(json.dumps([snap['raw_market_snapshot_id'], norm], sort_keys=True))[:16]}"
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
                    provider_id,
                    json.dumps({"raw_market_snapshot_id": snap["raw_market_snapshot_id"]}, sort_keys=True),
                    alias["canonical_market_id"],
                    alias["alias_text"],
                    "the_odds_api_exact_market_alias",
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
                    provider_id,
                    alias["canonical_market_id"],
                    "auto_mapped",
                    alias["confidence"],
                    "exact high-confidence market alias",
                    "v35_offline_adapter",
                    snap["raw_market_snapshot_id"],
                ),
            )
            mapped.append({"snapshot_id": snap["raw_market_snapshot_id"], "raw_market_name": snap["raw_market_name"], "canonical_market_id": alias["canonical_market_id"]})
        else:
            unknown.append({"snapshot_id": snap["raw_market_snapshot_id"], "raw_market_name": snap["raw_market_name"], "alias_matches": len(aliases)})
    con.commit()
    return {"mapped": mapped, "unknown": unknown}


def import_offline_event_markets(db_path: Path, input_path: Path, provider_id: str = "the_odds_api_offline_sample") -> Dict[str, Any]:
    payload = load_payload(input_path)
    con = connect(db_path)
    try:
        register_default_sources(con)
        seed_canonical_market_aliases(con)
        snapshot_ids = [store_raw_market_snapshot(con, snap) for snap in iter_market_snapshots(payload, provider_id)]
        apply_result = apply_exact_market_aliases(con, provider_id)
        coverage = rows(
            con,
            """
            SELECT bookmaker, raw_market_key, raw_market_name,
                   COUNT(*) AS outcomes,
                   SUM(CASE WHEN needs_mapping=0 THEN 1 ELSE 0 END) AS mapped,
                   SUM(CASE WHEN needs_mapping=1 THEN 1 ELSE 0 END) AS unknown
            FROM raw_market_snapshots
            WHERE provider_id=?
            GROUP BY bookmaker, raw_market_key, raw_market_name
            ORDER BY bookmaker, raw_market_key
            """,
            (provider_id,),
        )
        unknown_queue = rows(
            con,
            """
            SELECT raw_market_name, raw_selection_name, provider_id, bookmaker, snapshot_count
            FROM unknown_market_queue
            WHERE provider_id=?
            ORDER BY raw_market_name, raw_selection_name
            """,
            (provider_id,),
        )
        mapped_market_ids = rows(
            con,
            """
            SELECT mapped_market_id, COUNT(*) AS snapshots
            FROM raw_market_snapshots
            WHERE provider_id=? AND needs_mapping=0
            GROUP BY mapped_market_id
            ORDER BY mapped_market_id
            """,
            (provider_id,),
        )
        event_count = 1 if payload.get("id") else 0
        bookmaker_count = len(payload.get("bookmakers", []))
        market_count = sum(len(b.get("markets", [])) for b in payload.get("bookmakers", []))
        outcome_count = len(snapshot_ids)
    finally:
        con.close()
    return {
        "ok": True,
        "provider_id": provider_id,
        "input_path": str(input_path),
        "db_path": str(db_path),
        "events_seen": event_count,
        "bookmakers_seen": bookmaker_count,
        "markets_seen": market_count,
        "outcomes_seen": outcome_count,
        "raw_snapshots_inserted": len(snapshot_ids),
        "apply_result": apply_result,
        "coverage": coverage,
        "unknown_market_queue": unknown_queue,
        "mapped_market_ids": mapped_market_ids,
        "safety": {
            "offline_sample_only": True,
            "no_api_key": True,
            "no_network": True,
            "no_website_automation": True,
            "no_fuzzy_auto_mapping": True,
        },
    }
