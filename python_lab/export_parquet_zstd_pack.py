#!/usr/bin/env python3
"""Optional v27 Parquet+ZSTD pack exporter.

This is a local-scale storage path, not the CI/default pack format yet.

The script has two modes:

1. `--plan-only`: dependency-free; inspects a SQLite warehouse and writes a
   storage plan/size-readiness report. CI uses this mode.
2. export mode: requires `pyarrow`; writes one Parquet+ZSTD file per table plus
   a manifest. This is intended for local heavy warehouses.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_HEAVY_TABLES = [
    "competitions",
    "seasons",
    "teams",
    "players",
    "matches_norm",
    "match_events",
    "lineups",
    "odds_snapshots",
    "entity_identity_candidates",
    "gold_team_snapshots",
    "gold_match_features",
    "gold_goal_timing_features",
    "gold_match_phase_features",
    "gold_player_snapshots",
    "gold_market_features",
]

PARTITION_HINTS = {
    "matches_norm": ["sport", "competition_id", "season_id"],
    "match_events": ["sport", "competition_id", "season_id"],
    "lineups": ["sport", "competition_id", "season_id"],
    "players": ["source_id"],
    "odds_snapshots": ["sport", "market_id", "source_id"],
    "gold_market_features": ["market_id"],
    "gold_match_phase_features": ["settlement_scope"],
}


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


def table_columns(con: sqlite3.Connection, table: str) -> List[str]:
    return [r["name"] for r in table_schema(con, table)]


def table_count(con: sqlite3.Connection, table: str) -> int:
    if not table_exists(con, table):
        return 0
    return int(con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0])


def estimate_sqlite_payload_bytes(con: sqlite3.Connection, table: str, sample_rows: int = 200) -> Dict[str, Any]:
    """Estimate row payload size using compact JSON samples.

    This is not the Parquet size. It gives a stable rough comparator even when
    pyarrow is not installed.
    """
    if not table_exists(con, table):
        return {"sample_rows": 0, "sample_jsonl_bytes": 0, "estimated_jsonl_bytes": 0}
    cols = table_columns(con, table)
    rows = con.execute(f'SELECT * FROM "{table}" LIMIT ?', (sample_rows,)).fetchall()
    raw = 0
    for row in rows:
        obj = {cols[i]: row[i] for i in range(len(cols))}
        raw += len(json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")) + 1
    total = table_count(con, table)
    estimated = int((raw / max(1, len(rows))) * total) if rows else 0
    return {"sample_rows": len(rows), "sample_jsonl_bytes": raw, "estimated_jsonl_bytes": estimated}


def available_pyarrow() -> Dict[str, Any]:
    try:
        import pyarrow as pa  # type: ignore
        import pyarrow.parquet as pq  # noqa: F401  # type: ignore

        return {"available": True, "version": getattr(pa, "__version__", "unknown")}
    except Exception as e:
        return {"available": False, "error": str(e)}


def sqlite_type_to_arrow(sqlite_type: str):
    import pyarrow as pa  # type: ignore

    t = (sqlite_type or "").upper()
    if "INT" in t or t == "BOOLEAN":
        return pa.int64()
    if any(x in t for x in ["REAL", "FLOA", "DOUB", "NUM"]):
        return pa.float64()
    if "BLOB" in t:
        return pa.binary()
    return pa.string()


def arrow_schema_from_sqlite(con: sqlite3.Connection, table: str):
    import pyarrow as pa  # type: ignore

    fields = []
    for col in table_schema(con, table):
        fields.append(pa.field(col["name"], sqlite_type_to_arrow(col.get("type", ""))))
    return pa.schema(fields)


def coerce_value(value: Any, sqlite_type: str) -> Any:
    if value is None:
        return None
    t = (sqlite_type or "").upper()
    if "INT" in t or t == "BOOLEAN":
        try:
            return int(value)
        except Exception:
            return None
    if any(x in t for x in ["REAL", "FLOA", "DOUB", "NUM"]):
        try:
            return float(value)
        except Exception:
            return None
    if "BLOB" in t:
        return value
    return str(value)


def export_table_parquet(con: sqlite3.Connection, table: str, out_path: Path, zstd_level: int, row_group_size: int) -> Dict[str, Any]:
    import pyarrow as pa  # type: ignore
    import pyarrow.parquet as pq  # type: ignore

    out_path.parent.mkdir(parents=True, exist_ok=True)
    schema_info = table_schema(con, table)
    cols = [c["name"] for c in schema_info]
    types_by_col = {c["name"]: c.get("type", "") for c in schema_info}
    schema = arrow_schema_from_sqlite(con, table)

    cursor = con.execute(f'SELECT * FROM "{table}"')
    writer = None
    rows_written = 0
    try:
        while True:
            rows = cursor.fetchmany(row_group_size)
            if not rows:
                break
            batch = []
            for row in rows:
                batch.append({col: coerce_value(row[i], types_by_col[col]) for i, col in enumerate(cols)})
            arrow_table = pa.Table.from_pylist(batch, schema=schema)
            if writer is None:
                writer = pq.ParquetWriter(out_path, schema, compression="zstd", compression_level=zstd_level, use_dictionary=True)
            writer.write_table(arrow_table, row_group_size=row_group_size)
            rows_written += len(batch)

        if writer is None:
            empty = pa.Table.from_pylist([], schema=schema)
            pq.write_table(empty, out_path, compression="zstd", compression_level=zstd_level, use_dictionary=True)
    finally:
        if writer is not None:
            writer.close()

    pf = pq.ParquetFile(out_path)
    return {
        "table": table,
        "path": str(out_path),
        "rows": rows_written,
        "parquet_rows": pf.metadata.num_rows,
        "row_groups": pf.metadata.num_row_groups,
        "compressed_bytes": out_path.stat().st_size,
        "compression": "zstd",
        "zstd_level": zstd_level,
        "sha256": sha256_file(out_path),
        "schema": schema_info,
        "partition_hints": PARTITION_HINTS.get(table, []),
    }


def build_plan(db: Path, tables: List[str], zstd_level: int, row_group_size: int) -> Dict[str, Any]:
    con = sqlite3.connect(str(db))
    try:
        planned = []
        skipped = []
        for table in tables:
            if not table_exists(con, table):
                skipped.append({"table": table, "reason": "missing"})
                continue
            payload = estimate_sqlite_payload_bytes(con, table)
            planned.append({
                "table": table,
                "rows": table_count(con, table),
                "schema": table_schema(con, table),
                "estimated_jsonl_bytes": payload["estimated_jsonl_bytes"],
                "sample_rows": payload["sample_rows"],
                "partition_hints": PARTITION_HINTS.get(table, []),
            })
    finally:
        con.close()
    return {
        "ok": True,
        "mode": "plan_only",
        "milestone": "v27_parquet_zstd_storage_scale",
        "created_at": utc_now(),
        "source_db": str(db),
        "format": "omnibet.storage_plan.v1",
        "target_format": "parquet",
        "target_compression": "zstd",
        "zstd_level": zstd_level,
        "row_group_size": row_group_size,
        "pyarrow": available_pyarrow(),
        "tables": planned,
        "skipped": skipped,
        "total_rows": sum(t["rows"] for t in planned),
        "estimated_total_jsonl_bytes": sum(t["estimated_jsonl_bytes"] for t in planned),
        "policy": {
            "ci": "plan-only, dependency-free",
            "local_heavy": "requires pyarrow; writes Parquet+ZSTD",
            "runtime": "does not ship raw warehouse; ships compact model artifacts and metadata",
        },
    }


def export_pack(db: Path, out_dir: Path, tables: List[str], pack_name: str, zstd_level: int, row_group_size: int) -> Dict[str, Any]:
    pyarrow_info = available_pyarrow()
    if not pyarrow_info.get("available"):
        return {
            "ok": False,
            "error": "pyarrow is required for Parquet export. Install optional storage dependencies first.",
            "pyarrow": pyarrow_info,
            "hint": "python -m pip install -r requirements-storage.txt",
        }

    out_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = out_dir / "tables"
    tables_dir.mkdir(exist_ok=True)
    con = sqlite3.connect(str(db))
    try:
        exported = []
        skipped = []
        for table in tables:
            if not table_exists(con, table):
                skipped.append({"table": table, "reason": "missing"})
                continue
            exported.append(export_table_parquet(con, table, tables_dir / f"{table}.parquet", zstd_level, row_group_size))
    finally:
        con.close()

    manifest = {
        "ok": True,
        "pack_name": pack_name,
        "created_at": utc_now(),
        "source_db": str(db),
        "format": "omnibet.parquet_pack.v1",
        "codec": "parquet.zstd",
        "zstd_level": zstd_level,
        "row_group_size": row_group_size,
        "pyarrow": pyarrow_info,
        "tables": exported,
        "skipped": skipped,
        "total_rows": sum(t["rows"] for t in exported),
        "total_compressed_bytes": sum(t["compressed_bytes"] for t in exported),
        "storage_policy": {
            "role": "local heavy analytical warehouse pack",
            "query_engines": ["pyarrow", "duckdb", "polars"],
            "next_runtime_step": "export compact Rust-loadable model artifact after training",
        },
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    manifest["manifest_sha256"] = sha256_file(manifest_path)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def parse_tables(value: str) -> List[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def main() -> None:
    ap = argparse.ArgumentParser(description="Export or plan an OmniBet Parquet+ZSTD local warehouse pack.")
    ap.add_argument("--db", required=True)
    ap.add_argument("--out-dir", default="../build/v27_parquet_zstd_pack")
    ap.add_argument("--pack-name", default="football_v27_parquet_zstd")
    ap.add_argument("--tables", default=",".join(DEFAULT_HEAVY_TABLES), help="Comma-separated table list.")
    ap.add_argument("--zstd-level", type=int, default=6)
    ap.add_argument("--row-group-size", type=int, default=100_000)
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--out", default="", help="Optional JSON report path for plan-only or export summary.")
    args = ap.parse_args()

    tables = parse_tables(args.tables)
    if args.plan_only:
        result = build_plan(Path(args.db), tables, args.zstd_level, args.row_group_size)
    else:
        result = export_pack(Path(args.db), Path(args.out_dir), tables, args.pack_name, args.zstd_level, args.row_group_size)
        if not result.get("ok"):
            print(json.dumps(result, indent=2))
            raise SystemExit(2)

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
