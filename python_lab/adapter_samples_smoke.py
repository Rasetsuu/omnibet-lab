#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def slug(value: str) -> str:
    return value.lower().replace(" ", "-").replace("/", "-")


def label_from_score(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "home_win"
    if home_score < away_score:
        return "away_win"
    return "draw"


def load_csv_match_rows(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    fixtures: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fixture_id = f"csv-{slug(row['HomeTeam'])}-{slug(row['AwayTeam'])}-{row['Date']}"
            kickoff = f"{row['Date']}T00:00:00Z"
            home_score = int(row["FTHG"])
            away_score = int(row["FTAG"])
            fixtures.append({
                "source_id": "csv_match_sample",
                "fixture_id": fixture_id,
                "kickoff_utc": kickoff,
                "home_name": row["HomeTeam"],
                "away_name": row["AwayTeam"],
            })
            results.append({
                "source_id": "csv_match_sample",
                "fixture_id": fixture_id,
                "home_score": home_score,
                "away_score": away_score,
                "result_label": label_from_score(home_score, away_score),
                "label_available_after_utc": f"{row['Date']}T23:59:00Z",
                "total_goals": home_score + away_score,
            })
    return {"fixtures": fixtures, "results": results}


def load_json_match_rows(path: Path) -> Dict[str, List[Dict[str, Any]]]:
    payload = read_json(path)
    fixtures: List[Dict[str, Any]] = []
    results: List[Dict[str, Any]] = []
    for row in payload.get("matches", []):
        fixture_id = f"json-{slug(row['team1'])}-{slug(row['team2'])}-{row['date']}"
        home_score, away_score = row["score"]["ft"]
        fixtures.append({
            "source_id": "json_match_sample",
            "fixture_id": fixture_id,
            "kickoff_utc": f"{row['date']}T00:00:00Z",
            "home_name": row["team1"],
            "away_name": row["team2"],
            "round": row.get("round"),
        })
        results.append({
            "source_id": "json_match_sample",
            "fixture_id": fixture_id,
            "home_score": home_score,
            "away_score": away_score,
            "result_label": label_from_score(home_score, away_score),
            "label_available_after_utc": f"{row['date']}T23:59:00Z",
            "total_goals": home_score + away_score,
        })
    return {"fixtures": fixtures, "results": results}


def load_event_rows(path: Path) -> List[Dict[str, Any]]:
    payload = read_json(path)
    rows: List[Dict[str, Any]] = []
    for event in payload.get("events", []):
        rows.append({
            "source_id": "json_event_sample",
            "fixture_id": event["fixture_id"],
            "event_type": event.get("type", {}).get("name"),
            "team_name": event.get("team"),
            "minute": event.get("minute"),
            "player_name": event.get("player", {}).get("name"),
        })
    return rows


def build_report(root: Path) -> Dict[str, Any]:
    cfg = read_json(root / "configs/adapter_samples.v591_v620.json")
    inputs = cfg["inputs"]
    csv_rows = load_csv_match_rows(root / inputs["csv_match_sample"])
    json_rows = load_json_match_rows(root / inputs["json_match_sample"])
    event_rows = load_event_rows(root / inputs["json_event_sample"])
    fixtures = csv_rows["fixtures"] + json_rows["fixtures"]
    results = csv_rows["results"] + json_rows["results"]
    pack = {
        "schema": "omnibet.normalized_historical_pack.v591_v620",
        "ready_for_real_model": False,
        "source_policy": {
            "ci_downloads_allowed": False,
            "local_samples_only": True,
        },
        "counts": {
            "fixtures": len(fixtures),
            "results": len(results),
            "events": len(event_rows),
            "ratings": 0,
        },
        "fixtures": fixtures,
        "results": results,
        "events": event_rows,
        "gap_report": {
            "ratings": "future_slot",
            "corners_cards_free_kicks": "needs richer event data",
            "player_markets": "needs lineups and player event coverage",
        },
    }
    write_json(root / cfg["outputs"]["normalized_pack"], pack)
    checks = {
        "schema": cfg.get("schema") == "omnibet.adapter_samples_contract.v591_v620",
        "csv_fixture_rows": len(csv_rows["fixtures"]) == 3,
        "json_fixture_rows": len(json_rows["fixtures"]) == 3,
        "event_rows": len(event_rows) == 4,
        "result_rows": len(results) == 6,
        "normalized_pack_written": pack["counts"]["fixtures"] == 6,
        "no_ci_downloads": cfg.get("ci_downloads_allowed") is False,
        "ready_for_real_model_false": pack["ready_for_real_model"] is False,
    }
    return {"ok": all(checks.values()), "schema": "omnibet.adapter_samples_smoke.v591_v620", "acceptance": checks, "counts": pack["counts"]}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v591_v620_adapter_samples.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
