#!/usr/bin/env python3
"""OmniBet v28 real-source acquisition catalog.

This script is intentionally dependency-free and network-free by default.
It records where real data should come from, where it should live locally,
and which existing v26/v27 commands should consume it after the user syncs or
manually downloads the sources.

CI uses this to generate a deterministic source-readiness report without
committing or downloading large raw datasets.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List


SOURCES: List[Dict[str, Any]] = [
    {
        "source_id": "statsbomb_open_data",
        "name": "StatsBomb Open Data",
        "kind": "free_open_event_data",
        "sport": "football",
        "homepage": "https://github.com/statsbomb/open-data",
        "primary_sync": {
            "method": "git_clone_or_zip",
            "recommended_local_path": "data/external/statsbomb-open-data",
            "example_command": "git clone https://github.com/statsbomb/open-data.git data/external/statsbomb-open-data",
        },
        "v26_argument": "--statsbomb-dir data/external/statsbomb-open-data/data",
        "domains": ["competitions", "matches", "events", "lineups", "360_freeze_frame_selected_matches"],
        "format": "json",
        "license_or_terms_note": "Free public research data with attribution/terms requirements. Do not remove source attribution.",
        "priority": 1,
        "why": "Best currently available open event/lineup source for proving event-aware and player-aware pipelines.",
        "ci_policy": "never_download_in_ci",
    },
    {
        "source_id": "football_data_uk",
        "name": "Football-Data.co.uk",
        "kind": "free_results_stats_odds_csv",
        "sport": "football",
        "homepage": "https://www.football-data.co.uk/data.php",
        "primary_sync": {
            "method": "manual_or_scripted_csv_download",
            "recommended_local_path": "data/external/football-data",
            "example_command": "download selected CSV files from https://www.football-data.co.uk/data.php into data/external/football-data",
        },
        "v26_argument": "--football-data-dir data/external/football-data",
        "domains": ["match_results", "match_stats", "betting_odds", "closing_odds_columns_when_available"],
        "format": "csv_or_excel",
        "license_or_terms_note": "Free data site; preserve source attribution and original files in bronze cache.",
        "priority": 2,
        "why": "Strong free source for historical match results, match stats, and odds/CLV calibration across leagues/seasons.",
        "ci_policy": "never_download_in_ci",
    },
    {
        "source_id": "openfootball_worldcup",
        "name": "OpenFootball World Cup / football.db datasets",
        "kind": "public_domain_fixture_result_spine",
        "sport": "football",
        "homepage": "https://github.com/openfootball/worldcup",
        "primary_sync": {
            "method": "git_clone_or_zip",
            "recommended_local_path": "data/external/openfootball/worldcup",
            "example_command": "git clone https://github.com/openfootball/worldcup.git data/external/openfootball/worldcup",
        },
        "v26_argument": "--openfootball-dir data/external/openfootball",
        "domains": ["fixtures", "results", "world_cup", "qualifiers", "competition_structure"],
        "format": "football_txt_and_related_structured_text",
        "license_or_terms_note": "CC0/public-domain style source. Still keep source attribution in manifests.",
        "priority": 3,
        "why": "Excellent canonical public fixture/result spine for World Cup and qualifiers, including 2026 planning data.",
        "ci_policy": "never_download_in_ci",
    },
    {
        "source_id": "the_odds_api",
        "name": "The Odds API",
        "kind": "optional_paid_live_and_historical_odds_api",
        "sport": "multi_sport",
        "homepage": "https://the-odds-api.com/liveapi/guides/v4/",
        "primary_sync": {
            "method": "api_key_required",
            "recommended_local_path": "data/external/the-odds-api",
            "example_command": "export THE_ODDS_API_KEY=... # then run a future paid-source downloader outside CI",
        },
        "v26_argument": "--odds-dir data/external/the-odds-api",
        "domains": ["live_odds", "historical_odds", "historical_events", "player_props_after_supported_dates"],
        "format": "json_api",
        "license_or_terms_note": "Paid API for historical odds; never commit API keys, responses with restricted terms, or quota-heavy pulls.",
        "priority": 4,
        "why": "Candidate for live/current odds and historical odds snapshots once paid quota/API-key workflow is intentionally added.",
        "ci_policy": "never_require_api_key_in_ci",
    },
]

LAYOUT = {
    "bronze_root": "data/external",
    "silver_root": "build/local_backfills/<run_id>/packs or future data_lake/football/silver",
    "gold_root": "future data_lake/football/gold",
    "runtime_root": "models/ and small metadata/cache files only",
    "git_policy": [
        "Commit only tiny deterministic samples and manifests.",
        "Do not commit raw downloaded datasets.",
        "Do not commit paid API responses unless license explicitly allows it and size is tiny/sample-only.",
        "Keep local heavy warehouse under data/external, build/local_backfills, or ignored data_lake paths.",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def maybe_count_files(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"exists": False, "files": 0, "bytes": 0}
    files = [p for p in path.rglob("*") if p.is_file()]
    return {"exists": True, "files": len(files), "bytes": sum(p.stat().st_size for p in files)}


def build_catalog(local_root: Path | None = None) -> Dict[str, Any]:
    local_checks = {}
    if local_root is not None:
        for source in SOURCES:
            rec = source.get("primary_sync", {}).get("recommended_local_path", "")
            rel_parts = Path(rec).parts
            if "data" in rel_parts and "external" in rel_parts:
                idx = rel_parts.index("external")
                candidate = local_root.joinpath(*rel_parts[idx + 1 :])
            else:
                candidate = local_root / source["source_id"]
            local_checks[source["source_id"]] = {"path": str(candidate), **maybe_count_files(candidate)}
    return {
        "ok": True,
        "milestone": "v28_real_source_acquisition_catalog",
        "created_at": utc_now(),
        "sources": SOURCES,
        "layout": LAYOUT,
        "recommended_order": [s["source_id"] for s in sorted(SOURCES, key=lambda x: x["priority"])],
        "local_checks": local_checks,
        "v26_backfill_example": {
            "command": "python python_lab/local_backfill_runner.py --out build/local_backfills/v28_real_sources --pack-name football_v28_real_sources --football-data-dir data/external/football-data --statsbomb-dir data/external/statsbomb-open-data/data --openfootball-dir data/external/openfootball --wyscout-dir data/external/wyscout-style",
            "note": "Run only after syncing local source data. CI should use v26 tiny-smoke instead.",
        },
        "v27_storage_example": {
            "command": "python python_lab/export_parquet_zstd_pack.py --db build/local_backfills/v28_real_sources/omnibet_v26_backfill.sqlite --out-dir build/local_backfills/v28_real_sources/parquet_zstd_pack --pack-name football_v28_real_sources_parquet_zstd --zstd-level 6",
            "note": "Optional local heavy storage path after v26 backfill succeeds.",
        },
        "honesty": {
            "paper_only": True,
            "no_profit_claim": True,
            "no_model_quality_claim": True,
            "heavy_downloads_out_of_ci": True,
        },
    }


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")


def write_example_config(path: Path) -> None:
    config = {
        "version": "omnibet.source_acquisition.v28.example",
        "local_root": "data/external",
        "enabled_sources": ["statsbomb_open_data", "football_data_uk", "openfootball_worldcup"],
        "paid_sources_disabled_by_default": ["the_odds_api"],
        "sources": {
            s["source_id"]: {
                "enabled": s["source_id"] != "the_odds_api",
                "homepage": s["homepage"],
                "local_path": s["primary_sync"]["recommended_local_path"],
                "sync_method": s["primary_sync"]["method"],
                "v26_argument": s["v26_argument"],
            }
            for s in SOURCES
        },
    }
    write_json(path, config)


def render_shell_plan(path: Path) -> None:
    lines = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        "",
        "# OmniBet v28 local source sync plan.",
        "# Review source terms before running. This script is not used by CI.",
        "mkdir -p data/external",
        "",
        "# StatsBomb Open Data",
        "if [ ! -d data/external/statsbomb-open-data/.git ]; then",
        "  git clone https://github.com/statsbomb/open-data.git data/external/statsbomb-open-data",
        "else",
        "  git -C data/external/statsbomb-open-data pull --ff-only",
        "fi",
        "",
        "# OpenFootball World Cup",
        "mkdir -p data/external/openfootball",
        "if [ ! -d data/external/openfootball/worldcup/.git ]; then",
        "  git clone https://github.com/openfootball/worldcup.git data/external/openfootball/worldcup",
        "else",
        "  git -C data/external/openfootball/worldcup pull --ff-only",
        "fi",
        "",
        "# Football-Data.co.uk CSV files are intentionally manual/selective by default.",
        "# Put downloaded CSV files under data/external/football-data/.",
        "mkdir -p data/external/football-data",
        "",
        "echo 'Source sync skeleton complete. Add Football-Data CSVs manually, then run v26 backfill.'",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description="Generate OmniBet v28 real-source acquisition catalog.")
    ap.add_argument("--out", default="../reports/ci_v28_source_catalog.json")
    ap.add_argument("--local-root", default="", help="Optional local data/external root to inspect.")
    ap.add_argument("--write-example-config", default="")
    ap.add_argument("--write-shell-plan", default="")
    args = ap.parse_args()

    catalog = build_catalog(Path(args.local_root) if args.local_root else None)
    write_json(Path(args.out), catalog)
    if args.write_example_config:
        write_example_config(Path(args.write_example_config))
    if args.write_shell_plan:
        render_shell_plan(Path(args.write_shell_plan))
    print(json.dumps(catalog, indent=2))


if __name__ == "__main__":
    main()
