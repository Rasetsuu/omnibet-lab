#!/usr/bin/env python3
"""v37 offline provider event timeline join smoke.

This imports the v35 The Odds API-style offline sample and v36 API-Football-style
offline sample into one SQLite database, links both provider event ids to one
canonical event id, and materializes a combined provider event timeline.

No API keys, network calls, or live provider access are used.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from adapters.api_football_adapter import import_offline_live_state
from adapters.the_odds_api_adapter import import_offline_event_markets
from adapters.warehouse import connect, sha_text, table_counts, utc_now

TIMELINE_SCHEMA = """
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
"""


def load_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(con, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def ensure_schema(con) -> None:
    con.executescript(TIMELINE_SCHEMA)
    con.commit()


def insert_provider_links(con, link_manifest: Dict[str, Any]) -> List[str]:
    canonical_event_id = link_manifest["canonical_event_id"]
    inserted = []
    for link in link_manifest.get("provider_links", []):
        link_id = f"event_link:{canonical_event_id}:{link['provider_id']}:{link['provider_event_id']}"
        con.execute(
            """INSERT OR REPLACE INTO provider_event_links
               (link_id, canonical_event_id, provider_id, provider_event_id, provider_match_id,
                sport, competition, commence_time, home_team_name, away_team_name,
                link_strategy, confidence, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                link_id,
                canonical_event_id,
                link["provider_id"],
                str(link["provider_event_id"]),
                link.get("provider_match_id"),
                link_manifest.get("sport"),
                link_manifest.get("competition"),
                link_manifest.get("commence_time"),
                link_manifest.get("home_team_name"),
                link_manifest.get("away_team_name"),
                link.get("link_strategy") or "manual_manifest",
                float(link.get("confidence", 1.0)),
                json.dumps(link, ensure_ascii=False, sort_keys=True),
            ),
        )
        inserted.append(link_id)
    con.commit()
    return inserted


def rebuild_timeline(con, canonical_event_id: str) -> Dict[str, int]:
    con.execute("DELETE FROM provider_event_timeline WHERE canonical_event_id=?", (canonical_event_id,))
    inserted = {"match_state": 0, "match_event": 0, "odds_market": 0}

    api_links = rows(
        con,
        "SELECT * FROM provider_event_links WHERE canonical_event_id=? AND provider_id='api_football_offline_sample'",
        (canonical_event_id,),
    )
    for link in api_links:
        match_rows = rows(con, "SELECT * FROM matches_norm WHERE match_id=?", (link["provider_match_id"],))
        for match in match_rows:
            raw = json.dumps(match, ensure_ascii=False, sort_keys=True)
            tid = f"timeline:{canonical_event_id}:match_state:{match['match_id']}"
            con.execute(
                """INSERT OR REPLACE INTO provider_event_timeline
                   (timeline_id, canonical_event_id, timeline_type, observed_at, source_provider_id, source_ref,
                    match_status, home_score, away_score, payload_sha256, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tid,
                    canonical_event_id,
                    "match_state",
                    match.get("match_date"),
                    "api_football_offline_sample",
                    match["match_id"],
                    match.get("status"),
                    match.get("home_score"),
                    match.get("away_score"),
                    sha_text(raw),
                    raw,
                ),
            )
            inserted["match_state"] += 1
        event_rows = rows(con, "SELECT * FROM match_events WHERE match_id=? ORDER BY minute, event_id", (link["provider_match_id"],))
        for ev in event_rows:
            raw = json.dumps(ev, ensure_ascii=False, sort_keys=True)
            tid = f"timeline:{canonical_event_id}:match_event:{ev['event_id']}"
            con.execute(
                """INSERT OR REPLACE INTO provider_event_timeline
                   (timeline_id, canonical_event_id, timeline_type, observed_at, source_provider_id, source_ref,
                    minute, event_type, team_id, player_id, payload_sha256, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tid,
                    canonical_event_id,
                    "match_event",
                    None,
                    "api_football_offline_sample",
                    ev["event_id"],
                    ev.get("minute"),
                    ev.get("event_type"),
                    ev.get("team_id"),
                    ev.get("player_id"),
                    sha_text(raw),
                    raw,
                ),
            )
            inserted["match_event"] += 1

    odds_links = rows(
        con,
        "SELECT * FROM provider_event_links WHERE canonical_event_id=? AND provider_id='the_odds_api_offline_sample'",
        (canonical_event_id,),
    )
    for link in odds_links:
        market_rows = rows(
            con,
            """
            SELECT * FROM raw_market_snapshots
            WHERE provider_id=? AND provider_event_id=?
            ORDER BY observed_at, bookmaker, raw_market_key, raw_selection_key
            """,
            (link["provider_id"], link["provider_event_id"]),
        )
        for snap in market_rows:
            raw = json.dumps(snap, ensure_ascii=False, sort_keys=True)
            tid = f"timeline:{canonical_event_id}:odds_market:{snap['raw_market_snapshot_id']}"
            con.execute(
                """INSERT OR REPLACE INTO provider_event_timeline
                   (timeline_id, canonical_event_id, timeline_type, observed_at, source_provider_id, source_ref,
                    bookmaker, mapped_market_id, raw_market_name, raw_selection_name, line_value, decimal_odds,
                    needs_mapping, payload_sha256, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tid,
                    canonical_event_id,
                    "odds_market",
                    snap.get("observed_at"),
                    "the_odds_api_offline_sample",
                    snap["raw_market_snapshot_id"],
                    snap.get("bookmaker"),
                    snap.get("mapped_market_id"),
                    snap.get("raw_market_name"),
                    snap.get("raw_selection_name"),
                    snap.get("line_value"),
                    snap.get("decimal_odds"),
                    snap.get("needs_mapping"),
                    sha_text(raw),
                    raw,
                ),
            )
            inserted["odds_market"] += 1
    con.commit()
    return inserted


def build_report(db: Path, odds_input: Path, state_input: Path, link_input: Path) -> Dict[str, Any]:
    odds_report = import_offline_event_markets(db, odds_input)
    state_report = import_offline_live_state(db, state_input)
    link_manifest = load_json(link_input)
    canonical_event_id = link_manifest["canonical_event_id"]
    con = connect(db)
    try:
        ensure_schema(con)
        link_ids = insert_provider_links(con, link_manifest)
        inserted_by_type = rebuild_timeline(con, canonical_event_id)
        timeline_counts = rows(
            con,
            """
            SELECT timeline_type, COUNT(*) AS rows
            FROM provider_event_timeline
            WHERE canonical_event_id=?
            GROUP BY timeline_type
            ORDER BY timeline_type
            """,
            (canonical_event_id,),
        )
        market_counts = rows(
            con,
            """
            SELECT COALESCE(mapped_market_id, 'UNKNOWN') AS market_id, COUNT(*) AS rows
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='odds_market'
            GROUP BY COALESCE(mapped_market_id, 'UNKNOWN')
            ORDER BY market_id
            """,
            (canonical_event_id,),
        )
        unknown_markets = rows(
            con,
            """
            SELECT raw_market_name, raw_selection_name, bookmaker, decimal_odds
            FROM provider_event_timeline
            WHERE canonical_event_id=? AND timeline_type='odds_market' AND needs_mapping=1
            ORDER BY raw_market_name, raw_selection_name
            """,
            (canonical_event_id,),
        )
        compact_timeline = rows(
            con,
            """
            SELECT timeline_type, observed_at, minute, match_status, home_score, away_score,
                   event_type, mapped_market_id, raw_market_name, raw_selection_name, decimal_odds
            FROM provider_event_timeline
            WHERE canonical_event_id=?
            ORDER BY COALESCE(observed_at, ''), COALESCE(minute, -1), timeline_type, source_ref
            """,
            (canonical_event_id,),
        )
        timeline_total = int(con.execute("SELECT COUNT(*) FROM provider_event_timeline WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
        links_total = int(con.execute("SELECT COUNT(*) FROM provider_event_links WHERE canonical_event_id=?", (canonical_event_id,)).fetchone()[0])
        counts = table_counts(con)
    finally:
        con.close()

    type_counts = {row["timeline_type"]: row["rows"] for row in timeline_counts}
    market_ids = {row["market_id"] for row in market_counts}
    acceptance = {
        "odds_adapter_ok": bool(odds_report.get("ok")),
        "state_adapter_ok": bool(state_report.get("ok")),
        "provider_links_written": links_total == 2 and len(link_ids) == 2,
        "timeline_rows_written": timeline_total >= 1,
        "timeline_has_match_state": type_counts.get("match_state", 0) >= 1,
        "timeline_has_match_events": type_counts.get("match_event", 0) >= 4,
        "timeline_has_odds_markets": type_counts.get("odds_market", 0) >= 14,
        "mapped_markets_present": "football_1x2_regulation" in market_ids and "football_total_goals_regulation" in market_ids,
        "unknown_market_visible": len(unknown_markets) >= 1,
        "no_network": odds_report["safety"]["no_network"] and state_report["safety"]["no_network"],
        "no_api_key": odds_report["safety"]["no_api_key"] and state_report["safety"]["no_api_key"],
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v37_offline_provider_event_timeline_join",
        "canonical_event_id": canonical_event_id,
        "db": str(db),
        "odds_adapter_summary": {
            "raw_snapshots_inserted": odds_report.get("raw_snapshots_inserted"),
            "bookmakers_seen": odds_report.get("bookmakers_seen"),
            "markets_seen": odds_report.get("markets_seen"),
        },
        "state_adapter_summary": state_report.get("coverage"),
        "provider_event_link_ids": link_ids,
        "timeline_inserted_by_type": inserted_by_type,
        "timeline_counts": timeline_counts,
        "market_counts": market_counts,
        "unknown_markets": unknown_markets,
        "compact_timeline": compact_timeline,
        "warehouse_counts": counts,
        "acceptance": acceptance,
        "safety": {
            "offline_samples_only": True,
            "no_api_keys": True,
            "no_network": True,
            "no_website_automation": True,
            "no_betting_output": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v37 offline provider event timeline join smoke.")
    ap.add_argument("--db", default="../build/omnibet_v37_provider_event_timeline.sqlite")
    ap.add_argument("--odds-input", default="../data/samples/the_odds_api_event_markets_sample.json")
    ap.add_argument("--state-input", default="../data/samples/api_football_live_state_sample.json")
    ap.add_argument("--link-input", default="../data/samples/provider_event_link_sample.v37.json")
    ap.add_argument("--out", default="../reports/ci_v37_provider_event_timeline.json")
    args = ap.parse_args()
    report = build_report(Path(args.db), Path(args.odds_input), Path(args.state_input), Path(args.link_input))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
