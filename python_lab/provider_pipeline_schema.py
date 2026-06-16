#!/usr/bin/env python3
"""Shared provider-pipeline schema helpers for v42-v48.

Earlier milestones kept new tables inside individual smokes for safe iteration.
This module promotes those table definitions into one shared, reusable schema
extension without changing legacy warehouse behavior.
"""
from __future__ import annotations

import sqlite3

PROVIDER_PIPELINE_SCHEMA = """
CREATE TABLE IF NOT EXISTS provider_event_links (
    link_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    provider_event_id TEXT NOT NULL,
    provider_match_id TEXT,
    sport TEXT,
    competition TEXT,
    commence_time TEXT,
    home_team_name TEXT,
    away_team_name TEXT,
    link_strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_provider_event_links_provider
    ON provider_event_links(provider_id, provider_event_id, provider_match_id);
CREATE INDEX IF NOT EXISTS idx_provider_event_links_canonical
    ON provider_event_links(canonical_event_id);

CREATE TABLE IF NOT EXISTS provider_event_timeline (
    timeline_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    timeline_type TEXT NOT NULL,
    observed_at TEXT,
    source_provider_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    bookmaker TEXT,
    match_status TEXT,
    minute INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    event_type TEXT,
    team_id TEXT,
    player_id TEXT,
    mapped_market_id TEXT,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    needs_mapping INTEGER,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_provider_event_timeline_event_time
    ON provider_event_timeline(canonical_event_id, observed_at, timeline_type);
CREATE INDEX IF NOT EXISTS idx_provider_event_timeline_market
    ON provider_event_timeline(canonical_event_id, mapped_market_id, raw_market_name);

CREATE TABLE IF NOT EXISTS settlement_rules (
    rule_id TEXT PRIMARY KEY,
    mapped_market_id TEXT NOT NULL,
    truth_key TEXT NOT NULL,
    settlement_scope TEXT NOT NULL,
    supported INTEGER NOT NULL,
    rule_version TEXT NOT NULL,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS outcome_truth (
    truth_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    truth_key TEXT NOT NULL,
    truth_value_text TEXT,
    truth_value_numeric REAL,
    source_ref TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_outcome_truth_event_key
    ON outcome_truth(canonical_event_id, truth_key);

CREATE TABLE IF NOT EXISTS settlement_evaluations (
    evaluation_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    mapped_market_id TEXT,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    settlement_result TEXT NOT NULL,
    settlement_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_settlement_eval_event_market
    ON settlement_evaluations(canonical_event_id, mapped_market_id, settlement_status);

CREATE TABLE IF NOT EXISTS event_feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    snapshot_stage TEXT NOT NULL,
    feature_cutoff_time TEXT,
    source_ref TEXT NOT NULL,
    match_status TEXT,
    minute INTEGER,
    event_type TEXT,
    team_id TEXT,
    player_id TEXT,
    home_score INTEGER,
    away_score INTEGER,
    final_truth_allowed INTEGER NOT NULL DEFAULT 0,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_event_feature_stage
    ON event_feature_snapshots(canonical_event_id, snapshot_stage, feature_cutoff_time);

CREATE TABLE IF NOT EXISTS market_feature_snapshots (
    feature_snapshot_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    snapshot_stage TEXT NOT NULL,
    feature_cutoff_time TEXT,
    source_ref TEXT NOT NULL,
    bookmaker TEXT,
    mapped_market_id TEXT,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    implied_probability REAL,
    home_score INTEGER,
    away_score INTEGER,
    final_truth_allowed INTEGER NOT NULL DEFAULT 0,
    settlement_result TEXT,
    settlement_status TEXT,
    model_eligible INTEGER NOT NULL DEFAULT 0,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_market_feature_stage
    ON market_feature_snapshots(canonical_event_id, snapshot_stage, mapped_market_id, feature_cutoff_time);

CREATE TABLE IF NOT EXISTS offline_paper_evaluations (
    paper_eval_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    source_ref TEXT NOT NULL,
    mapped_market_id TEXT NOT NULL,
    raw_market_name TEXT,
    raw_selection_name TEXT,
    line_value REAL,
    decimal_odds REAL,
    implied_probability REAL,
    baseline_probability REAL,
    settlement_result TEXT NOT NULL,
    paper_unit_result REAL NOT NULL,
    evaluation_status TEXT NOT NULL,
    reason TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_offline_paper_eval_event
    ON offline_paper_evaluations(canonical_event_id, mapped_market_id, settlement_result);

CREATE TABLE IF NOT EXISTS provider_identity_candidates (
    candidate_id TEXT PRIMARY KEY,
    canonical_entity_type TEXT NOT NULL,
    canonical_id TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    provider_entity_id TEXT,
    raw_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    match_strategy TEXT NOT NULL,
    confidence REAL NOT NULL,
    decision TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_provider_identity_candidates_lookup
    ON provider_identity_candidates(canonical_entity_type, provider_id, normalized_name, decision);

CREATE TABLE IF NOT EXISTS provider_identity_review_queue (
    review_id TEXT PRIMARY KEY,
    canonical_entity_type TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    provider_entity_id TEXT,
    raw_name TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    candidate_canonical_id TEXT,
    confidence REAL NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_provider_identity_review_queue_type
    ON provider_identity_review_queue(canonical_entity_type, provider_id, confidence);

CREATE TABLE IF NOT EXISTS player_prop_truth (
    truth_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    provider_player_id TEXT,
    canonical_player_id TEXT,
    player_name TEXT NOT NULL,
    stat_key TEXT NOT NULL,
    stat_value REAL NOT NULL,
    minutes_played REAL,
    source_ref TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    raw_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_player_prop_truth_lookup
    ON player_prop_truth(canonical_event_id, player_name, stat_key);

CREATE TABLE IF NOT EXISTS feature_export_manifest (
    export_id TEXT PRIMARY KEY,
    export_version TEXT NOT NULL,
    canonical_event_id TEXT NOT NULL,
    output_dir TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    manifest_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS first_model_pass_reports (
    report_id TEXT PRIMARY KEY,
    canonical_event_id TEXT NOT NULL,
    model_kind TEXT NOT NULL,
    train_rows INTEGER NOT NULL,
    eval_rows INTEGER NOT NULL,
    metrics_json TEXT NOT NULL,
    caveat TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS live_provider_scaffold_runs (
    run_id TEXT PRIMARY KEY,
    provider_id TEXT NOT NULL,
    mode TEXT NOT NULL,
    api_key_env TEXT NOT NULL,
    network_enabled INTEGER NOT NULL,
    would_call_endpoint TEXT,
    status TEXT NOT NULL,
    reason TEXT NOT NULL,
    raw_json TEXT
);
"""

EXPECTED_PROVIDER_PIPELINE_TABLES = [
    "provider_event_links",
    "provider_event_timeline",
    "settlement_rules",
    "outcome_truth",
    "settlement_evaluations",
    "event_feature_snapshots",
    "market_feature_snapshots",
    "offline_paper_evaluations",
    "provider_identity_candidates",
    "provider_identity_review_queue",
    "player_prop_truth",
    "feature_export_manifest",
    "first_model_pass_reports",
    "live_provider_scaffold_runs",
]


def ensure_provider_pipeline_schema(con: sqlite3.Connection) -> None:
    con.executescript(PROVIDER_PIPELINE_SCHEMA)
    con.commit()


def provider_pipeline_table_counts(con: sqlite3.Connection) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in EXPECTED_PROVIDER_PIPELINE_TABLES:
        counts[table] = int(con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
    return counts
