#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def pyarrow_status() -> dict:
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # noqa: F401  # type: ignore
        return {"available": True, "version": getattr(pa, "__version__", "unknown")}
    except Exception as e:
        return {"available": False, "error": str(e)}


def check_pack(pack_dir: Path, manifest_only: bool = False) -> dict:
    manifest_path = pack_dir / "manifest.json"
    if not manifest_path.exists():
        return {"ok": False, "error": "missing manifest"}
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    pa_info = pyarrow_status()
    parquet_module = None
    if pa_info.get("available") and not manifest_only:
        import pyarrow.parquet as parquet_module  # type: ignore

    errors = []
    checked = []
    for item in manifest.get("tables", []):
        table_name = item.get("table")
        p = Path(item.get("path", ""))
        if not p.is_absolute():
            p = pack_dir / p
        if not p.exists():
            p = pack_dir / "tables" / f"{table_name}.parquet"
        if not p.exists():
            errors.append({"table": table_name, "error": "file missing"})
            continue
        row = {"table": table_name, "hash_ok": file_hash(p) == item.get("sha256"), "size_bytes": p.stat().st_size}
        if parquet_module is not None:
            meta = parquet_module.ParquetFile(p).metadata
            row["rows_expected"] = item.get("rows")
            row["rows_actual"] = meta.num_rows
            row["rows_ok"] = meta.num_rows == item.get("rows")
            row["row_groups"] = meta.num_row_groups
        checked.append(row)
        if row.get("hash_ok") is False or row.get("rows_ok") is False:
            errors.append({"table": table_name, "error": "check failed", **row})
    return {"ok": not errors, "manifest_only": manifest_only, "pyarrow": pa_info, "checked_tables": len(checked), "checked": checked, "errors": errors}


def main() -> None:
    ap = argparse.ArgumentParser(description="Check an OmniBet Parquet+ZSTD pack.")
    ap.add_argument("--pack-dir", required=True)
    ap.add_argument("--manifest-only", action="store_true")
    args = ap.parse_args()
    result = check_pack(Path(args.pack_dir), args.manifest_only)
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
