#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from adapters.football_data_uk_adapter import import_csv
from adapters.openfootball_json_adapter import import_file as import_openfootball
from adapters.statsbomb_open_adapter import import_all as import_statsbomb_all
from adapters.warehouse import connect, register_default_sources
from adapters.wyscout_public_adapter import import_wyscout
from backfill_reports import write_reports
from export_data_pack import DEFAULT_TABLES, export_pack
from multisource_lab import build_identity_candidates

EXTRA_TABLES = ["entity_identity_candidates"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def existing(paths: Iterable[Optional[str]]) -> List[Path]:
    out = []
    for p in paths:
        if not p:
            continue
        path = Path(p)
        if path.exists():
            out.append(path)
    return out


def scan_files(root: Optional[str], pattern: str, limit: int = 0) -> List[Path]:
    if not root:
        return []
    r = Path(root)
    if not r.exists():
        return []
    files = sorted(p for p in r.rglob(pattern) if p.is_file())
    return files[:limit] if limit and limit > 0 else files


def reset_path(path: Path) -> None:
    if path.exists():
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def tiny_smoke_defaults(args: argparse.Namespace) -> None:
    root = repo_root()
    args.football_data_csv.append(str(root / "data" / "samples" / "football_data_odds_sample.csv"))
    args.openfootball_json.append(str(root / "data" / "samples" / "openfootball_sample.json"))
    args.wyscout_matches = args.wyscout_matches or str(root / "data" / "samples" / "wyscout_public_sample_matches.json")
    args.wyscout_events = args.wyscout_events or str(root / "data" / "samples" / "wyscout_public_sample_events.json")
    args.pack_name = args.pack_name or "football_v26_tiny_smoke"
    args.max_files_per_source = args.max_files_per_source or 20


def import_football_data(db: Path, args: argparse.Namespace) -> List[dict]:
    files = existing(args.football_data_csv)
    files.extend(scan_files(args.football_data_dir, "*.csv", args.max_files_per_source))
    seen = set()
    reports = []
    for f in files:
        key = str(f.resolve())
        if key in seen:
            continue
        seen.add(key)
        reports.append(import_csv(db, str(f), competition_hint=args.competition or "local_backfill", season_hint=args.season or "unknown"))
    return reports


def import_openfootball_files(db: Path, args: argparse.Namespace) -> List[dict]:
    files = existing(args.openfootball_json)
    files.extend(scan_files(args.openfootball_dir, "*.json", args.max_files_per_source))
    seen = set()
    reports = []
    for f in files:
        key = str(f.resolve())
        if key in seen:
            continue
        seen.add(key)
        reports.append(import_openfootball(db, f, competition_hint=args.competition or "local_backfill", season_hint=args.season or "unknown"))
    return reports


def guess_wyscout_pair(root: Optional[str]) -> tuple[Optional[Path], Optional[Path]]:
    if not root:
        return None, None
    r = Path(root)
    if not r.exists():
        return None, None
    jsons = sorted(p for p in r.rglob("*.json") if p.is_file())
    matches = [p for p in jsons if "match" in p.name.lower()]
    events = [p for p in jsons if "event" in p.name.lower()]
    return (matches[0] if matches else None, events[0] if events else None)


def import_wyscout_files(db: Path, args: argparse.Namespace) -> List[dict]:
    reports = []
    matches = Path(args.wyscout_matches) if args.wyscout_matches and Path(args.wyscout_matches).exists() else None
    events = Path(args.wyscout_events) if args.wyscout_events and Path(args.wyscout_events).exists() else None
    if not (matches and events):
        matches, events = guess_wyscout_pair(args.wyscout_dir)
    if matches and events:
        reports.append(import_wyscout(db, matches, events))
    return reports


def import_statsbomb(db: Path, args: argparse.Namespace) -> List[dict]:
    root = Path(args.statsbomb_dir) if args.statsbomb_dir else None
    if not root or not root.exists():
        return []
    reports = [import_statsbomb_all(db, root, limit_matches=args.max_statsbomb_matches if args.max_statsbomb_matches > 0 else None, include_events=not args.no_events)]
    return reports


def db_table_counts(db: Path) -> Dict[str, int]:
    con = sqlite3.connect(str(db))
    try:
        rows = con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        return {name: int(con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]) for (name,) in rows if not str(name).startswith("sqlite_")}
    finally:
        con.close()


def run(args: argparse.Namespace) -> Dict[str, Any]:
    if args.preset == "tiny-smoke":
        tiny_smoke_defaults(args)

    out = Path(args.out)
    packs_dir = out / "packs"
    reports_dir = out / "reports"
    db = out / "omnibet_v26_backfill.sqlite"
    pack_dir = packs_dir / (args.pack_name or "football_v26_backfill")

    if args.clean:
        reset_path(out)
    out.mkdir(parents=True, exist_ok=True)
    packs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    if db.exists():
        db.unlink()
    con = connect(db)
    register_default_sources(con)
    con.close()

    imports = {
        "football_data": import_football_data(db, args),
        "openfootball": import_openfootball_files(db, args),
        "wyscout": import_wyscout_files(db, args),
        "statsbomb": import_statsbomb(db, args),
    }
    identity = build_identity_candidates(db)
    pack = export_pack(db, pack_dir, DEFAULT_TABLES + EXTRA_TABLES, sport="football", pack_name=args.pack_name or "football_v26_backfill")
    report_bundle = write_reports(db, reports_dir)

    counts = db_table_counts(db)
    source_report = report_bundle["reports"]["source_coverage"]
    event_report = report_bundle["reports"]["event_coverage"]
    player_report = report_bundle["reports"]["player_coverage"]
    odds_report = report_bundle["reports"]["odds_coverage"]
    ready_report = report_bundle["reports"]["walk_forward_ready"]

    required = {
        "matches_norm": counts.get("matches_norm", 0),
        "source_count": len([k for k, v in source_report.get("matches_by_source", {}).items() if v > 0]),
        "pack_rows": pack["total_rows"],
        "compressed_bytes": pack["total_compressed_bytes"],
        "identity_candidates": identity["candidate_rows"],
    }
    if args.preset == "tiny-smoke":
        required.update({
            "odds_snapshots": counts.get("odds_snapshots", 0),
            "event_rows": counts.get("match_events", 0),
        })

    manifest = {
        "ok": True,
        "milestone": "v26_local_scale_historical_backfill_runner",
        "created_at": utc_now(),
        "preset": args.preset,
        "honesty": {
            "paper_only": True,
            "claim": "Data backfill/readiness infrastructure only. No model-quality or profitability claim.",
            "ci_policy": "tiny-smoke stays deterministic; full/heavy imports are local-only.",
        },
        "paths": {
            "out": str(out),
            "db": str(db),
            "pack_dir": str(pack_dir),
            "reports_dir": str(reports_dir),
        },
        "input_args": {k: v for k, v in vars(args).items() if k not in {"func"}},
        "imports": imports,
        "identity": identity,
        "db_counts": counts,
        "coverage_digest": {
            "matches_by_source": source_report.get("matches_by_source", {}),
            "event_match_coverage": event_report.get("event_match_coverage"),
            "lineup_match_coverage": player_report.get("lineup_match_coverage"),
            "odds_match_coverage": odds_report.get("odds_match_coverage"),
            "walk_forward_ready": ready_report,
        },
        "pack_summary": {
            "pack_name": pack["pack_name"],
            "format": pack["format"],
            "total_rows": pack["total_rows"],
            "total_uncompressed_jsonl_bytes": pack["total_uncompressed_jsonl_bytes"],
            "total_compressed_bytes": pack["total_compressed_bytes"],
            "overall_compression_ratio": pack["overall_compression_ratio"],
            "manifest": str(pack_dir / "manifest.json"),
        },
        "reports_written": report_bundle["written"],
        "required_positive": required,
        "next_storage_step": {
            "current_v26_codec": "jsonl.gzip",
            "why": "stdlib, deterministic, CI-friendly, Rust verifier already exists",
            "v27_heavy_local_codec": "parquet.zstd",
            "note": "Raw historical/event/player/odds data should stay local; runtime ships compact model artifacts and metadata only.",
        },
    }
    manifest["ok"] = all(int(v or 0) > 0 for v in required.values())
    manifest_path = reports_dir / "v26_backfill_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))
    if not manifest["ok"]:
        raise SystemExit(1)
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description="OmniBet v26 local-scale historical football data backfill runner.")
    ap.add_argument("--preset", choices=["tiny-smoke", "local"], default="local")
    ap.add_argument("--out", default="../build/local_backfills/v26_run")
    ap.add_argument("--pack-name", default="")
    ap.add_argument("--clean", action="store_true", default=True)

    ap.add_argument("--football-data-csv", action="append", default=[], help="Football-Data-style CSV file. Repeatable.")
    ap.add_argument("--football-data-dir", default="", help="Directory recursively scanned for Football-Data-style CSV files.")
    ap.add_argument("--statsbomb-dir", default="", help="StatsBomb open-data data/ directory with competitions/matches/events/lineups.")
    ap.add_argument("--openfootball-json", action="append", default=[], help="OpenFootball-style JSON file. Repeatable.")
    ap.add_argument("--openfootball-dir", default="", help="Directory recursively scanned for OpenFootball-style JSON files.")
    ap.add_argument("--wyscout-matches", default="", help="Wyscout-style matches JSON.")
    ap.add_argument("--wyscout-events", default="", help="Wyscout-style events JSON.")
    ap.add_argument("--wyscout-dir", default="", help="Directory containing Wyscout-style matches/events JSON files.")
    ap.add_argument("--odds-dir", default="", help="Reserved for dedicated odds-history backfill sources; Football-Data odds are imported via CSV now.")

    ap.add_argument("--competition", default="")
    ap.add_argument("--season", default="")
    ap.add_argument("--max-files-per-source", type=int, default=0, help="0 means unlimited. Useful for local dry-runs.")
    ap.add_argument("--max-statsbomb-matches", type=int, default=0, help="0 means unlimited when --statsbomb-dir is supplied.")
    ap.add_argument("--no-events", action="store_true", help="Skip StatsBomb event imports; useful for fast local fixture-only runs.")

    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
