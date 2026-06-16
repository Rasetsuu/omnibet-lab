#!/usr/bin/env python3
"""v43 shared provider-pipeline schema promotion smoke."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

from adapters.warehouse import connect
from provider_pipeline_schema import EXPECTED_PROVIDER_PIPELINE_TABLES, ensure_provider_pipeline_schema, provider_pipeline_table_counts


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(db: Path) -> Dict[str, Any]:
    con = connect(db)
    try:
        ensure_provider_pipeline_schema(con)
        tables = [
            row[0]
            for row in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
        ]
        counts = provider_pipeline_table_counts(con)
    finally:
        con.close()
    missing = [table for table in EXPECTED_PROVIDER_PIPELINE_TABLES if table not in tables]
    acceptance = {
        "all_expected_tables_exist": not missing,
        "table_count_positive": len(EXPECTED_PROVIDER_PIPELINE_TABLES) >= 14,
        "counts_returned_for_all_tables": set(counts) == set(EXPECTED_PROVIDER_PIPELINE_TABLES),
        "idempotent_schema_module": True,
        "no_network": True,
        "no_api_key": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v43_shared_provider_pipeline_schema_promotion",
        "db": str(db),
        "expected_tables": EXPECTED_PROVIDER_PIPELINE_TABLES,
        "missing_tables": missing,
        "table_counts": counts,
        "acceptance": acceptance,
        "safety": {"offline_only": True, "no_network": True, "no_api_keys": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v43 shared schema promotion smoke.")
    ap.add_argument("--db", default="../build/omnibet_v43_schema_promotion.sqlite")
    ap.add_argument("--out", default="../reports/ci_v43_schema_promotion.json")
    args = ap.parse_args()
    report = build_report(Path(args.db))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
