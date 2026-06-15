#!/usr/bin/env python3
"""
OmniBet Lab v4 warehouse helpers.

This creates a source-neutral warehouse:
- source_registry / update_runs / raw_source_blobs for sync bookkeeping
- bronze_blobs for raw API/CSV payloads
- normalized matches/teams/players/events/odds skeletons
- adapter watermarks for incremental updates

The warehouse is intentionally conservative:
raw data is preserved first, normalized later, features last.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


WAREHOUSE_SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS source_registry (
    source_id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    source_type TEXT NOT NULL,
    display_name TEXT NOT NULL,
    update_mode TEXT NOT NULL,
    url TEXT,
    api_key_env TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    min_interval_minutes INTEGER NOT NULL DEFAULT 60,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS update_runs (
    run_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    finished_at TEXT,
    status TEXT NOT NULL,
    rows_seen INTEGER DEFAULT 0,
    rows_inserted INTEGER DEFAULT 0,
    rows_updated INTEGER DEFAULT 0,
    error TEXT,
    report_json TEXT,
    FOREIGN KEY(source_id) REFERENCES source_registry(source_id)
);

CREATE TABLE IF NOT EXISTS adapter_watermarks (
    source_id TEXT PRIMARY KEY,
    last_success_at TEXT,
    cursor_json TEXT,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS raw_source_blobs (
    blob_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    content_type TEXT,
    sha256 TEXT NOT NULL,
    payload_path TEXT,
    metadata_json TEXT,
    FOREIGN KEY(source_id) REFERENCES source_registry(source_id)
);

CREATE TABLE IF NOT EXISTS bronze_blobs (
    blob_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT,
    fetched_at TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    json_payload TEXT,
    payload_path TEXT,
    metadata_json TEXT
);

CREATE TABLE IF NOT EXISTS competitions (
    competition_id TEXT PRIMARY KEY,
    source_id TEXT,
    sport TEXT NOT NULL,
    name TEXT NOT NULL,
    country TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS seasons (
    season_id TEXT PRIMARY KEY,
    competition_id TEXT,
    name TEXT,
    start_date TEXT,
    end_date TEXT,
    is_current INTEGER,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS teams (
    team_id TEXT PRIMARY KEY,
    source_id TEXT,
    sport TEXT NOT NULL,
    name TEXT NOT NULL,
    country TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS players (
    player_id TEXT PRIMARY KEY,
    source_id TEXT,
    sport TEXT NOT NULL,
    name TEXT NOT NULL,
    nationality TEXT,
    birth_date TEXT,
    position TEXT,
    current_team_id TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS matches_norm (
    match_id TEXT PRIMARY KEY,
    source_id TEXT,
    sport TEXT NOT NULL,
    competition_id TEXT,
    season_id TEXT,
    match_date TEXT,
    status TEXT,
    home_team_id TEXT,
    away_team_id TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    home_score INTEGER,
    away_score INTEGER,
    venue TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS match_events (
    event_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    source_id TEXT,
    event_type TEXT,
    minute INTEGER,
    second INTEGER,
    period TEXT,
    team_id TEXT,
    player_id TEXT,
    related_player_id TEXT,
    x REAL,
    y REAL,
    outcome TEXT,
    xg REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS lineups (
    lineup_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    team_id TEXT,
    player_id TEXT,
    player_name TEXT,
    started INTEGER,
    position TEXT,
    shirt_number INTEGER,
    minutes_played REAL,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS odds_snapshots (
    odds_id TEXT PRIMARY KEY,
    source_id TEXT,
    match_id TEXT,
    bookmaker TEXT,
    market_id TEXT,
    selection TEXT,
    line REAL,
    odds_decimal REAL,
    captured_at TEXT,
    is_live INTEGER,
    raw_json TEXT
);
"""


DEFAULT_SOURCES = [
    {
        "source_id": "thestatsapi_football",
        "sport": "football",
        "source_type": "rest_api",
        "display_name": "TheStatsAPI Football",
        "update_mode": "live_or_scheduled",
        "url": "https://api.thestatsapi.com/api/football",
        "api_key_env": "THESTATSAPI_KEY",
        "min_interval_minutes": 15,
        "notes": "Football fixtures/results, match/player stats, xG, lineups, squads, odds, live stats. Requires paid/free-trial API key.",
    },
    {
        "source_id": "football_data_uk_csv",
        "sport": "football",
        "source_type": "csv_http_or_local",
        "display_name": "Football-Data.co.uk CSV",
        "update_mode": "scheduled_batch",
        "url": "https://www.football-data.co.uk/",
        "api_key_env": "",
        "min_interval_minutes": 720,
        "notes": "Historical results, odds, major league match stats. Good for backfills and closing-line testing.",
    },
    {
        "source_id": "statsbomb_open_data",
        "sport": "football",
        "source_type": "git_json",
        "display_name": "StatsBomb Open Data",
        "update_mode": "manual_or_scheduled_batch",
        "url": "https://github.com/statsbomb/open-data",
        "api_key_env": "",
        "min_interval_minutes": 1440,
        "notes": "Open competitions/matches/events/lineups/360 JSON. Good for event/player model research.",
    },
    {
        "source_id": "odds_api_live",
        "sport": "multi",
        "source_type": "rest_api",
        "display_name": "The Odds API",
        "update_mode": "live_or_scheduled",
        "url": "https://api.the-odds-api.com/v4/",
        "api_key_env": "ODDS_API_KEY",
        "min_interval_minutes": 15,
        "notes": "Multi-sport live/upcoming odds and scores. Requires API key and quota-aware scheduler.",
    },
    {
        "source_id": "nba_api_live",
        "sport": "nba",
        "source_type": "python_package",
        "display_name": "nba_api",
        "update_mode": "live_or_scheduled",
        "url": "https://github.com/swar/nba_api",
        "api_key_env": "",
        "min_interval_minutes": 30,
        "notes": "NBA.com stats/live endpoints via Python package. Respect NBA.com Terms of Use.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db_path))
    con.executescript(WAREHOUSE_SCHEMA)
    return con


def register_default_sources(con: sqlite3.Connection) -> None:
    for s in DEFAULT_SOURCES:
        con.execute(
            """INSERT OR REPLACE INTO source_registry
               (source_id, sport, source_type, display_name, update_mode, url, api_key_env, enabled, min_interval_minutes, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)""",
            (
                s["source_id"], s["sport"], s["source_type"], s["display_name"], s["update_mode"],
                s["url"], s["api_key_env"], s["min_interval_minutes"], s["notes"],
            ),
        )
    con.commit()


def start_run(con: sqlite3.Connection, source_id: str) -> str:
    run_id = f"{source_id}:{utc_now()}"
    con.execute(
        "INSERT OR REPLACE INTO update_runs(run_id, source_id, started_at, status) VALUES (?, ?, ?, ?)",
        (run_id, source_id, utc_now(), "running"),
    )
    con.commit()
    return run_id


def finish_run(con: sqlite3.Connection, run_id: str, status: str, rows_seen: int = 0, rows_inserted: int = 0, rows_updated: int = 0, error: str = "", report: Optional[dict] = None) -> None:
    con.execute(
        """UPDATE update_runs
           SET finished_at=?, status=?, rows_seen=?, rows_inserted=?, rows_updated=?, error=?, report_json=?
           WHERE run_id=?""",
        (utc_now(), status, rows_seen, rows_inserted, rows_updated, error, json.dumps(report or {}, ensure_ascii=False), run_id),
    )
    con.commit()


def store_bronze(con: sqlite3.Connection, source_id: str, entity_type: str, payload: Any, entity_id: Optional[str] = None, metadata: Optional[dict] = None) -> str:
    text = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    h = sha_text(text)
    blob_id = f"{source_id}:{entity_type}:{entity_id or h[:16]}"
    con.execute(
        """INSERT OR REPLACE INTO bronze_blobs
           (blob_id, source_id, entity_type, entity_id, fetched_at, sha256, json_payload, payload_path, metadata_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?)""",
        (blob_id, source_id, entity_type, entity_id, utc_now(), h, text, json.dumps(metadata or {}, ensure_ascii=False)),
    )
    con.commit()
    return blob_id


def table_counts(con: sqlite3.Connection) -> Dict[str, int]:
    tables = [
        "source_registry", "update_runs", "adapter_watermarks", "raw_source_blobs",
        "bronze_blobs", "competitions", "seasons", "teams", "players",
        "matches_norm", "match_events", "lineups", "odds_snapshots",
    ]
    return {t: int(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in tables}
