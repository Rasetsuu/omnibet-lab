#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import urllib.request
from pathlib import Path
from typing import Any, List

from adapters.statsbomb_open_adapter import import_all
from adapters.warehouse import connect, register_default_sources, table_counts
from export_data_pack import DEFAULT_TABLES, export_pack
from gold_feature_builder import build_gold
from goal_timing_lab import analyze as analyze_goal_timing
from player_score_lab import build_player_scores

DEFAULT_RAW_BASE = "https://" + "raw.githubusercontent.com" + "/statsbomb/open-data/master/data"


def fetch_json(url: str) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "omnibet-lab-ci"})
    with urllib.request.urlopen(req, timeout=45) as resp:
        return json.loads(resp.read().decode("utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def materialize_sample(root: Path, raw_base: str, competition_id: int, season_id: int, limit_matches: int) -> dict:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    competitions = fetch_json(f"{raw_base}/competitions.json")
    matches_all = fetch_json(f"{raw_base}/matches/{competition_id}/{season_id}.json")
    selected_matches = matches_all[:limit_matches]
    match_ids: List[int] = [int(m["match_id"]) for m in selected_matches]
    selected_competitions = [
        c for c in competitions
        if int(c.get("competition_id", -1)) == competition_id and int(c.get("season_id", -1)) == season_id
    ] or competitions[:1]

    write_json(root / "competitions.json", selected_competitions)
    write_json(root / "matches" / str(competition_id) / f"{season_id}.json", selected_matches)
    for mid in match_ids:
        write_json(root / "events" / f"{mid}.json", fetch_json(f"{raw_base}/events/{mid}.json"))
        write_json(root / "lineups" / f"{mid}.json", fetch_json(f"{raw_base}/lineups/{mid}.json"))
    return {"root": str(root), "selected_match_ids": match_ids, "matches_file_rows": len(selected_matches)}


def run(sample_root: Path, db_path: Path, pack_dir: Path, reports_dir: Path, raw_base: str, competition_id: int, season_id: int, limit_matches: int) -> dict:
    reports_dir.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()
    sample = materialize_sample(sample_root, raw_base, competition_id, season_id, limit_matches)

    con = connect(db_path)
    register_default_sources(con)
    before_counts = table_counts(con)
    con.close()

    imported = import_all(db_path, sample_root, limit_matches=limit_matches, include_events=True)
    gold = build_gold(db_path, rolling_n=10, reset=True)
    timing = analyze_goal_timing(db_path)
    player = build_player_scores(db_path)
    pack = export_pack(db_path, pack_dir, DEFAULT_TABLES, sport="football", pack_name="football_statsbomb_sample_v1")

    con = connect(db_path)
    after_counts = table_counts(con)
    con.close()

    required_positive = {
        "matches_norm": after_counts.get("matches_norm", 0),
        "match_events": after_counts.get("match_events", 0),
        "lineups": after_counts.get("lineups", 0),
        "players": after_counts.get("players", 0),
        "gold_goal_timing_features": gold.get("counts", {}).get("gold_goal_timing_features", 0),
        "gold_player_snapshots": player.get("snapshots_written", 0),
    }
    report = {
        "ok": all(int(v or 0) > 0 for v in required_positive.values()),
        "sample": sample,
        "db_path": str(db_path),
        "pack_dir": str(pack_dir),
        "before_counts": before_counts,
        "imported": imported,
        "gold": gold,
        "goal_timing": timing,
        "player_score": player,
        "pack_summary": {"pack_name": pack["pack_name"], "total_rows": pack["total_rows"], "total_compressed_bytes": pack["total_compressed_bytes"], "overall_compression_ratio": pack["overall_compression_ratio"]},
        "after_counts": after_counts,
        "required_positive": required_positive,
    }
    (reports_dir / "v14_statsbomb_public_sample.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    if not report["ok"]:
        raise SystemExit(json.dumps(report, indent=2))
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-root", default="../data/statsbomb_public_sample/data")
    ap.add_argument("--db", default="../build/omnibet_v14_statsbomb_sample.sqlite")
    ap.add_argument("--pack-dir", default="../data_packs/football_statsbomb_sample_v1")
    ap.add_argument("--reports-dir", default="../reports")
    ap.add_argument("--raw-base", default=DEFAULT_RAW_BASE)
    ap.add_argument("--competition-id", type=int, default=9)
    ap.add_argument("--season-id", type=int, default=281)
    ap.add_argument("--limit-matches", type=int, default=3)
    args = ap.parse_args()
    print(json.dumps(run(Path(args.sample_root), Path(args.db), Path(args.pack_dir), Path(args.reports_dir), args.raw_base, args.competition_id, args.season_id, args.limit_matches), indent=2))


if __name__ == "__main__":
    main()
