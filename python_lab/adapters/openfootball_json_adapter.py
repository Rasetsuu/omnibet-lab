#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .warehouse import connect, finish_run, register_default_sources, start_run, store_bronze

SOURCE_ID = "openfootball_json"


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def team_id(name: str) -> str:
    return "openfootball:" + name.strip().lower().replace(" ", "_")


def parse_score(obj: Any) -> Tuple[Optional[int], Optional[int]]:
    if isinstance(obj, dict):
        ft = obj.get("ft") or obj.get("fulltime") or obj.get("full_time")
        if isinstance(ft, list) and len(ft) >= 2:
            return int(ft[0]), int(ft[1])
    if isinstance(obj, list) and len(obj) >= 2:
        return int(obj[0]), int(obj[1])
    return None, None


def import_file(db_path: Path, input_path: Path, competition_hint: str = "", season_hint: str = "") -> dict:
    payload = read_json(input_path)
    matches = payload.get("matches", []) if isinstance(payload, dict) else payload
    competition = competition_hint or (payload.get("competition") if isinstance(payload, dict) else None) or "openfootball_sample"
    season = season_hint or (payload.get("season") if isinstance(payload, dict) else None) or "unknown"

    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    inserted = 0
    try:
        store_bronze(con, SOURCE_ID, "openfootball_file", payload, entity_id=str(input_path), metadata={"input": str(input_path)})
        con.execute(
            """INSERT OR REPLACE INTO competitions(competition_id, source_id, sport, name, country, raw_json)
               VALUES (?, ?, 'football', ?, NULL, ?)""",
            (f"openfootball:{competition}", SOURCE_ID, competition, json.dumps({"competition": competition}, ensure_ascii=False)),
        )
        con.execute(
            """INSERT OR REPLACE INTO seasons(season_id, competition_id, name, start_date, end_date, is_current, raw_json)
               VALUES (?, ?, ?, NULL, NULL, 0, ?)""",
            (f"openfootball:{competition}:{season}", f"openfootball:{competition}", season, json.dumps({"season": season}, ensure_ascii=False)),
        )
        for idx, m in enumerate(matches):
            home = m.get("team1") or m.get("home") or m.get("home_team") or ""
            away = m.get("team2") or m.get("away") or m.get("away_team") or ""
            date = m.get("date") or m.get("match_date") or ""
            if not home or not away or not date:
                continue
            hg, ag = parse_score(m.get("score"))
            hid, aid = team_id(home), team_id(away)
            mid = f"openfootball:{competition}:{season}:{date}:{home}:{away}:{idx}".replace(" ", "_")
            for tid, name in [(hid, home), (aid, away)]:
                con.execute(
                    """INSERT OR REPLACE INTO teams(team_id, source_id, sport, name, country, raw_json)
                       VALUES (?, ?, 'football', ?, NULL, ?)""",
                    (tid, SOURCE_ID, name, json.dumps({"name": name}, ensure_ascii=False)),
                )
            con.execute(
                """INSERT OR REPLACE INTO matches_norm
                   (match_id, source_id, sport, competition_id, season_id, match_date, status,
                    home_team_id, away_team_id, home_team_name, away_team_name, home_score, away_score, raw_json)
                   VALUES (?, ?, 'football', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    mid, SOURCE_ID, f"openfootball:{competition}", f"openfootball:{competition}:{season}", date,
                    "finished" if hg is not None and ag is not None else "scheduled",
                    hid, aid, home, away, hg, ag, json.dumps(m, ensure_ascii=False),
                ),
            )
            inserted += 1
        con.commit()
        finish_run(con, run_id, "success", rows_seen=len(matches), rows_inserted=inserted, report={"input": str(input_path), "matches": inserted})
        return {"run_id": run_id, "source_id": SOURCE_ID, "input": str(input_path), "matches_inserted": inserted}
    except Exception as e:
        finish_run(con, run_id, "error", rows_seen=len(matches), rows_inserted=inserted, error=str(e))
        raise
    finally:
        con.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Import OpenFootball-style JSON into OmniBet warehouse.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--input", required=True)
    ap.add_argument("--competition", default="")
    ap.add_argument("--season", default="")
    args = ap.parse_args()
    print(json.dumps(import_file(Path(args.db), Path(args.input), args.competition, args.season), indent=2))


if __name__ == "__main__":
    main()
