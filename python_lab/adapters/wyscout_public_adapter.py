#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .warehouse import connect, finish_run, register_default_sources, start_run, store_bronze

SOURCE_ID = "wyscout_public_events"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def clean_name(v: Any) -> str:
    return str(v or "").strip()


def match_date(v: str) -> str:
    v = str(v or "")
    return v[:10] if len(v) >= 10 else v


def minute_second(period: Any, event_sec: Any) -> Tuple[int, int, str]:
    sec = float(event_sec or 0.0)
    p = str(period or "").upper()
    base = 0
    label = "1"
    if p == "2H":
        base, label = 45 * 60, "2"
    elif p == "E1":
        base, label = 90 * 60, "3"
    elif p == "E2":
        base, label = 105 * 60, "4"
    elif p in {"P", "PEN"}:
        base, label = 120 * 60, "5"
    total = int(base + sec)
    return total // 60, total % 60, label


def xy(positions: Any) -> Tuple[Optional[float], Optional[float]]:
    if isinstance(positions, list) and positions:
        p = positions[0]
        if isinstance(p, dict):
            return p.get("x"), p.get("y")
    return None, None


def import_wyscout(db_path: Path, matches_path: Path, events_path: Path) -> dict:
    matches = read_json(matches_path)
    events = read_json(events_path)
    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    inserted_matches = 0
    inserted_events = 0
    try:
        store_bronze(con, SOURCE_ID, "wyscout_matches_file", matches, entity_id=str(matches_path), metadata={"input": str(matches_path)})
        store_bronze(con, SOURCE_ID, "wyscout_events_file", events, entity_id=str(events_path), metadata={"input": str(events_path)})
        match_team_names: Dict[int, Dict[int, str]] = {}
        for m in matches:
            mid_raw = int(m.get("wyId"))
            teams = m.get("teamsData") or {}
            home = away = ""
            home_score = away_score = None
            home_tid = away_tid = None
            team_names = {}
            for _, td in teams.items():
                tid = int(td.get("teamId"))
                name = clean_name((td.get("team") or {}).get("name") or td.get("name"))
                side = clean_name(td.get("side")).lower()
                team_names[tid] = name
                if side == "home":
                    home, home_tid, home_score = name, tid, td.get("score")
                elif side == "away":
                    away, away_tid, away_score = name, tid, td.get("score")
            match_team_names[mid_raw] = team_names
            comp = f"wyscout:{m.get('competitionId', 'unknown')}"
            season = f"{comp}:{m.get('seasonId', 'unknown')}"
            con.execute("INSERT OR REPLACE INTO competitions(competition_id, source_id, sport, name, country, raw_json) VALUES (?, ?, 'football', ?, NULL, ?)", (comp, SOURCE_ID, comp, json.dumps({"competitionId": m.get("competitionId")}, ensure_ascii=False)))
            con.execute("INSERT OR REPLACE INTO seasons(season_id, competition_id, name, start_date, end_date, is_current, raw_json) VALUES (?, ?, ?, NULL, NULL, 0, ?)", (season, comp, str(m.get("seasonId", "unknown")), json.dumps({"seasonId": m.get("seasonId")}, ensure_ascii=False)))
            for tid, name in [(home_tid, home), (away_tid, away)]:
                if tid is None:
                    continue
                con.execute("INSERT OR REPLACE INTO teams(team_id, source_id, sport, name, country, raw_json) VALUES (?, ?, 'football', ?, NULL, ?)", (f"wyscout:{tid}", SOURCE_ID, name, json.dumps({"teamId": tid, "name": name}, ensure_ascii=False)))
            con.execute(
                """INSERT OR REPLACE INTO matches_norm
                   (match_id, source_id, sport, competition_id, season_id, match_date, status,
                    home_team_id, away_team_id, home_team_name, away_team_name, home_score, away_score, raw_json)
                   VALUES (?, ?, 'football', ?, ?, ?, 'finished', ?, ?, ?, ?, ?, ?, ?)""",
                (f"wyscout:{mid_raw}", SOURCE_ID, comp, season, match_date(m.get("dateutc")), f"wyscout:{home_tid}", f"wyscout:{away_tid}", home, away, home_score, away_score, json.dumps(m, ensure_ascii=False)),
            )
            inserted_matches += 1

        for ev in events:
            mid_raw = int(ev.get("matchId"))
            minute, second, period = minute_second(ev.get("matchPeriod"), ev.get("eventSec"))
            x, y = xy(ev.get("positions"))
            tid = ev.get("teamId")
            pid = ev.get("playerId")
            event_type = clean_name(ev.get("eventName")) or clean_name(ev.get("subEventName"))
            outcome = clean_name(ev.get("subEventName")) or None
            con.execute(
                """INSERT OR REPLACE INTO match_events
                   (event_id, match_id, source_id, event_type, minute, second, period, team_id, player_id,
                    related_player_id, x, y, outcome, xg, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, ?, ?, ?, NULL, ?)""",
                (f"wyscout:{ev.get('id')}", f"wyscout:{mid_raw}", SOURCE_ID, event_type, minute, second, period, f"wyscout:{tid}" if tid is not None else None, f"wyscout:{pid}" if pid is not None else None, x, y, outcome, json.dumps(ev, ensure_ascii=False)),
            )
            inserted_events += 1
        con.commit()
        finish_run(con, run_id, "success", rows_seen=len(matches) + len(events), rows_inserted=inserted_matches + inserted_events, report={"matches": inserted_matches, "events": inserted_events})
        return {"run_id": run_id, "source_id": SOURCE_ID, "matches_inserted": inserted_matches, "events_inserted": inserted_events}
    except Exception as e:
        finish_run(con, run_id, "error", rows_seen=len(matches) + len(events), rows_inserted=inserted_matches + inserted_events, error=str(e))
        raise
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Import Wyscout-style public event JSON into OmniBet warehouse.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--matches", required=True)
    ap.add_argument("--events", required=True)
    args = ap.parse_args()
    print(json.dumps(import_wyscout(Path(args.db), Path(args.matches), Path(args.events)), indent=2))


if __name__ == "__main__":
    main()
