#!/usr/bin/env python3
"""
OmniBet Lab v6 compressed data-pack exporter.

Exports selected SQLite tables into a portable compressed pack.

Current dependency-free format:
  JSONL.GZ + manifest.json

Future preferred format:
  Parquet + ZSTD for large historical/event/player tables.

Why JSONL.GZ first?
- Python stdlib only.
- deterministic and easy to verify.
- good enough as a fallback while Rust/Parquet/ZSTD path is planned.

Pack layout:
  pack_dir/
    manifest.json
    tables/
      matches_norm.jsonl.gz
      gold_match_features.jsonl.gz
      ...

The manifest contains rows, uncompressed bytes, compressed bytes, SHA256, table
schema, and pack policy.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Tuple


DEFAULT_TABLES = [
    "competitions", "seasons", "teams", "players",
    "matches_norm", "match_events", "lineups", "odds_snapshots",
    "gold_team_snapshots", "gold_match_features", "gold_goal_timing_features",
    "gold_player_snapshots", "gold_market_features",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table_exists(con: sqlite3.Connection, table: str) -> bool:
    return con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)).fetchone() is not None


def table_schema(con: sqlite3.Connection, table: str) -> List[dict]:
    rows = con.execute(f'PRAGMA table_info("{table}")').fetchall()
    return [
        {"cid": r[0], "name": r[1], "type": r[2], "notnull": bool(r[3]), "default": r[4], "pk": bool(r[5])}
        for r in rows
    ]


def export_table(con: sqlite3.Connection, table: str, out_path: Path, gzip_level: int = 9) -> dict:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{table}")').fetchall()]
    rows = con.execute(f'SELECT * FROM "{table}"')
    count = 0
    raw_bytes = 0

    with gzip.open(out_path, "wt", encoding="utf-8", compresslevel=gzip_level, newline="\n") as f:
        for row in rows:
            obj = {col: row[i] for i, col in enumerate(cols)}
            line = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            raw_bytes += len(line.encode("utf-8")) + 1
            f.write(line + "\n")
            count += 1

    compressed = out_path.stat().st_size
    return {
        "table": table,
        "path": str(out_path),
        "rows": count,
        "uncompressed_jsonl_bytes": raw_bytes,
        "compressed_bytes": compressed,
        "compression": "gzip",
        "gzip_level": gzip_level,
        "compression_ratio": (round(compressed / raw_bytes, 4) if raw_bytes > 0 else None),
        "sha256": sha256_file(out_path),
        "schema": table_schema(con, table),
    }


def export_pack(db: Path, out_dir: Path, tables: List[str], sport: str = "football", pack_name: str = "football_core_v1") -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "tables").mkdir(exist_ok=True)
    con = sqlite3.connect(str(db))

    exported = []
    skipped = []
    for table in tables:
        if not table_exists(con, table):
            skipped.append({"table": table, "reason": "missing"})
            continue
        info = export_table(con, table, out_dir / "tables" / f"{table}.jsonl.gz")
        exported.append(info)

    con.close()

    manifest = {
        "pack_name": pack_name,
        "sport": sport,
        "created_at": utc_now(),
        "source_db": str(db),
        "format": "omnibet.pack.v1",
        "storage_policy": {
            "current_codec": "jsonl.gzip",
            "future_preferred_codec": "parquet.zstd",
            "sqlite_role": "metadata/cache/recent state",
            "pack_role": "compressed immutable historical data",
        },
        "tables": exported,
        "skipped": skipped,
        "total_rows": sum(t["rows"] for t in exported),
        "total_uncompressed_jsonl_bytes": sum(t["uncompressed_jsonl_bytes"] for t in exported),
        "total_compressed_bytes": sum(t["compressed_bytes"] for t in exported),
    }
    manifest["overall_compression_ratio"] = round(
        manifest["total_compressed_bytes"] / max(1, manifest["total_uncompressed_jsonl_bytes"]), 4
    )
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(out_dir / "manifest.json")
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def main():
    ap = argparse.ArgumentParser(description="Export compressed OmniBet data pack.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--out-dir", default="../data_packs/football_core_v1")
    ap.add_argument("--sport", default="football")
    ap.add_argument("--pack-name", default="football_core_v1")
    ap.add_argument("--tables", default=",".join(DEFAULT_TABLES), help="Comma-separated table list.")
    args = ap.parse_args()

    tables = [x.strip() for x in args.tables.split(",") if x.strip()]
    res = export_pack(Path(args.db), Path(args.out_dir), tables, args.sport, args.pack_name)
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
