#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from adapters.statsbomb_open_adapter import import_all
from adapters.warehouse import connect, register_default_sources, table_counts
from export_data_pack import DEFAULT_TABLES, export_pack
from gold_feature_builder import build_gold
from goal_timing_lab import analyze as analyze_goal_timing
from player_score_lab import build_player_scores

DEFAULT_RAW_BASE = "https://" + "raw.githubusercontent.com" + "/statsbomb/open-data/master/data"
DEFAULT_SMOKE_PAIR = (9, 281)  # Bundesliga 2023/2024, compact but event-rich.


def fetch_json(url: str, timeout: int = 60, retries: int = 4, backoff: float = 0.6) -> Any:
    last_error: Exception | None = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "omnibet-lab-v20-scale"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            last_error = e
            if attempt + 1 < retries:
                time.sleep(backoff * (attempt + 1))
    raise last_error or RuntimeError(f"failed to fetch {url}")


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_pair(text: str) -> Tuple[int, int]:
    left, right = text.replace(":", "/").split("/", 1)
    return int(left), int(right)


def unique_pairs(competitions: List[dict]) -> List[Tuple[int, int]]:
    pairs = []
    seen = set()
    for c in competitions:
        pair = (int(c["competition_id"]), int(c["season_id"]))
        if pair not in seen:
            seen.add(pair)
            pairs.append(pair)
    return pairs


def load_competition_pairs(raw_base: str, profile: str, explicit_pairs: List[str], max_competitions: int) -> Tuple[List[dict], List[Tuple[int, int]]]:
    competitions = fetch_json(f"{raw_base}/competitions.json")
    if explicit_pairs:
        pairs = [parse_pair(x) for x in explicit_pairs]
    elif profile == "smoke":
        pairs = [DEFAULT_SMOKE_PAIR]
    else:
        pairs = unique_pairs(competitions)
        if max_competitions > 0:
            pairs = pairs[:max_competitions]
    return competitions, pairs


def materialize_open_data_slice(
    root: Path,
    raw_base: str,
    profile: str,
    pairs: List[Tuple[int, int]],
    competitions: List[dict],
    max_matches: int,
    include_events: bool,
    sleep_seconds: float,
) -> Dict[str, Any]:
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    allowed_pairs = set(pairs)
    selected_competitions = [
        c for c in competitions
        if (int(c["competition_id"]), int(c["season_id"])) in allowed_pairs
    ]
    write_json(root / "competitions.json", selected_competitions)

    selected_match_ids: List[int] = []
    match_file_rows = 0
    event_files = 0
    lineup_files = 0
    failures: List[dict] = []

    for competition_id, season_id in pairs:
        if max_matches > 0 and len(selected_match_ids) >= max_matches:
            break
        try:
            matches_all = fetch_json(f"{raw_base}/matches/{competition_id}/{season_id}.json")
        except Exception as e:
            failures.append({"stage": "matches", "competition_id": competition_id, "season_id": season_id, "error": str(e)})
            continue

        remaining = max_matches - len(selected_match_ids) if max_matches > 0 else len(matches_all)
        selected = matches_all[:remaining]
        match_file_rows += len(selected)
        write_json(root / "matches" / str(competition_id) / f"{season_id}.json", selected)

        for m in selected:
            mid = int(m["match_id"])
            selected_match_ids.append(mid)
            if not include_events:
                continue
            try:
                write_json(root / "events" / f"{mid}.json", fetch_json(f"{raw_base}/events/{mid}.json"))
                event_files += 1
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            except Exception as e:
                failures.append({"stage": "events", "match_id": mid, "error": str(e)})
            try:
                write_json(root / "lineups" / f"{mid}.json", fetch_json(f"{raw_base}/lineups/{mid}.json"))
                lineup_files += 1
                if sleep_seconds > 0:
                    time.sleep(sleep_seconds)
            except Exception as e:
                failures.append({"stage": "lineups", "match_id": mid, "error": str(e)})

    manifest = {
        "profile": profile,
        "root": str(root),
        "raw_base": raw_base,
        "competition_season_pairs": [{"competition_id": c, "season_id": s} for c, s in pairs],
        "max_matches": max_matches,
        "include_events": include_events,
        "competitions_written": len(selected_competitions),
        "match_file_rows": match_file_rows,
        "selected_match_ids": selected_match_ids,
        "event_files": event_files,
        "lineup_files": lineup_files,
        "failures": failures,
    }
    write_json(root / "omnibet_source_slice_manifest.json", manifest)
    return manifest


def sqlite_size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def table_count(con: sqlite3.Connection, table: str) -> int:
    return con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]


def quality_report(db_path: Path) -> Dict[str, Any]:
    con = sqlite3.connect(str(db_path))
    counts = table_counts(con)
    playable = table_count(con, "matches_norm") if "matches_norm" in counts else 0
    event_matches = con.execute("SELECT COUNT(DISTINCT match_id) FROM match_events").fetchone()[0]
    lineup_matches = con.execute("SELECT COUNT(DISTINCT match_id) FROM lineups").fetchone()[0]
    players = table_count(con, "players") if "players" in counts else 0
    con.close()
    return {
        "counts": counts,
        "event_match_coverage": (event_matches / playable) if playable else None,
        "lineup_match_coverage": (lineup_matches / playable) if playable else None,
        "players": players,
    }


def run(args: argparse.Namespace) -> Dict[str, Any]:
    root = Path(args.sample_root)
    db_path = Path(args.db)
    pack_dir = Path(args.pack_dir)
    reports_dir = Path(args.reports_dir)
    reports_dir.mkdir(parents=True, exist_ok=True)

    competitions, pairs = load_competition_pairs(args.raw_base, args.profile, args.competition_season, args.max_competitions)
    source_manifest = materialize_open_data_slice(
        root=root,
        raw_base=args.raw_base,
        profile=args.profile,
        pairs=pairs,
        competitions=competitions,
        max_matches=args.max_matches,
        include_events=not args.no_events,
        sleep_seconds=args.sleep_seconds,
    )

    if db_path.exists():
        db_path.unlink()
    con = connect(db_path)
    register_default_sources(con)
    con.close()

    imported = import_all(db_path, root, limit_matches=args.max_matches if args.max_matches > 0 else None, include_events=not args.no_events)
    gold = build_gold(db_path, rolling_n=args.rolling, reset=True)
    timing = analyze_goal_timing(db_path)
    player = build_player_scores(db_path)
    pack = export_pack(db_path, pack_dir, DEFAULT_TABLES, sport="football", pack_name=args.pack_name)
    quality = quality_report(db_path)

    report = {
        "ok": True,
        "profile": args.profile,
        "db_path": str(db_path),
        "db_bytes": sqlite_size(db_path),
        "pack_dir": str(pack_dir),
        "source_manifest": source_manifest,
        "imported": imported,
        "gold": gold,
        "goal_timing": timing,
        "player_score": player,
        "quality": quality,
        "pack_summary": {
            "pack_name": pack["pack_name"],
            "format": pack["format"],
            "total_rows": pack["total_rows"],
            "total_uncompressed_jsonl_bytes": pack["total_uncompressed_jsonl_bytes"],
            "total_compressed_bytes": pack["total_compressed_bytes"],
            "overall_compression_ratio": pack["overall_compression_ratio"],
        },
        "storage_plan": {
            "current_ci_codec": "jsonl.gzip",
            "current_role": "portable deterministic CI pack and Rust reader input",
            "next_large_local_codec": "parquet.zstd or duckdb external tables",
            "sqlite_role": "metadata/cache/recent state, not giant historical lake",
            "full_import_command": "python statsbomb_scale_pipeline.py --profile full --max-matches 0 --pack-name football_statsbomb_full_v1",
        },
    }

    positive = {
        "matches_norm": quality["counts"].get("matches_norm", 0),
        "match_events": quality["counts"].get("match_events", 0),
        "lineups": quality["counts"].get("lineups", 0),
        "players": quality["counts"].get("players", 0),
        "pack_rows": pack["total_rows"],
        "compressed_bytes": pack["total_compressed_bytes"],
    }
    report["required_positive"] = positive
    report["ok"] = all(int(v or 0) > 0 for v in positive.values()) and len(source_manifest["failures"]) == 0

    out = reports_dir / args.report_name
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Configurable StatsBomb public data-scale pipeline.")
    ap.add_argument("--profile", choices=["smoke", "medium", "full"], default="smoke")
    ap.add_argument("--sample-root", default="../data/statsbomb_scale_sample/data")
    ap.add_argument("--db", default="../build/omnibet_v20_statsbomb_scale.sqlite")
    ap.add_argument("--pack-dir", default="../data_packs/football_statsbomb_scale_v1")
    ap.add_argument("--pack-name", default="football_statsbomb_scale_v1")
    ap.add_argument("--reports-dir", default="../reports")
    ap.add_argument("--report-name", default="ci_v20_data_scale.json")
    ap.add_argument("--raw-base", default=DEFAULT_RAW_BASE)
    ap.add_argument("--competition-season", action="append", default=[], help="competition_id/season_id, repeatable")
    ap.add_argument("--max-competitions", type=int, default=1)
    ap.add_argument("--max-matches", type=int, default=16, help="0 means no global match limit")
    ap.add_argument("--rolling", type=int, default=10)
    ap.add_argument("--no-events", action="store_true")
    ap.add_argument("--sleep-seconds", type=float, default=0.0)
    args = ap.parse_args()

    if args.profile == "full" and args.max_matches == 16:
        args.max_matches = 0
        args.max_competitions = 0
    elif args.profile == "medium" and args.max_matches == 16:
        args.max_matches = 100
        args.max_competitions = max(args.max_competitions, 3)

    run(args)


if __name__ == "__main__":
    main()
