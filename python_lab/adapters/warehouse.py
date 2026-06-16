#!/usr/bin/env python3
"""
OmniBet Lab v4+ warehouse helpers.

This creates a source-neutral warehouse:
- source_registry / update_runs / raw_source_blobs for sync bookkeeping
- bronze_blobs for raw API/CSV payloads
- normalized matches/teams/players/events/odds skeletons
- dynamic raw bookmaker/provider market snapshots for market discovery
- canonical resolver tables for teams/players/markets/selections
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

CREATE TABLE IF NOT EXISTS raw_market_snapshots (
    raw_market_snapshot_id TEXT PRIMARY KEY,
    observed_at TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    bookmaker TEXT,
    provider_sport_key TEXT,
    provider_event_id TEXT,
    match_id TEXT,
    raw_market_key TEXT,
    raw_market_name TEXT,
    raw_selection_key TEXT,
    raw_selection_name TEXT,
    decimal_odds REAL,
    line_raw TEXT,
    line_value REAL,
    team_name_raw TEXT,
    team_id TEXT,
    player_name_raw TEXT,
    player_id TEXT,
    period_raw TEXT,
    settlement_scope_guess TEXT,
    mapped_market_id TEXT,
    mapping_confidence REAL,
    needs_mapping INTEGER NOT NULL DEFAULT 1,
    suspended INTEGER NOT NULL DEFAULT 0,
    last_update TEXT,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_raw_market_event_time
    ON raw_market_snapshots(provider_id, provider_event_id, observed_at);
CREATE INDEX IF NOT EXISTS idx_raw_market_mapping
    ON raw_market_snapshots(needs_mapping, mapped_market_id, raw_market_name, raw_selection_name);
CREATE INDEX IF NOT EXISTS idx_raw_market_match_market
    ON raw_market_snapshots(match_id, mapped_market_id, observed_at);

CREATE TABLE IF NOT EXISTS market_mapping_rules (
    mapping_rule_id TEXT PRIMARY KEY,
    provider_id TEXT,
    bookmaker TEXT,
    raw_market_key TEXT,
    raw_market_name_pattern TEXT,
    raw_selection_name_pattern TEXT,
    mapped_market_id TEXT NOT NULL,
    settlement_scope TEXT,
    parser_hint_json TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_market_mapping_provider
    ON market_mapping_rules(provider_id, bookmaker, enabled);

CREATE VIEW IF NOT EXISTS unknown_market_queue AS
SELECT
    raw_market_name,
    raw_selection_name,
    provider_id,
    bookmaker,
    provider_sport_key,
    COUNT(*) AS snapshot_count,
    MIN(observed_at) AS first_observed_at,
    MAX(observed_at) AS last_observed_at,
    MIN(provider_event_id) AS example_provider_event_id,
    MIN(match_id) AS example_match_id
FROM raw_market_snapshots
WHERE needs_mapping = 1 OR mapped_market_id IS NULL OR mapped_market_id = ''
GROUP BY raw_market_name, raw_selection_name, provider_id, bookmaker, provider_sport_key;

CREATE TABLE IF NOT EXISTS canonical_teams (
    canonical_team_id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    display_name TEXT NOT NULL,
    country TEXT,
    team_type TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS team_aliases (
    alias_id TEXT PRIMARY KEY,
    canonical_team_id TEXT NOT NULL,
    provider_id TEXT,
    alias_text TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(canonical_team_id) REFERENCES canonical_teams(canonical_team_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_team_alias_unique
    ON team_aliases(provider_id, normalized_alias, canonical_team_id);
CREATE INDEX IF NOT EXISTS idx_team_alias_lookup
    ON team_aliases(normalized_alias, provider_id);

CREATE TABLE IF NOT EXISTS canonical_players (
    canonical_player_id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    display_name TEXT NOT NULL,
    birth_date TEXT,
    nationality TEXT,
    primary_team_id TEXT,
    position TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS player_aliases (
    alias_id TEXT PRIMARY KEY,
    canonical_player_id TEXT NOT NULL,
    provider_id TEXT,
    alias_text TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    team_context_id TEXT,
    country_context TEXT,
    shirt_number INTEGER,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(canonical_player_id) REFERENCES canonical_players(canonical_player_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_player_alias_unique
    ON player_aliases(provider_id, normalized_alias, canonical_player_id, COALESCE(team_context_id, ''));
CREATE INDEX IF NOT EXISTS idx_player_alias_lookup
    ON player_aliases(normalized_alias, provider_id, team_context_id);

CREATE TABLE IF NOT EXISTS canonical_markets (
    canonical_market_id TEXT PRIMARY KEY,
    sport TEXT NOT NULL,
    market_family TEXT NOT NULL,
    display_name TEXT NOT NULL,
    settlement_scope TEXT NOT NULL,
    period TEXT,
    line_required INTEGER NOT NULL DEFAULT 0,
    team_required INTEGER NOT NULL DEFAULT 0,
    player_required INTEGER NOT NULL DEFAULT 0,
    dangerous_confusables_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS market_aliases (
    alias_id TEXT PRIMARY KEY,
    canonical_market_id TEXT NOT NULL,
    provider_id TEXT,
    alias_text TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    settlement_scope_hint TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(canonical_market_id) REFERENCES canonical_markets(canonical_market_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_market_alias_unique
    ON market_aliases(provider_id, normalized_alias, canonical_market_id);
CREATE INDEX IF NOT EXISTS idx_market_alias_lookup
    ON market_aliases(normalized_alias, provider_id);

CREATE TABLE IF NOT EXISTS canonical_selections (
    canonical_selection_id TEXT PRIMARY KEY,
    selection_family TEXT NOT NULL,
    display_name TEXT NOT NULL,
    side TEXT,
    metadata_json TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS selection_aliases (
    alias_id TEXT PRIMARY KEY,
    canonical_selection_id TEXT NOT NULL,
    provider_id TEXT,
    alias_text TEXT NOT NULL,
    normalized_alias TEXT NOT NULL,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_note TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(canonical_selection_id) REFERENCES canonical_selections(canonical_selection_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_selection_alias_unique
    ON selection_aliases(provider_id, normalized_alias, canonical_selection_id);
CREATE INDEX IF NOT EXISTS idx_selection_alias_lookup
    ON selection_aliases(normalized_alias, provider_id);

CREATE TABLE IF NOT EXISTS resolver_mapping_candidates (
    candidate_id TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    normalized_raw_value TEXT NOT NULL,
    provider_id TEXT,
    context_json TEXT,
    candidate_canonical_id TEXT,
    candidate_display_name TEXT,
    strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    auto_map_allowed INTEGER NOT NULL DEFAULT 0,
    reason TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS resolver_mapping_decisions (
    decision_id TEXT PRIMARY KEY,
    candidate_id TEXT,
    entity_type TEXT NOT NULL,
    raw_value TEXT NOT NULL,
    provider_id TEXT,
    canonical_id TEXT,
    decision TEXT NOT NULL,
    confidence REAL,
    reason TEXT,
    decided_by TEXT NOT NULL DEFAULT 'system',
    decided_at TEXT DEFAULT CURRENT_TIMESTAMP,
    immutable_raw_ref TEXT,
    FOREIGN KEY(candidate_id) REFERENCES resolver_mapping_candidates(candidate_id)
);

CREATE VIEW IF NOT EXISTS resolver_review_queue AS
SELECT
    entity_type,
    raw_value,
    normalized_raw_value,
    provider_id,
    context_json,
    candidate_canonical_id,
    candidate_display_name,
    strategy,
    confidence,
    reason,
    COUNT(*) AS candidate_count,
    MIN(created_at) AS first_seen_at,
    MAX(created_at) AS last_seen_at
FROM resolver_mapping_candidates
WHERE auto_map_allowed = 0 OR confidence < 0.95 OR candidate_canonical_id IS NULL OR candidate_canonical_id = ''
GROUP BY entity_type, raw_value, normalized_raw_value, provider_id, context_json,
         candidate_canonical_id, candidate_display_name, strategy, confidence, reason;
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


WAREHOUSE_COUNT_TABLES = [
    "source_registry", "update_runs", "adapter_watermarks", "raw_source_blobs",
    "bronze_blobs", "competitions", "seasons", "teams", "players",
    "matches_norm", "match_events", "lineups", "odds_snapshots",
    "raw_market_snapshots", "market_mapping_rules", "unknown_market_queue",
    "canonical_teams", "team_aliases", "canonical_players", "player_aliases",
    "canonical_markets", "market_aliases", "canonical_selections", "selection_aliases",
    "resolver_mapping_candidates", "resolver_mapping_decisions", "resolver_review_queue",
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


def store_raw_market_snapshot(con: sqlite3.Connection, snapshot: Dict[str, Any]) -> str:
    raw_json = json.dumps(snapshot.get("raw_json", snapshot), ensure_ascii=False, sort_keys=True)
    payload_sha256 = snapshot.get("payload_sha256") or sha_text(raw_json)
    snapshot_id = snapshot.get("raw_market_snapshot_id") or f"{snapshot.get('provider_id', 'provider')}:{snapshot.get('provider_event_id', 'event')}:{snapshot.get('raw_market_key', 'market')}:{snapshot.get('raw_selection_key', 'selection')}:{payload_sha256[:12]}"
    con.execute(
        """INSERT OR REPLACE INTO raw_market_snapshots
           (raw_market_snapshot_id, observed_at, provider_id, bookmaker, provider_sport_key, provider_event_id,
            match_id, raw_market_key, raw_market_name, raw_selection_key, raw_selection_name, decimal_odds,
            line_raw, line_value, team_name_raw, team_id, player_name_raw, player_id, period_raw,
            settlement_scope_guess, mapped_market_id, mapping_confidence, needs_mapping, suspended,
            last_update, payload_sha256, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            snapshot_id,
            snapshot.get("observed_at") or utc_now(),
            snapshot["provider_id"],
            snapshot.get("bookmaker"),
            snapshot.get("provider_sport_key"),
            snapshot.get("provider_event_id"),
            snapshot.get("match_id"),
            snapshot.get("raw_market_key"),
            snapshot.get("raw_market_name"),
            snapshot.get("raw_selection_key"),
            snapshot.get("raw_selection_name"),
            snapshot.get("decimal_odds"),
            snapshot.get("line_raw"),
            snapshot.get("line_value"),
            snapshot.get("team_name_raw"),
            snapshot.get("team_id"),
            snapshot.get("player_name_raw"),
            snapshot.get("player_id"),
            snapshot.get("period_raw"),
            snapshot.get("settlement_scope_guess"),
            snapshot.get("mapped_market_id"),
            snapshot.get("mapping_confidence"),
            int(bool(snapshot.get("needs_mapping", not snapshot.get("mapped_market_id")))),
            int(bool(snapshot.get("suspended", False))),
            snapshot.get("last_update"),
            payload_sha256,
            raw_json,
        ),
    )
    con.commit()
    return snapshot_id


def table_counts(con: sqlite3.Connection) -> Dict[str, int]:
    return {t: int(con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]) for t in WAREHOUSE_COUNT_TABLES}
