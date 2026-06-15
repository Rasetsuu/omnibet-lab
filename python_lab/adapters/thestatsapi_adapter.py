#!/usr/bin/env python3
"""
TheStatsAPI adapter for OmniBet Lab v4.

This adapter is API-key gated and quota-aware by design.

Environment:
  THESTATSAPI_KEY=...

Examples:
  python -m adapters.thestatsapi_adapter status --db ../build/omnibet.sqlite
  python -m adapters.thestatsapi_adapter get --endpoint /competitions --db ../build/omnibet.sqlite
  python -m adapters.thestatsapi_adapter sync-competitions --db ../build/omnibet.sqlite --limit-pages 2

Notes:
- Base URL is https://api.thestatsapi.com/api/football
- This adapter stores raw JSON in bronze_blobs first.
- Normalization is intentionally conservative and should be extended as endpoint
  schemas are observed with a real API key.
"""
from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional

from .warehouse import connect, finish_run, register_default_sources, start_run, store_bronze, table_counts


SOURCE_ID = "thestatsapi_football"
BASE_URL = "https://api.thestatsapi.com/api/football"
API_KEY_ENV = "THESTATSAPI_KEY"


class TheStatsAPIError(RuntimeError):
    pass


def api_key() -> str:
    key = os.environ.get(API_KEY_ENV, "").strip()
    if not key:
        raise TheStatsAPIError(f"Missing API key. Set {API_KEY_ENV}=...")
    return key


def request_json(endpoint: str, params: Optional[dict] = None, sleep_after: float = 0.0) -> Any:
    endpoint = endpoint if endpoint.startswith("/") else "/" + endpoint
    url = BASE_URL + endpoint
    if params:
        url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {api_key()}",
            "Content-Type": "application/json",
            "User-Agent": "OmniBetLab/0.4",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as res:
            body = res.read().decode("utf-8")
            if sleep_after > 0:
                time.sleep(sleep_after)
            return json.loads(body)
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise TheStatsAPIError(f"HTTP {e.code}: {body[:500]}") from e
    except urllib.error.URLError as e:
        raise TheStatsAPIError(f"Network error: {e}") from e


def extract_items(payload: Any) -> list:
    """Try common pagination shapes without assuming exact endpoint schema."""
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ["data", "items", "results", "competitions", "matches", "players", "teams", "odds"]:
        if isinstance(payload.get(key), list):
            return payload[key]
    return []


def pagination_has_more(payload: Any, page: int) -> bool:
    if not isinstance(payload, dict):
        return False
    meta = payload.get("meta") or payload.get("pagination") or {}
    if not isinstance(meta, dict):
        return False
    if "has_more" in meta:
        return bool(meta["has_more"])
    total_pages = meta.get("total_pages") or meta.get("last_page")
    if total_pages is not None:
        try:
            return page < int(total_pages)
        except Exception:
            return False
    return False


def status(db_path: Path) -> dict:
    con = connect(db_path)
    register_default_sources(con)
    out = {
        "source_id": SOURCE_ID,
        "base_url": BASE_URL,
        "api_key_env": API_KEY_ENV,
        "api_key_present": bool(os.environ.get(API_KEY_ENV)),
        "counts": table_counts(con),
    }
    con.close()
    return out


def generic_get(db_path: Path, endpoint: str, params: dict, entity_type: str) -> dict:
    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    try:
        payload = request_json(endpoint, params=params)
        items = extract_items(payload)
        store_bronze(con, SOURCE_ID, entity_type, payload, entity_id=endpoint.strip("/").replace("/", "_"), metadata={"endpoint": endpoint, "params": params})
        finish_run(con, run_id, "success", rows_seen=len(items), rows_inserted=1, report={"endpoint": endpoint, "params": params})
        return {"run_id": run_id, "rows_seen": len(items), "stored_payload": True, "endpoint": endpoint}
    except Exception as e:
        finish_run(con, run_id, "error", error=str(e), report={"endpoint": endpoint, "params": params})
        raise
    finally:
        con.close()


def sync_paginated(db_path: Path, endpoint: str, entity_type: str, limit_pages: int = 1, per_page: int = 50, extra_params: Optional[dict] = None) -> dict:
    con = connect(db_path)
    register_default_sources(con)
    run_id = start_run(con, SOURCE_ID)
    rows_seen = 0
    pages = 0
    try:
        for page in range(1, limit_pages + 1):
            params = {"page": page, "per_page": per_page}
            if extra_params:
                params.update(extra_params)
            payload = request_json(endpoint, params=params, sleep_after=0.25)
            items = extract_items(payload)
            rows_seen += len(items)
            pages += 1
            store_bronze(con, SOURCE_ID, entity_type, payload, entity_id=f"{endpoint.strip('/').replace('/', '_')}:page:{page}", metadata={"endpoint": endpoint, "page": page, "per_page": per_page})
            if not pagination_has_more(payload, page):
                break
        finish_run(con, run_id, "success", rows_seen=rows_seen, rows_inserted=pages, report={"endpoint": endpoint, "pages": pages})
        return {"run_id": run_id, "endpoint": endpoint, "pages": pages, "rows_seen": rows_seen}
    except Exception as e:
        finish_run(con, run_id, "error", rows_seen=rows_seen, rows_inserted=pages, error=str(e), report={"endpoint": endpoint, "pages": pages})
        raise
    finally:
        con.close()


def main():
    ap = argparse.ArgumentParser(description="TheStatsAPI adapter.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_status = sub.add_parser("status")
    p_status.add_argument("--db", default="../build/omnibet.sqlite")

    p_get = sub.add_parser("get")
    p_get.add_argument("--db", default="../build/omnibet.sqlite")
    p_get.add_argument("--endpoint", required=True)
    p_get.add_argument("--entity-type", default="generic")
    p_get.add_argument("--param", action="append", default=[], help="key=value query param")

    p_comp = sub.add_parser("sync-competitions")
    p_comp.add_argument("--db", default="../build/omnibet.sqlite")
    p_comp.add_argument("--limit-pages", type=int, default=1)
    p_comp.add_argument("--per-page", type=int, default=50)

    p_matches = sub.add_parser("sync-matches")
    p_matches.add_argument("--db", default="../build/omnibet.sqlite")
    p_matches.add_argument("--limit-pages", type=int, default=1)
    p_matches.add_argument("--per-page", type=int, default=50)
    p_matches.add_argument("--competition-id", default=None)
    p_matches.add_argument("--season-id", default=None)
    p_matches.add_argument("--from-date", default=None)
    p_matches.add_argument("--to-date", default=None)

    args = ap.parse_args()
    db = Path(args.db)

    if args.cmd == "status":
        out = status(db)
    elif args.cmd == "get":
        params = {}
        for x in args.param:
            if "=" in x:
                k, v = x.split("=", 1)
                params[k] = v
        out = generic_get(db, args.endpoint, params, args.entity_type)
    elif args.cmd == "sync-competitions":
        out = sync_paginated(db, "/competitions", "competitions", args.limit_pages, args.per_page)
    else:
        params = {
            "competition_id": args.competition_id,
            "season_id": args.season_id,
            "from": args.from_date,
            "to": args.to_date,
        }
        out = sync_paginated(db, "/matches", "matches", args.limit_pages, args.per_page, params)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
