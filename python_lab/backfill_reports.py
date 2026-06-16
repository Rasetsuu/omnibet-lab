#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def count(con: sqlite3.Connection, table: str, where: str = "", params: tuple[Any, ...] = ()) -> int:
    if not table_exists(con, table):
        return 0
    sql = f'SELECT COUNT(*) FROM "{table}"'
    if where:
        sql += f" WHERE {where}"
    return int(con.execute(sql, params).fetchone()[0])


def scalar(con: sqlite3.Connection, sql: str, params: tuple[Any, ...] = ()) -> Any:
    row = con.execute(sql, params).fetchone()
    return row[0] if row else None


def grouped(con: sqlite3.Connection, table: str, key: str, where: str = "", limit: int | None = None) -> Dict[str, int]:
    if not table_exists(con, table):
        return {}
    sql = f'SELECT COALESCE({key}, "") AS k, COUNT(*) AS n FROM "{table}"'
    if where:
        sql += f" WHERE {where}"
    sql += " GROUP BY k ORDER BY n DESC, k"
    if limit:
        sql += f" LIMIT {int(limit)}"
    return {str(k): int(n) for k, n in con.execute(sql).fetchall()}


def coverage_rate(numer: int, denom: int) -> float | None:
    return round(numer / denom, 6) if denom else None


def table_counts(con: sqlite3.Connection) -> Dict[str, int]:
    rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
    return {name: count(con, name) for (name,) in rows if not str(name).startswith("sqlite_")}


def source_coverage(con: sqlite3.Connection) -> Dict[str, Any]:
    return {
        "summary": table_counts(con),
        "matches_by_source": grouped(con, "matches_norm", "source_id"),
        "events_by_source": grouped(con, "match_events", "source_id"),
        "lineups_by_source": grouped(con, "lineups", "substr(lineup_id, 1, instr(lineup_id || ':', ':') - 1)"),
        "players_by_source": grouped(con, "players", "source_id"),
        "odds_by_source": grouped(con, "odds_snapshots", "source_id"),
        "competitions": grouped(con, "competitions", "name", limit=50),
        "seasons": grouped(con, "seasons", "name", limit=50),
        "date_range": {
            "min_match_date": scalar(con, "SELECT MIN(match_date) FROM matches_norm WHERE match_date IS NOT NULL AND match_date != ''") if table_exists(con, "matches_norm") else None,
            "max_match_date": scalar(con, "SELECT MAX(match_date) FROM matches_norm WHERE match_date IS NOT NULL AND match_date != ''") if table_exists(con, "matches_norm") else None,
        },
    }


def identity_coverage(con: sqlite3.Connection) -> Dict[str, Any]:
    if not table_exists(con, "entity_identity_candidates"):
        return {"candidate_rows": 0, "multi_source_candidate_rows": 0, "top_multi_source_candidates": []}
    candidates = count(con, "entity_identity_candidates")
    multi = count(con, "entity_identity_candidates", "source_count >= 2")
    rows = con.execute(
        """SELECT candidate_id, canonical_name, normalized_name, source_count, sources_json, variants_json
           FROM entity_identity_candidates
           WHERE source_count >= 2
           ORDER BY source_count DESC, canonical_name
           LIMIT 25"""
    ).fetchall()
    return {
        "candidate_rows": candidates,
        "multi_source_candidate_rows": multi,
        "multi_source_rate": coverage_rate(multi, candidates),
        "top_multi_source_candidates": [
            {
                "candidate_id": r[0],
                "canonical_name": r[1],
                "normalized_name": r[2],
                "source_count": r[3],
                "sources": json.loads(r[4] or "[]"),
                "variants": json.loads(r[5] or "[]"),
            }
            for r in rows
        ],
    }


def event_coverage(con: sqlite3.Connection) -> Dict[str, Any]:
    matches = count(con, "matches_norm")
    event_rows = count(con, "match_events")
    event_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM match_events") or 0) if table_exists(con, "match_events") else 0
    xg_rows = count(con, "match_events", "xg IS NOT NULL")
    return {
        "matches_total": matches,
        "event_rows": event_rows,
        "matches_with_events": event_matches,
        "event_match_coverage": coverage_rate(event_matches, matches),
        "xg_event_rows": xg_rows,
        "xg_event_rate": coverage_rate(xg_rows, event_rows),
        "event_types_top": grouped(con, "match_events", "event_type", limit=25),
        "periods": grouped(con, "match_events", "period", limit=25),
    }


def player_coverage(con: sqlite3.Connection) -> Dict[str, Any]:
    matches = count(con, "matches_norm")
    player_rows = count(con, "players")
    lineup_rows = count(con, "lineups")
    lineup_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM lineups") or 0) if table_exists(con, "lineups") else 0
    starters = count(con, "lineups", "started = 1")
    minutes_known = count(con, "lineups", "minutes_played IS NOT NULL")
    return {
        "players_total": player_rows,
        "lineup_rows": lineup_rows,
        "matches_with_lineups": lineup_matches,
        "lineup_match_coverage": coverage_rate(lineup_matches, matches),
        "starter_rows": starters,
        "minutes_known_rows": minutes_known,
        "positions_top": grouped(con, "lineups", "position", where="position IS NOT NULL AND position != ''", limit=25),
    }


def odds_coverage(con: sqlite3.Connection) -> Dict[str, Any]:
    matches = count(con, "matches_norm")
    odds_rows = count(con, "odds_snapshots")
    odds_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM odds_snapshots") or 0) if table_exists(con, "odds_snapshots") else 0
    closing_rows = 0
    closing_matches = 0
    if table_exists(con, "odds_snapshots"):
        closing_where = "LOWER(COALESCE(bookmaker, '')) LIKE '%pinnacle%' OR LOWER(COALESCE(bookmaker, '')) LIKE '%closing%' OR bookmaker='Pinnacle/PS'"
        closing_rows = count(con, "odds_snapshots", closing_where)
        closing_matches = int(scalar(con, f"SELECT COUNT(DISTINCT match_id) FROM odds_snapshots WHERE {closing_where}") or 0)
    return {
        "odds_rows": odds_rows,
        "matches_with_odds": odds_matches,
        "odds_match_coverage": coverage_rate(odds_matches, matches),
        "closing_odds_rows": closing_rows,
        "matches_with_closing_odds": closing_matches,
        "closing_odds_match_coverage": coverage_rate(closing_matches, matches),
        "odds_by_market": grouped(con, "odds_snapshots", "market_id", limit=50),
        "odds_by_bookmaker": grouped(con, "odds_snapshots", "bookmaker", limit=50),
        "odds_by_selection": grouped(con, "odds_snapshots", "selection", limit=50),
    }


def walk_forward_readiness(con: sqlite3.Connection) -> Dict[str, Any]:
    finished = count(con, "matches_norm", "home_score IS NOT NULL AND away_score IS NOT NULL")
    dated_finished = count(con, "matches_norm", "home_score IS NOT NULL AND away_score IS NOT NULL AND match_date IS NOT NULL AND match_date != ''")
    odds_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM odds_snapshots") or 0) if table_exists(con, "odds_snapshots") else 0
    event_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM match_events") or 0) if table_exists(con, "match_events") else 0
    lineup_matches = int(scalar(con, "SELECT COUNT(DISTINCT match_id) FROM lineups") or 0) if table_exists(con, "lineups") else 0
    warnings: List[str] = []
    if finished < 100:
        warnings.append("small_finished_match_count: CI/local smoke only, not model proof")
    if odds_matches < 20:
        warnings.append("small_odds_match_count: not enough for serious CLV validation")
    if event_matches == 0:
        warnings.append("no_event_match_coverage: event-aware features unavailable")
    if lineup_matches == 0:
        warnings.append("no_lineup_match_coverage: lineup/player availability features unavailable")
    return {
        "finished_matches": finished,
        "dated_finished_matches": dated_finished,
        "date_ready_rate": coverage_rate(dated_finished, finished),
        "matches_with_odds": odds_matches,
        "matches_with_events": event_matches,
        "matches_with_lineups": lineup_matches,
        "odds_walk_forward_ready": finished > 0 and dated_finished == finished and odds_matches > 0,
        "event_model_ready": event_matches > 0 and lineup_matches > 0,
        "honesty": "Readiness report only. No model quality or profitability claim.",
        "warnings": warnings,
    }


def build_reports(db_path: Path) -> Dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    try:
        return {
            "source_coverage": source_coverage(con),
            "identity_coverage": identity_coverage(con),
            "event_coverage": event_coverage(con),
            "player_coverage": player_coverage(con),
            "odds_coverage": odds_coverage(con),
            "walk_forward_ready": walk_forward_readiness(con),
        }
    finally:
        con.close()


def write_reports(db_path: Path, reports_dir: Path) -> Dict[str, Any]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    bundle = build_reports(db_path)
    file_map = {
        "source_coverage": "v26_source_coverage_report.json",
        "identity_coverage": "v26_identity_coverage_report.json",
        "event_coverage": "v26_event_coverage_report.json",
        "player_coverage": "v26_player_coverage_report.json",
        "odds_coverage": "v26_odds_coverage_report.json",
        "walk_forward_ready": "v26_walk_forward_ready_report.json",
    }
    written = {}
    for key, filename in file_map.items():
        path = reports_dir / filename
        path.write_text(json.dumps(bundle[key], indent=2), encoding="utf-8")
        written[key] = str(path)
    return {"reports": bundle, "written": written}


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate OmniBet v26 backfill coverage reports from a warehouse SQLite DB.")
    ap.add_argument("--db", required=True)
    ap.add_argument("--reports-dir", required=True)
    args = ap.parse_args()
    result = write_reports(Path(args.db), Path(args.reports_dir))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
