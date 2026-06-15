#!/usr/bin/env python3
"""
OmniBet Lab live/update manager skeleton.

Goal:
- Keep the local database fresh without mixing source-specific hacks into models.
- Track update runs, source health, import counts, and API quota notes.
- Provide a clean place to add real adapters:
  - Football-Data.co.uk CSV updates
  - StatsBomb open-data sync
  - The Odds API live/upcoming odds
  - nba_api live scoreboard and NBA stats

This v3B script is safe-by-default: it can initialize metadata tables, register
sources, import a local football CSV, and create update reports. API-key live
connectors are documented but intentionally not called unless implemented.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


LIVE_SCHEMA = """
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

CREATE TABLE IF NOT EXISTS raw_source_blobs (
    blob_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    fetched_at TEXT NOT NULL,
    content_type TEXT,
    sha256 TEXT,
    payload_path TEXT,
    metadata_json TEXT,
    FOREIGN KEY(source_id) REFERENCES source_registry(source_id)
);
"""


DEFAULT_SOURCES = [
    {
        "source_id": "football_data_uk_csv",
        "sport": "football",
        "source_type": "csv_http_or_local",
        "display_name": "Football-Data.co.uk CSV",
        "update_mode": "scheduled_batch",
        "url": "https://www.football-data.co.uk/",
        "api_key_env": "",
        "min_interval_minutes": 720,
        "notes": "Historical results, odds, and major league match stats. Best for batch updates/backfills.",
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
        "notes": "Open competitions/matches/events/lineups/360 JSON. Best for event/player modelling research.",
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
        "notes": "Live/upcoming odds and scores. Requires API key and quota-aware scheduler.",
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
        "notes": "NBA.com stats/live endpoints through Python package. Respect NBA.com Terms of Use.",
    },
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect(db: Path) -> sqlite3.Connection:
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(db))
    con.executescript(LIVE_SCHEMA)
    return con


def register_defaults(con: sqlite3.Connection):
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


def init(db: Path) -> dict:
    con = connect(db)
    register_defaults(con)
    counts = {}
    for t in ["source_registry", "update_runs", "raw_source_blobs"]:
        counts[t] = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
    con.close()
    return {"db": str(db), "counts": counts}


def status(db: Path) -> dict:
    con = connect(db)
    register_defaults(con)
    srcs = con.execute(
        """SELECT source_id, sport, source_type, display_name, update_mode, url, api_key_env, enabled,
                  min_interval_minutes, notes
           FROM source_registry ORDER BY sport, source_id"""
    ).fetchall()
    runs = con.execute(
        """SELECT source_id, status, MAX(finished_at), COUNT(*)
           FROM update_runs GROUP BY source_id, status ORDER BY source_id"""
    ).fetchall()
    con.close()

    sources = []
    for row in srcs:
        api_env = row[6] or ""
        sources.append({
            "source_id": row[0],
            "sport": row[1],
            "source_type": row[2],
            "display_name": row[3],
            "update_mode": row[4],
            "url": row[5],
            "api_key_env": api_env,
            "api_key_present": bool(api_env and os.environ.get(api_env)),
            "enabled": bool(row[7]),
            "min_interval_minutes": row[8],
            "notes": row[9],
        })
    return {"sources": sources, "run_summary": runs}


def log_run(con: sqlite3.Connection, source_id: str, status: str, rows_seen: int = 0, rows_inserted: int = 0, rows_updated: int = 0, error: str = "", report: Optional[dict] = None) -> str:
    run_id = f"{source_id}:{int(time.time())}"
    now = utc_now()
    con.execute(
        """INSERT OR REPLACE INTO update_runs
           (run_id, source_id, started_at, finished_at, status, rows_seen, rows_inserted, rows_updated, error, report_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (run_id, source_id, now, now, status, rows_seen, rows_inserted, rows_updated, error, json.dumps(report or {})),
    )
    con.commit()
    return run_id


def import_local_football_csv(db: Path, csv_path: Path, source_id: str = "manual_football_csv") -> dict:
    """Minimal local update path: count rows and record the file as an update.

    Real match-table merge is intentionally delegated to feature_store.py for now.
    This function is the live/update bookkeeping layer.
    """
    con = connect(db)
    register_defaults(con)
    if source_id == "manual_football_csv":
        con.execute(
            """INSERT OR REPLACE INTO source_registry
               (source_id, sport, source_type, display_name, update_mode, url, api_key_env, enabled, min_interval_minutes, notes)
               VALUES (?, 'football', 'local_csv', 'Manual Football CSV Import', 'manual', ?, '', 1, 0, ?)""",
            (source_id, str(csv_path), "User-provided local CSV import. Use feature_store.py to rebuild features."),
        )
    rows = 0
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for _ in csv.DictReader(f):
            rows += 1
    run_id = log_run(con, source_id, "success", rows_seen=rows, rows_inserted=0, rows_updated=0, report={"csv_path": str(csv_path)})
    con.close()
    return {"run_id": run_id, "source_id": source_id, "rows_seen": rows, "note": "Bookkeeping complete. Run feature_store.py init to rebuild model-ready features."}


def write_source_config(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(DEFAULT_SOURCES, indent=2), encoding="utf-8")
    return {"path": str(path), "sources": len(DEFAULT_SOURCES)}


def main():
    ap = argparse.ArgumentParser(description="Manage OmniBet live/batch data updates.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init")
    p_init.add_argument("--db", default="../build/omnibet.sqlite")

    p_status = sub.add_parser("status")
    p_status.add_argument("--db", default="../build/omnibet.sqlite")

    p_import = sub.add_parser("import-local-football-csv")
    p_import.add_argument("--db", default="../build/omnibet.sqlite")
    p_import.add_argument("--csv", required=True)

    p_cfg = sub.add_parser("write-source-config")
    p_cfg.add_argument("--out", default="../config/source_registry.template.json")

    args = ap.parse_args()

    if args.cmd == "init":
        out = init(Path(args.db))
    elif args.cmd == "status":
        out = status(Path(args.db))
    elif args.cmd == "import-local-football-csv":
        out = import_local_football_csv(Path(args.db), Path(args.csv))
    else:
        out = write_source_config(Path(args.out))

    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
