#!/usr/bin/env python3
"""
OmniBet Lab v6 storage audit.

Audits the current package/database/data-pack size situation:
- file sizes
- SQLite table row counts
- approximate table payload sizes
- compression ratios for CSV/JSON/SQLite files
- recommendations for what belongs in SQLite vs compressed packs

No third-party dependencies.
"""
from __future__ import annotations

import argparse
import gzip
import json
import os
import sqlite3
import tempfile
from pathlib import Path
from typing import Dict, List


def human(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)
    for u in units:
        if x < 1024 or u == units[-1]:
            return f"{x:.2f} {u}"
        x /= 1024


def gzip_size(path: Path, level: int = 9) -> int:
    data = path.read_bytes()
    return len(gzip.compress(data, compresslevel=level))


def table_counts(db: Path) -> Dict[str, int]:
    if not db.exists():
        return {}
    con = sqlite3.connect(str(db))
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")]
    out = {}
    for t in tables:
        try:
            out[t] = int(con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
        except Exception:
            out[t] = -1
    con.close()
    return out


def sqlite_info(db: Path) -> Dict[str, object]:
    if not db.exists():
        return {"exists": False}
    con = sqlite3.connect(str(db))
    page_count = con.execute("PRAGMA page_count").fetchone()[0]
    page_size = con.execute("PRAGMA page_size").fetchone()[0]
    freelist = con.execute("PRAGMA freelist_count").fetchone()[0]
    con.close()
    return {
        "exists": True,
        "path": str(db),
        "bytes": db.stat().st_size,
        "human": human(db.stat().st_size),
        "page_count": page_count,
        "page_size": page_size,
        "sqlite_pages_bytes": page_count * page_size,
        "freelist_pages": freelist,
        "gzip9_bytes": gzip_size(db),
        "gzip_ratio": round(gzip_size(db) / max(1, db.stat().st_size), 4),
        "tables": table_counts(db),
    }


def file_entry(path: Path, base: Path) -> Dict[str, object]:
    size = path.stat().st_size
    gz = None
    ratio = None
    if path.suffix.lower() in {".csv", ".json", ".jsonl", ".sqlite", ".db"} or path.name.endswith(".md"):
        try:
            gz = gzip_size(path)
            ratio = round(gz / max(1, size), 4)
        except Exception:
            pass
    return {
        "path": str(path.relative_to(base)),
        "bytes": size,
        "human": human(size),
        "gzip9_bytes": gz,
        "gzip_ratio": ratio,
    }


def audit(root: Path, db: Path | None = None) -> Dict[str, object]:
    if db is None:
        db = root / "build" / "omnibet.sqlite"

    files = []
    total = 0
    for p in sorted(root.rglob("*")):
        if p.is_file():
            # ignore __pycache if any
            if "__pycache__" in p.parts:
                continue
            total += p.stat().st_size
            files.append(file_entry(p, root))

    largest = sorted(files, key=lambda x: x["bytes"], reverse=True)[:25]
    by_ext: Dict[str, int] = {}
    for f in files:
        ext = Path(f["path"]).suffix.lower() or "(no_ext)"
        by_ext[ext] = by_ext.get(ext, 0) + int(f["bytes"])

    dbinfo = sqlite_info(db)
    recommendations = [
        "Keep app metadata, source registry, watermarks and recent cache in SQLite.",
        "Move big immutable historical/event/player data into compressed data packs.",
        "Preferred future pack format: Parquet + ZSTD when pyarrow/duckdb is available.",
        "Current stdlib fallback: JSONL.GZ, deterministic, portable, slower/larger than ZSTD.",
        "Do not bundle every sport/season by default; use optional sport/season/source packs.",
        "Gold features can be regenerated, so treat them as cache unless expensive to rebuild.",
    ]

    return {
        "root": str(root),
        "total_files": len(files),
        "total_bytes": total,
        "total_human": human(total),
        "by_extension_bytes": {k: {"bytes": v, "human": human(v)} for k, v in sorted(by_ext.items())},
        "largest_files": largest,
        "sqlite": dbinfo,
        "recommendations": recommendations,
    }


def main():
    ap = argparse.ArgumentParser(description="Audit OmniBet storage/database sizes.")
    ap.add_argument("--root", default="..")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--out", default="../reports/v6_storage_audit.json")
    args = ap.parse_args()

    res = audit(Path(args.root).resolve(), Path(args.db).resolve())
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
