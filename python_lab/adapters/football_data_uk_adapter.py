#!/usr/bin/env python3
"""
Football-Data.co.uk CSV adapter for OmniBet Lab v4.

Purpose:
- Import local or URL CSV files from Football-Data style datasets.
- Preserve each row in bronze.
- Normalize common columns into matches_norm and odds_snapshots where possible.

This adapter is usable without an API key. Network URL download uses urllib from
the Python standard library.
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from .warehouse import connect, finish_run, register_default_sources, start_run, store_bronze


SOURCE_ID = "football_data_uk_csv"


def read_text(path_or_url: str) -> str:
    if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
        with urllib.request.urlopen(path_or_url, timeout=45) as r:
            return r.read().decode("utf-8-sig", errors="replace")
    return Path(path_or_url).read_text(encoding="utf-8-sig")


def first(row: dict, *keys: str):
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return v
    return None


def parse_int(v):
    try:
        if v in (None, ""):
            return None
        return int(float(v))
    except Exception:
        return None


def parse_float(v):
    try:
        if v in (None, ""):
            return None
        return float(v)
    except Exception:
        return None


def normalize_date(v: str) -> str:
    # Football-Data often uses DD/MM/YYYY; keep ISO when already ISO.
    if not v:
        return ""
    v = str(v).strip()
    if "-" in v and len(v[:10]) == 10:
        return v[:10]
    if "/" in v:
        parts = v.split("/")
        if len(parts) == 3:
            d, m, y = parts
            if len(y) == 2:
                y = "20" + y
            return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"
    return v


def import_csv(db_path: Path, input_path: str, competition_hint: str = "", season_hint: str = "") -> dict:
    text = read_text(input_path)
    reader = csv.DictReader(io.StringIO(text))
    rows = list(reader)

    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    inserted_matches = 0
    inserted_odds = 0

    try:
        for idx, row in enumerate(rows):
            div = first(row, "Div", "league", "League") or competition_hint
            date = normalize_date(first(row, "Date", "date") or "")
            home = first(row, "HomeTeam", "home_team", "Home") or ""
            away = first(row, "AwayTeam", "away_team", "Away") or ""
            if not date or not home or not away:
                continue
            match_id = f"fdc:{div}:{date}:{home}:{away}:{idx}".replace(" ", "_")
            payload_id = f"{match_id}:raw"
            store_bronze(con, SOURCE_ID, "football_data_uk_row", row, entity_id=payload_id, metadata={"input": input_path})

            hg = parse_int(first(row, "FTHG", "HG", "home_goals"))
            ag = parse_int(first(row, "FTAG", "AG", "away_goals"))
            status = "finished" if hg is not None and ag is not None else "scheduled"

            con.execute(
                """INSERT OR REPLACE INTO matches_norm
                   (match_id, source_id, sport, competition_id, season_id, match_date, status,
                    home_team_name, away_team_name, home_score, away_score, raw_json)
                   VALUES (?, ?, 'football', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (match_id, SOURCE_ID, div, season_hint, date, status, home, away, hg, ag, json.dumps(row, ensure_ascii=False)),
            )
            inserted_matches += 1

            # Common Football-Data odds columns. Store if present.
            odds_cols = [
                ("B365H", "1x2", "home", "Bet365"),
                ("B365D", "1x2", "draw", "Bet365"),
                ("B365A", "1x2", "away", "Bet365"),
                ("PSH", "1x2", "home", "Pinnacle/PS"),
                ("PSD", "1x2", "draw", "Pinnacle/PS"),
                ("PSA", "1x2", "away", "Pinnacle/PS"),
                ("MaxH", "1x2", "home", "Max"),
                ("MaxD", "1x2", "draw", "Max"),
                ("MaxA", "1x2", "away", "Max"),
                ("AvgH", "1x2", "home", "Average"),
                ("AvgD", "1x2", "draw", "Average"),
                ("AvgA", "1x2", "away", "Average"),
                ("B365>2.5", "total_goals", "over_2.5", "Bet365"),
                ("B365<2.5", "total_goals", "under_2.5", "Bet365"),
                ("P>2.5", "total_goals", "over_2.5", "Pinnacle/PS"),
                ("P<2.5", "total_goals", "under_2.5", "Pinnacle/PS"),
            ]
            for col, market, selection, bookmaker in odds_cols:
                od = parse_float(row.get(col))
                if od is None:
                    continue
                odds_id = f"{match_id}:{bookmaker}:{market}:{selection}:{col}".replace(" ", "_")
                con.execute(
                    """INSERT OR REPLACE INTO odds_snapshots
                       (odds_id, source_id, match_id, bookmaker, market_id, selection, line, odds_decimal, captured_at, is_live, raw_json)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)""",
                    (odds_id, SOURCE_ID, match_id, bookmaker, f"football.{market}", selection, 2.5 if "2.5" in selection else None, od, date, json.dumps({col: row.get(col)}, ensure_ascii=False)),
                )
                inserted_odds += 1

        con.commit()
        finish_run(con, run_id, "success", rows_seen=len(rows), rows_inserted=inserted_matches, rows_updated=inserted_odds, report={"input": input_path, "matches": inserted_matches, "odds": inserted_odds})
        return {"run_id": run_id, "input": input_path, "rows_seen": len(rows), "matches_inserted": inserted_matches, "odds_inserted": inserted_odds}
    except Exception as e:
        finish_run(con, run_id, "error", rows_seen=len(rows), rows_inserted=inserted_matches, rows_updated=inserted_odds, error=str(e))
        raise
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="Import Football-Data.co.uk style CSV.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--input", required=True, help="Local CSV path or URL.")
    ap.add_argument("--competition", default="")
    ap.add_argument("--season", default="")
    args = ap.parse_args()
    print(json.dumps(import_csv(Path(args.db), args.input, args.competition, args.season), indent=2))


if __name__ == "__main__":
    main()
