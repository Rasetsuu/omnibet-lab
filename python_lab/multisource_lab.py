#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Dict, List

from adapters.football_data_uk_adapter import import_csv
from adapters.openfootball_json_adapter import import_file as import_openfootball
from adapters.warehouse import connect, register_default_sources, table_counts
from adapters.wyscout_public_adapter import import_wyscout
from export_data_pack import DEFAULT_TABLES, export_pack

IDENTITY_SCHEMA = """
CREATE TABLE IF NOT EXISTS entity_identity_candidates (
    candidate_id TEXT PRIMARY KEY,
    entity_kind TEXT NOT NULL,
    normalized_name TEXT NOT NULL,
    canonical_name TEXT NOT NULL,
    source_count INTEGER NOT NULL,
    sources_json TEXT NOT NULL,
    variants_json TEXT NOT NULL
);
"""


def norm_name(name: str) -> str:
    s = (name or "").strip().lower()
    s = re.sub(r"[^a-z0-9]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    aliases = {
        "cape verde": "cape verde",
        "cabo verde": "cape verde",
        "germany": "germany",
        "deutschland": "germany",
        "japan": "japan",
        "spain": "spain",
        "espana": "spain",
    }
    return aliases.get(s, s)


def build_identity_candidates(db_path: Path) -> dict:
    con = sqlite3.connect(str(db_path))
    con.executescript(IDENTITY_SCHEMA)
    con.execute("DELETE FROM entity_identity_candidates")

    groups: Dict[str, List[dict]] = defaultdict(list)
    rows = con.execute("SELECT team_id, source_id, name FROM teams WHERE sport='football'").fetchall()
    for team_id, source_id, name in rows:
        groups[norm_name(name)].append({"team_id": team_id, "source_id": source_id, "name": name})

    candidates = []
    for normalized, xs in sorted(groups.items()):
        sources = sorted({x["source_id"] for x in xs if x["source_id"]})
        variants = sorted({x["name"] for x in xs if x["name"]})
        if not normalized:
            continue
        cid = f"team:{normalized.replace(' ', '_')}"
        canonical = variants[0] if variants else normalized.title()
        con.execute(
            """INSERT OR REPLACE INTO entity_identity_candidates
               (candidate_id, entity_kind, normalized_name, canonical_name, source_count, sources_json, variants_json)
               VALUES (?, 'team', ?, ?, ?, ?, ?)""",
            (cid, normalized, canonical, len(sources), json.dumps(sources), json.dumps(variants)),
        )
        candidates.append({"candidate_id": cid, "normalized_name": normalized, "canonical_name": canonical, "source_count": len(sources), "sources": sources, "variants": variants})
    con.commit()
    multi_source = [c for c in candidates if c["source_count"] >= 2]
    con.close()
    return {"candidate_rows": len(candidates), "multi_source_candidate_rows": len(multi_source), "samples": multi_source[:10]}


def source_counts(db_path: Path) -> dict:
    con = sqlite3.connect(str(db_path))
    out = {
        "tables": table_counts(con),
        "matches_by_source": dict(con.execute("SELECT source_id, COUNT(*) FROM matches_norm GROUP BY source_id").fetchall()),
        "events_by_source": dict(con.execute("SELECT source_id, COUNT(*) FROM match_events GROUP BY source_id").fetchall()),
        "odds_by_source": dict(con.execute("SELECT source_id, COUNT(*) FROM odds_snapshots GROUP BY source_id").fetchall()),
    }
    con.close()
    return out


def run(args: argparse.Namespace) -> dict:
    db = Path(args.db)
    if db.exists():
        db.unlink()
    con = connect(db)
    register_default_sources(con)
    con.close()

    reports = []
    reports.append(import_csv(db, args.football_data_csv, competition_hint="unified_international", season_hint="sample"))
    reports.append(import_openfootball(db, Path(args.openfootball_json), competition_hint="sample_league", season_hint="2024-2025"))
    reports.append(import_wyscout(db, Path(args.wyscout_matches), Path(args.wyscout_events)))

    identity = build_identity_candidates(db)
    counts = source_counts(db)
    pack = export_pack(db, Path(args.pack_dir), DEFAULT_TABLES + ["entity_identity_candidates"], sport="football", pack_name=args.pack_name)

    required = {
        "source_count": len(counts["matches_by_source"]),
        "matches_norm": counts["tables"].get("matches_norm", 0),
        "match_events": counts["tables"].get("match_events", 0),
        "odds_snapshots": counts["tables"].get("odds_snapshots", 0),
        "identity_candidates": identity["candidate_rows"],
        "multi_source_identity_candidates": identity["multi_source_candidate_rows"],
        "pack_rows": pack["total_rows"],
        "compressed_bytes": pack["total_compressed_bytes"],
    }
    result = {
        "ok": True,
        "db": str(db),
        "imports": reports,
        "source_counts": counts,
        "identity": identity,
        "pack_summary": {
            "pack_name": pack["pack_name"],
            "total_rows": pack["total_rows"],
            "total_uncompressed_jsonl_bytes": pack["total_uncompressed_jsonl_bytes"],
            "total_compressed_bytes": pack["total_compressed_bytes"],
            "overall_compression_ratio": pack["overall_compression_ratio"],
        },
        "required_positive": required,
        "source_manifest": {
            "football_data_uk_csv": "historical results and odds style CSV",
            "openfootball_json": "broad fixture/result JSON style",
            "wyscout_public_events": "event/player JSON style",
            "statsbomb_open_data": "covered by v20 scale pipeline",
        },
    }
    result["ok"] = all(int(v or 0) > 0 for v in required.values()) and required["source_count"] >= 3
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(1)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Run multi-source football adapter smoke and identity report.")
    ap.add_argument("--db", default="../build/omnibet_v23_multisource.sqlite")
    ap.add_argument("--football-data-csv", default="../data/unified_intl_matches.csv")
    ap.add_argument("--openfootball-json", default="../data/samples/openfootball_sample.json")
    ap.add_argument("--wyscout-matches", default="../data/samples/wyscout_public_sample_matches.json")
    ap.add_argument("--wyscout-events", default="../data/samples/wyscout_public_sample_events.json")
    ap.add_argument("--pack-dir", default="../data_packs/football_multisource_v1")
    ap.add_argument("--pack-name", default="football_multisource_v1")
    ap.add_argument("--out", default="../reports/ci_v23_multisource.json")
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
