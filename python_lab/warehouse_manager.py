#!/usr/bin/env python3
"""
OmniBet Lab v4 warehouse manager.

Commands are safe and mostly offline:
  init/status/register sources
  run local Football-Data CSV import
  inspect table counts

API/live adapters live in python_lab/adapters and only call remote services when
you explicitly run them and provide API keys.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from adapters.warehouse import connect, register_default_sources, table_counts


def init(db: Path) -> dict:
    con = connect(db)
    register_default_sources(con)
    counts = table_counts(con)
    con.close()
    return {"db": str(db), "counts": counts}


def status(db: Path) -> dict:
    con = connect(db)
    register_default_sources(con)
    srcs = con.execute(
        """SELECT source_id, sport, source_type, display_name, update_mode, url, api_key_env, enabled,
                  min_interval_minutes, notes
           FROM source_registry ORDER BY sport, source_id"""
    ).fetchall()
    counts = table_counts(con)
    con.close()
    return {
        "counts": counts,
        "sources": [
            {
                "source_id": r[0], "sport": r[1], "source_type": r[2], "display_name": r[3],
                "update_mode": r[4], "url": r[5], "api_key_env": r[6], "enabled": bool(r[7]),
                "min_interval_minutes": r[8], "notes": r[9],
            }
            for r in srcs
        ],
    }


def main():
    ap = argparse.ArgumentParser(description="Manage OmniBet v4 warehouse.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_init = sub.add_parser("init")
    p_init.add_argument("--db", default="../build/omnibet.sqlite")
    p_status = sub.add_parser("status")
    p_status.add_argument("--db", default="../build/omnibet.sqlite")
    args = ap.parse_args()
    if args.cmd == "init":
        out = init(Path(args.db))
    else:
        out = status(Path(args.db))
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
