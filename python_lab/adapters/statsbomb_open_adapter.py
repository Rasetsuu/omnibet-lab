#!/usr/bin/env python3
"""
StatsBomb Open Data adapter for OmniBet Lab v4.

Usage:
  git clone https://github.com/statsbomb/open-data path/to/open-data
  python -m adapters.statsbomb_open_adapter import --root path/to/open-data/data --db ../build/omnibet.sqlite --limit-matches 50

This adapter expects the standard open-data/data layout:
- competitions.json
- matches/{competition_id}/{season_id}.json
- events/{match_id}.json
- lineups/{match_id}.json

It preserves raw JSON in bronze and normalizes competitions, seasons, matches,
events and lineups where possible.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .warehouse import connect, finish_run, register_default_sources, start_run, store_bronze


SOURCE_ID = "statsbomb_open_data"


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def jget(obj, *keys, default=None):
    cur = obj
    for k in keys:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur


def import_competitions(con, root: Path) -> int:
    p = root / "competitions.json"
    if not p.exists():
        return 0
    comps = read_json(p)
    store_bronze(con, SOURCE_ID, "competitions_file", comps, entity_id="competitions")
    count = 0
    for c in comps:
        comp_id = str(c.get("competition_id"))
        season_id = f"statsbomb:{comp_id}:{c.get('season_id')}"
        con.execute(
            """INSERT OR REPLACE INTO competitions
               (competition_id, source_id, sport, name, country, raw_json)
               VALUES (?, ?, 'football', ?, ?, ?)""",
            (f"statsbomb:{comp_id}", SOURCE_ID, c.get("competition_name") or "", c.get("country_name"), json.dumps(c, ensure_ascii=False)),
        )
        con.execute(
            """INSERT OR REPLACE INTO seasons
               (season_id, competition_id, name, start_date, end_date, is_current, raw_json)
               VALUES (?, ?, ?, NULL, NULL, 0, ?)""",
            (season_id, f"statsbomb:{comp_id}", c.get("season_name") or str(c.get("season_id")), json.dumps(c, ensure_ascii=False)),
        )
        count += 1
    return count


def import_matches(con, root: Path, limit_matches: Optional[int] = None) -> int:
    matches_root = root / "matches"
    if not matches_root.exists():
        return 0
    count = 0
    for path in sorted(matches_root.glob("*/*.json")):
        try:
            comp_id = path.parent.name
            season_raw = path.stem
            matches = read_json(path)
            store_bronze(con, SOURCE_ID, "matches_file", matches, entity_id=f"{comp_id}:{season_raw}")
            for m in matches:
                mid = f"statsbomb:{m.get('match_id')}"
                home = jget(m, "home_team", "home_team_name", default="")
                away = jget(m, "away_team", "away_team_name", default="")
                htid = str(jget(m, "home_team", "home_team_id", default=""))
                atid = str(jget(m, "away_team", "away_team_id", default=""))
                home_score = m.get("home_score")
                away_score = m.get("away_score")
                con.execute(
                    """INSERT OR REPLACE INTO teams(team_id, source_id, sport, name, country, raw_json)
                       VALUES (?, ?, 'football', ?, NULL, ?)""",
                    (f"statsbomb:{htid}", SOURCE_ID, home, json.dumps(m.get("home_team") or {}, ensure_ascii=False)),
                )
                con.execute(
                    """INSERT OR REPLACE INTO teams(team_id, source_id, sport, name, country, raw_json)
                       VALUES (?, ?, 'football', ?, NULL, ?)""",
                    (f"statsbomb:{atid}", SOURCE_ID, away, json.dumps(m.get("away_team") or {}, ensure_ascii=False)),
                )
                con.execute(
                    """INSERT OR REPLACE INTO matches_norm
                       (match_id, source_id, sport, competition_id, season_id, match_date, status,
                        home_team_id, away_team_id, home_team_name, away_team_name, home_score, away_score, venue, raw_json)
                       VALUES (?, ?, 'football', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        mid, SOURCE_ID, f"statsbomb:{comp_id}", f"statsbomb:{comp_id}:{season_raw}",
                        m.get("match_date"), "finished", f"statsbomb:{htid}", f"statsbomb:{atid}",
                        home, away, home_score, away_score, jget(m, "stadium", "name", default=None),
                        json.dumps(m, ensure_ascii=False),
                    ),
                )
                count += 1
                if limit_matches and count >= limit_matches:
                    return count
        except Exception:
            # continue across bad files; raw imports should be robust
            continue
    return count


def import_events(con, root: Path, limit_matches: Optional[int] = None) -> int:
    events_root = root / "events"
    if not events_root.exists():
        return 0
    count = 0
    match_files = sorted(events_root.glob("*.json"))
    if limit_matches:
        match_files = match_files[:limit_matches]
    for path in match_files:
        match_id = f"statsbomb:{path.stem}"
        events = read_json(path)
        store_bronze(con, SOURCE_ID, "events_file", events, entity_id=path.stem)
        for ev in events:
            eid = f"statsbomb:{ev.get('id')}"
            event_type = jget(ev, "type", "name", default="")
            player_id = jget(ev, "player", "id", default=None)
            team_id = jget(ev, "team", "id", default=None)
            loc = ev.get("location") if isinstance(ev.get("location"), list) else [None, None]
            shot = ev.get("shot") if isinstance(ev.get("shot"), dict) else {}
            xg = shot.get("statsbomb_xg")
            outcome = jget(shot, "outcome", "name", default=None) or jget(ev.get("pass") or {}, "outcome", "name", default=None)
            con.execute(
                """INSERT OR REPLACE INTO match_events
                   (event_id, match_id, source_id, event_type, minute, second, period, team_id, player_id,
                    related_player_id, x, y, outcome, xg, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    eid, match_id, SOURCE_ID, event_type, ev.get("minute"), ev.get("second"),
                    jget(ev, "period", "name", default=str(ev.get("period"))),
                    f"statsbomb:{team_id}" if team_id is not None else None,
                    f"statsbomb:{player_id}" if player_id is not None else None,
                    None,
                    loc[0] if len(loc) > 0 else None, loc[1] if len(loc) > 1 else None,
                    outcome, xg, json.dumps(ev, ensure_ascii=False),
                ),
            )
            count += 1
    return count


def import_lineups(con, root: Path, limit_matches: Optional[int] = None) -> int:
    lineups_root = root / "lineups"
    if not lineups_root.exists():
        return 0
    count = 0
    files = sorted(lineups_root.glob("*.json"))
    if limit_matches:
        files = files[:limit_matches]
    for path in files:
        match_id = f"statsbomb:{path.stem}"
        teams = read_json(path)
        store_bronze(con, SOURCE_ID, "lineups_file", teams, entity_id=path.stem)
        for team in teams:
            team_id = f"statsbomb:{team.get('team_id')}"
            for player in team.get("lineup", []) or []:
                pid = f"statsbomb:{player.get('player_id')}"
                pname = player.get("player_name") or ""
                pos = None
                if player.get("positions"):
                    pos = player["positions"][0].get("position")
                con.execute(
                    """INSERT OR REPLACE INTO players(player_id, source_id, sport, name, nationality, birth_date, position, current_team_id, raw_json)
                       VALUES (?, ?, 'football', ?, NULL, NULL, ?, ?, ?)""",
                    (pid, SOURCE_ID, pname, pos, team_id, json.dumps(player, ensure_ascii=False)),
                )
                lid = f"{match_id}:{team_id}:{pid}"
                con.execute(
                    """INSERT OR REPLACE INTO lineups
                       (lineup_id, match_id, team_id, player_id, player_name, started, position, shirt_number, minutes_played, raw_json)
                       VALUES (?, ?, ?, ?, ?, NULL, ?, ?, NULL, ?)""",
                    (lid, match_id, team_id, pid, pname, pos, player.get("jersey_number"), json.dumps(player, ensure_ascii=False)),
                )
                count += 1
    return count


def import_all(db_path: Path, root: Path, limit_matches: Optional[int] = None, include_events: bool = True) -> dict:
    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    try:
        comps = import_competitions(con, root)
        matches = import_matches(con, root, limit_matches=limit_matches)
        lineups = import_lineups(con, root, limit_matches=limit_matches)
        events = import_events(con, root, limit_matches=limit_matches) if include_events else 0
        con.commit()
        report = {"root": str(root), "competitions": comps, "matches": matches, "lineups": lineups, "events": events}
        finish_run(con, run_id, "success", rows_seen=comps + matches + lineups + events, rows_inserted=comps + matches + lineups + events, report=report)
        return {"run_id": run_id, **report}
    except Exception as e:
        finish_run(con, run_id, "error", error=str(e), report={"root": str(root)})
        raise
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Import StatsBomb open-data JSON.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("import")
    p.add_argument("--db", default="../build/omnibet.sqlite")
    p.add_argument("--root", required=True, help="Path to open-data/data")
    p.add_argument("--limit-matches", type=int, default=None)
    p.add_argument("--no-events", action="store_true")
    args = ap.parse_args()
    print(json.dumps(import_all(Path(args.db), Path(args.root), args.limit_matches, include_events=not args.no_events), indent=2))


if __name__ == "__main__":
    main()
