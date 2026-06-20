#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def count_jsonl_gz(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return sum(1 for _ in fh)


def read_jsonl_gz(path: Path, limit: int = 100) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        for idx, line in enumerate(fh):
            if idx >= limit:
                break
            rows.append(json.loads(line))
    return rows


def static_report(root: Path, cache_dir: Path | None) -> Dict[str, Any]:
    contract = read_json(root / "configs/bronze_snapshot_cache.v236.json")
    rust = (root / "rust-core/src/bronze_cache.rs").read_text(encoding="utf-8")
    cli = (root / "rust-core/src/bin/omnibet-bronze-cache.rs").read_text(encoding="utf-8")
    cargo = (root / "rust-core/Cargo.toml").read_text(encoding="utf-8")

    checks: Dict[str, bool] = {
        "schema_ok": contract.get("schema") == "omnibet.bronze_snapshot_cache_contract.v236",
        "codec_jsonl_gzip": contract.get("codec") == "jsonl.gzip",
        "network_free_contract": contract.get("network_policy", {}).get("network_calls_in_ci") is False,
        "credential_free_contract": contract.get("network_policy", {}).get("provider_credentials_required") is False,
        "rust_manifest_type": "BronzeSnapshotCacheManifest" in rust,
        "rust_table_type": "BronzeSnapshotCacheTable" in rust,
        "rust_rows_type": "BronzeSnapshotRows" in rust,
        "rust_writer": "write_bronze_snapshot_cache" in rust,
        "rust_verifier": "verify_bronze_snapshot_cache" in rust,
        "rust_gzip_writer": "GzEncoder" in rust and "Compression::new(6)" in rust,
        "rust_table_hashing": "sha256_file" in rust and "manifest_sha256" in rust,
        "rust_no_network_flag": "network_calls_performed: false" in rust,
        "rust_no_credentials_flag": "credential_values_stored: false" in rust,
        "rust_preserves_unknown_review": "special_combo_unknown" in rust and "needs_mapping_review" in rust,
        "cli_exists": "omnibet-bronze-cache" in cargo and "write_bronze_snapshot_cache" in cli,
    }

    cache_checks: Dict[str, Any] = {}
    if cache_dir is not None and (cache_dir / "manifest.json").exists():
        manifest = read_json(cache_dir / "manifest.json")
        by_table = {row["table"]: row for row in manifest.get("tables", [])}
        cache_checks["manifest_schema_ok"] = manifest.get("schema") == "omnibet.bronze_snapshot_cache.v236"
        cache_checks["manifest_total_rows"] = manifest.get("total_rows") == 53
        cache_checks["manifest_tables"] = len(manifest.get("tables", [])) == 7
        cache_checks["manifest_no_network"] = manifest.get("network_calls_performed") is False
        cache_checks["manifest_no_credentials"] = manifest.get("credential_values_stored") is False
        for row in contract.get("tables", []):
            table = row["table"]
            path = cache_dir / by_table.get(table, {}).get("path", "missing")
            cache_checks[f"table_exists_{table}"] = path.exists()
            cache_checks[f"table_rows_{table}"] = path.exists() and count_jsonl_gz(path) == row["expected_rows"]
        market_path = cache_dir / by_table.get("market_discovery", {}).get("path", "missing")
        if market_path.exists():
            market_rows = read_jsonl_gz(market_path)
            cache_checks["unknown_market_review_preserved"] = any(
                r.get("market_key") == "special_combo_unknown" and r.get("needs_mapping_review") is True
                for r in market_rows
            )
        else:
            cache_checks["unknown_market_review_preserved"] = False

    all_checks = {**checks, **cache_checks}
    return {
        "ok": all(all_checks.values()),
        "schema": "omnibet.bronze_snapshot_cache_smoke.v236",
        "milestone": "v236_bronze_snapshot_cache",
        "checks": all_checks,
        "cache_dir": str(cache_dir) if cache_dir else None,
        "expected_total_rows": 53,
        "safety": {
            "network_calls_in_ci": False,
            "provider_credentials_required": False,
            "credential_values_stored": False,
            "unknown_markets_auto_promoted": False
        }
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--cache-dir", default=None)
    ap.add_argument("--out", default="reports/ci_v236_bronze_snapshot_cache.json")
    args = ap.parse_args()
    report = static_report(Path(args.root), Path(args.cache_dir) if args.cache_dir else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
