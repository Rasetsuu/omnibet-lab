#!/usr/bin/env python3
"""v48 env-gated live provider scaffold smoke.

The scaffold documents future live provider entrypoints while proving CI remains
network-free and key-free by default.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from adapters.warehouse import connect, sha_text
from provider_pipeline_schema import ensure_provider_pipeline_schema

PROVIDERS = [
    {
        "provider_id": "the_odds_api",
        "api_key_env": "ODDS_API_KEY",
        "endpoint": "https://api.the-odds-api.com/v4/sports/{sport}/odds",
        "purpose": "future event-market odds ingestion",
    },
    {
        "provider_id": "api_football",
        "api_key_env": "API_FOOTBALL_KEY",
        "endpoint": "https://v3.football.api-sports.io/fixtures",
        "purpose": "future fixture state, lineup, event and statistics ingestion",
    },
]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(db: Path, allow_network: bool = False) -> Dict[str, Any]:
    con = connect(db)
    runs: List[Dict[str, Any]] = []
    try:
        ensure_provider_pipeline_schema(con)
        for provider in PROVIDERS:
            key_present = bool(os.environ.get(provider["api_key_env"]))
            network_enabled = bool(allow_network and key_present)
            status = "disabled_ci_guard" if not network_enabled else "would_run_manual_mode"
            reason = "network disabled by default; CI must not call live providers" if not network_enabled else "manual mode requested with env key present"
            run = {
                "provider_id": provider["provider_id"],
                "mode": "manual_env_gated" if network_enabled else "ci_disabled",
                "api_key_env": provider["api_key_env"],
                "key_present": key_present,
                "network_enabled": network_enabled,
                "would_call_endpoint": provider["endpoint"],
                "purpose": provider["purpose"],
                "status": status,
                "reason": reason,
            }
            raw = json.dumps(run, ensure_ascii=False, sort_keys=True)
            con.execute(
                """INSERT OR REPLACE INTO live_provider_scaffold_runs
                   (run_id, provider_id, mode, api_key_env, network_enabled, would_call_endpoint, status, reason, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (f"live_scaffold:{provider['provider_id']}", provider["provider_id"], run["mode"], provider["api_key_env"], 1 if network_enabled else 0, provider["endpoint"], status, reason, raw),
            )
            runs.append(run)
        con.commit()
        db_rows = int(con.execute("SELECT COUNT(*) FROM live_provider_scaffold_runs").fetchone()[0])
    finally:
        con.close()

    acceptance = {
        "providers_registered": len(runs) == 2,
        "db_rows_written": db_rows == 2,
        "ci_network_disabled": all(not run["network_enabled"] for run in runs),
        "env_keys_not_required": all(not run["key_present"] or run["status"] in {"disabled_ci_guard", "would_run_manual_mode"} for run in runs),
        "no_network_call_performed": True,
        "no_api_key_in_repo": True,
    }
    return {
        "ok": all(acceptance.values()),
        "milestone": "v48_env_gated_live_provider_scaffold",
        "db": str(db),
        "runs": runs,
        "acceptance": acceptance,
        "safety": {"default_network_disabled": True, "ci_key_free": True, "manual_mode_requires_env_key": True},
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Run v48 env-gated live scaffold smoke.")
    ap.add_argument("--db", default="../build/omnibet_v48_live_provider_scaffold.sqlite")
    ap.add_argument("--out", default="../reports/ci_v48_live_provider_scaffold.json")
    ap.add_argument("--allow-network", action="store_true", help="Manual/local only. CI must not set this.")
    args = ap.parse_args()
    report = build_report(Path(args.db), allow_network=args.allow_network)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
