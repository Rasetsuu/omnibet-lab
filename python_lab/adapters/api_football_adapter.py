#!/usr/bin/env python3
"""Offline API-Football-style adapter.

This adapter is intentionally network-free. It consumes local sample JSON shaped
like API-Football fixture responses and writes normalized match state, teams,
players, lineups, and events to OmniBet's warehouse.
"""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from adapters.warehouse import connect, register_default_sources, sha_text, store_bronze

SOURCE_ID = "api_football_offline_sample"


def load_payload(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def rows(con: sqlite3.Connection, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    cur = con.execute(sql, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def team_id(raw_team_id: Any) -> str:
    return f"api_football_team:{raw_team_id}"


def player_id(raw_player_id: Any) -> Optional[str]:
    if raw_player_id is None:
        return None
    return f"api_football_player:{raw_player_id}"


def match_id(raw_fixture_id: Any) -> str:
    return f"api_football_fixture:{raw_fixture_id}"


def event_id(raw_fixture_id: Any, idx: int, event: Dict[str, Any]) -> str:
    player = event.get("player") or {}
    return f"api_football_event:{raw_fixture_id}:{idx}:{event.get('type', 'event')}:{player.get('id', 'none')}"


def insert_team(con: sqlite3.Connection, raw_team: Dict[str, Any]) -> str:
    tid = team_id(raw_team.get("id"))
    con.execute(
        """INSERT OR REPLACE INTO teams
           (team_id, source_id, sport, name, country, raw_json)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (tid, SOURCE_ID, "football", raw_team.get("name") or tid, None, json.dumps(raw_team, ensure_ascii=False, sort_keys=True)),
    )
    return tid


def insert_player(con: sqlite3.Connection, raw_player: Dict[str, Any], current_team_id: Optional[str]) -> Optional[str]:
    pid = player_id(raw_player.get("id"))
    if not pid:
        return None
    con.execute(
        """INSERT OR REPLACE INTO players
           (player_id, source_id, sport, name, nationality, birth_date, position, current_team_id, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            pid,
            SOURCE_ID,
            "football",
            raw_player.get("name") or pid,
            None,
            None,
            raw_player.get("pos"),
            current_team_id,
            json.dumps(raw_player, ensure_ascii=False, sort_keys=True),
        ),
    )
    return pid


def insert_match(con: sqlite3.Connection, fixture_obj: Dict[str, Any]) -> str:
    fixture = fixture_obj["fixture"]
    league = fixture_obj.get("league") or {}
    teams = fixture_obj.get("teams") or {}
    goals = fixture_obj.get("goals") or {}
    home = teams.get("home") or {}
    away = teams.get("away") or {}
    mid = match_id(fixture.get("id"))
    home_tid = insert_team(con, home)
    away_tid = insert_team(con, away)
    competition_id = f"api_football_league:{league.get('id')}" if league.get("id") is not None else None
    season_id = f"api_football_season:{league.get('id')}:{league.get('season')}" if league.get("id") is not None else None
    venue = fixture.get("venue") or {}
    status = fixture.get("status") or {}
    venue_text = ", ".join([str(x) for x in [venue.get("name"), venue.get("city")] if x]) or None
    con.execute(
        """INSERT OR REPLACE INTO matches_norm
           (match_id, source_id, sport, competition_id, season_id, match_date, status,
            home_team_id, away_team_id, home_team_name, away_team_name, home_score, away_score, venue, raw_json)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            mid,
            SOURCE_ID,
            "football",
            competition_id,
            season_id,
            fixture.get("date"),
            status.get("short") or status.get("long"),
            home_tid,
            away_tid,
            home.get("name"),
            away.get("name"),
            goals.get("home"),
            goals.get("away"),
            venue_text,
            json.dumps(fixture_obj, ensure_ascii=False, sort_keys=True),
        ),
    )
    return mid


def insert_lineups(con: sqlite3.Connection, fixture_obj: Dict[str, Any], mid: str) -> int:
    count = 0
    for lineup in fixture_obj.get("lineups", []):
        raw_team = lineup.get("team") or {}
        tid = team_id(raw_team.get("id"))
        insert_team(con, raw_team)
        for started, bucket in [(1, "startXI"), (0, "substitutes")]:
            for item in lineup.get(bucket, []):
                raw_player = item.get("player") or {}
                pid = insert_player(con, raw_player, tid)
                if not pid:
                    continue
                lid = f"api_football_lineup:{mid}:{pid}:{started}"
                con.execute(
                    """INSERT OR REPLACE INTO lineups
                       (lineup_id, match_id, team_id, player_id, player_name, started, position, shirt_number, minutes_played, raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        lid,
                        mid,
                        tid,
                        pid,
                        raw_player.get("name"),
                        started,
                        raw_player.get("pos"),
                        raw_player.get("number"),
                        None,
                        json.dumps({"lineup": lineup, "player": raw_player, "started": bool(started)}, ensure_ascii=False, sort_keys=True),
                    ),
                )
                count += 1
    return count


def event_period(elapsed: Optional[int]) -> str:
    if elapsed is None:
        return "unknown"
    if elapsed <= 45:
        return "first_half"
    if elapsed <= 90:
        return "second_half"
    return "extra_time_or_stoppage"


def insert_events(con: sqlite3.Connection, fixture_obj: Dict[str, Any], mid: str) -> int:
    raw_fixture_id = fixture_obj.get("fixture", {}).get("id")
    count = 0
    for idx, ev in enumerate(fixture_obj.get("events", [])):
        raw_team = ev.get("team") or {}
        raw_player = ev.get("player") or {}
        raw_assist = ev.get("assist") or {}
        tid = team_id(raw_team.get("id")) if raw_team.get("id") is not None else None
        pid = insert_player(con, raw_player, tid) if raw_player.get("id") is not None else None
        aid = insert_player(con, raw_assist, tid) if raw_assist.get("id") is not None else None
        time = ev.get("time") or {}
        elapsed = time.get("elapsed")
        eid = event_id(raw_fixture_id, idx, ev)
        con.execute(
            """INSERT OR REPLACE INTO match_events
               (event_id, match_id, source_id, event_type, minute, second, period, team_id, player_id,
                related_player_id, x, y, outcome, xg, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                eid,
                mid,
                SOURCE_ID,
                ev.get("type"),
                elapsed,
                None,
                event_period(elapsed),
                tid,
                pid,
                aid,
                None,
                None,
                ev.get("detail"),
                None,
                json.dumps(ev, ensure_ascii=False, sort_keys=True),
            ),
        )
        count += 1
    return count


def summarize_statistics(fixture_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for team_stats in fixture_obj.get("statistics", []):
        team = team_stats.get("team") or {}
        stats = {}
        for item in team_stats.get("statistics", []):
            stats[item.get("type") or "unknown"] = item.get("value")
        out.append({"team_id": team_id(team.get("id")), "team_name": team.get("name"), "stats": stats})
    return out


def import_offline_live_state(db_path: Path, input_path: Path) -> Dict[str, Any]:
    payload = load_payload(input_path)
    con = connect(db_path)
    try:
        register_default_sources(con)
        store_bronze(con, SOURCE_ID, "api_football_fixture_payload", payload, entity_id=str(payload.get("parameters", {}).get("id", "sample")), metadata={"offline_sample": True})
        matches_inserted = 0
        lineups_inserted = 0
        events_inserted = 0
        stats_summary: List[Dict[str, Any]] = []
        for fixture_obj in payload.get("response", []):
            mid = insert_match(con, fixture_obj)
            matches_inserted += 1
            lineups_inserted += insert_lineups(con, fixture_obj, mid)
            events_inserted += insert_events(con, fixture_obj, mid)
            stats_summary.extend(summarize_statistics(fixture_obj))
        con.commit()
        coverage = {
            "payload_results": payload.get("results"),
            "matches_inserted": matches_inserted,
            "lineups_inserted": lineups_inserted,
            "events_inserted": events_inserted,
            "statistics_team_rows": len(stats_summary),
            "statistics_summary": stats_summary,
        }
        db_counts = {
            "teams": int(con.execute("SELECT COUNT(*) FROM teams WHERE source_id=?", (SOURCE_ID,)).fetchone()[0]),
            "players": int(con.execute("SELECT COUNT(*) FROM players WHERE source_id=?", (SOURCE_ID,)).fetchone()[0]),
            "matches_norm": int(con.execute("SELECT COUNT(*) FROM matches_norm WHERE source_id=?", (SOURCE_ID,)).fetchone()[0]),
            "match_events": int(con.execute("SELECT COUNT(*) FROM match_events WHERE source_id=?", (SOURCE_ID,)).fetchone()[0]),
            "lineups": int(con.execute("SELECT COUNT(*) FROM lineups WHERE match_id LIKE 'api_football_fixture:%'").fetchone()[0]),
            "bronze_blobs": int(con.execute("SELECT COUNT(*) FROM bronze_blobs WHERE source_id=?", (SOURCE_ID,)).fetchone()[0]),
        }
        imported_matches = rows(con, "SELECT match_id, home_team_name, away_team_name, home_score, away_score, status FROM matches_norm WHERE source_id=? ORDER BY match_id", (SOURCE_ID,))
        imported_events = rows(con, "SELECT event_type, minute, team_id, player_id, outcome FROM match_events WHERE source_id=? ORDER BY minute, event_id", (SOURCE_ID,))
    finally:
        con.close()
    return {
        "ok": True,
        "provider_id": SOURCE_ID,
        "input_path": str(input_path),
        "db_path": str(db_path),
        "coverage": coverage,
        "db_counts": db_counts,
        "imported_matches": imported_matches,
        "imported_events": imported_events,
        "safety": {
            "offline_sample_only": True,
            "no_api_key": True,
            "no_network": True,
            "no_website_automation": True,
            "no_betting_output": True,
        },
    }
