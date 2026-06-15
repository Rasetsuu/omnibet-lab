#!/usr/bin/env python3
"""
Verify an OmniBet compressed data pack.

Checks:
- manifest exists
- every table file exists
- SHA256 matches
- row count matches JSONL.GZ line count
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def line_count_gz(path: Path) -> int:
    n = 0
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for _ in f:
            n += 1
    return n


def verify(pack_dir: Path) -> dict:
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "error": "manifest.json missing"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    errors = []
    checked = []
    for table in manifest.get("tables", []):
        p = Path(table["path"])
        if not p.is_absolute():
            p = pack_dir / p
        # Older manifests may store absolute paths; prefer basename fallback.
        if not p.exists():
            p = pack_dir / "tables" / f"{table['table']}.jsonl.gz"
        if not p.exists():
            errors.append({"table": table["table"], "error": "file missing"})
            continue
        sha = sha256_file(p)
        rows = line_count_gz(p)
        item = {"table": table["table"], "sha_ok": sha == table.get("sha256"), "rows_ok": rows == table.get("rows"), "rows": rows}
        checked.append(item)
        if not item["sha_ok"] or not item["rows_ok"]:
            errors.append({"table": table["table"], "error": "verification failed", **item})
    return {"ok": not errors, "checked_tables": len(checked), "checked": checked, "errors": errors}


def main():
    ap = argparse.ArgumentParser(description="Verify compressed OmniBet data pack.")
    ap.add_argument("--pack-dir", default="../data_packs/football_core_v1")
    args = ap.parse_args()
    print(json.dumps(verify(Path(args.pack_dir)), indent=2))


if __name__ == "__main__":
    main()
