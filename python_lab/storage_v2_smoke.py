#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_SILVER = {
    "competitions",
    "seasons",
    "teams",
    "players",
    "matches",
    "lineups",
    "match_events",
    "odds_snapshots",
    "market_catalog",
    "market_aliases",
    "settlement_rules",
    "provider_identity_map",
}

REQUIRED_GOLD = {
    "gold_match_features",
    "gold_team_snapshots",
    "gold_player_snapshots",
    "gold_market_features",
    "gold_live_state_features",
    "labels",
    "settlements",
    "paper_ledger",
    "clv_reports",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/storage_v2_big_data.v233.json")
    current_manifest = read_json(root / "data_packs/football_core_v1/manifest.json")
    rust_storage = (root / "rust-core/src/storage_v2.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")

    bronze = contract.get("layers", {}).get("bronze_raw_snapshots", {})
    silver = contract.get("layers", {}).get("silver_canonical_facts", {})
    gold = contract.get("layers", {}).get("gold_training_features", {})
    manifest_req = contract.get("manifest_requirements", {})
    safety = contract.get("training_safety", {})
    acceptance = contract.get("acceptance", {})

    current_policy = current_manifest.get("storage_policy", {})
    current_tables = current_manifest.get("tables", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.storage_v2_big_data.v233",
        "keeps_current_pack_compat": contract.get("compatibility", {}).get("current_runtime_pack_codec") == "jsonl.gzip" and contract.get("compatibility", {}).get("keep_jsonl_gzip_for_ci_and_small_runtime_packs") is True,
        "adds_parquet_zstd": contract.get("compatibility", {}).get("add_parquet_zstd_for_large_history_and_training") is True,
        "bronze_temporary": bronze.get("retention_days_default") == 30 and bronze.get("delete_or_archive_after_promotion") is True,
        "bronze_no_credentials": bronze.get("credential_values_allowed") is False,
        "silver_parquet_zstd": silver.get("default_codec") == "parquet.zstd",
        "gold_parquet_zstd": gold.get("default_codec") == "parquet.zstd",
        "silver_tables_complete": REQUIRED_SILVER.issubset(set(silver.get("tables", []))),
        "gold_tables_complete": REQUIRED_GOLD.issubset(set(gold.get("tables", []))),
        "manifest_requires_lineage": manifest_req.get("source_lineage_required") is True and manifest_req.get("content_hashes_required") is True,
        "manifest_requires_time_boundaries": manifest_req.get("prediction_time_boundary_required") is True and manifest_req.get("observed_at_boundary_required") is True,
        "training_no_random_split": safety.get("random_split_allowed") is False,
        "training_walk_forward": safety.get("walk_forward_required") is True,
        "training_observed_before_prediction": safety.get("features_must_be_observed_before_prediction_time") is True,
        "labels_after_settlement": safety.get("labels_only_after_settlement") is True,
        "acceptance_reproducible": acceptance.get("canonical_facts_and_features_are_reproducible") is True,
        "acceptance_no_secret_storage": acceptance.get("credential_values_never_stored") is True,
        "current_manifest_has_policy": current_policy.get("current_codec") == "jsonl.gzip" and current_policy.get("future_preferred_codec") == "parquet.zstd",
        "current_manifest_has_compression_stats": current_manifest.get("overall_compression_ratio") is not None and current_manifest.get("total_compressed_bytes", 0) > 0,
        "current_tables_are_compressed": all(row.get("compression") == "gzip" for row in current_tables),
        "rust_module_exposed": "pub mod storage_v2;" in rust_lib and "pub use storage_v2::*;" in rust_lib,
        "rust_contract_structs": "StorageV2Contract" in rust_storage and "validate_storage_v2_contract" in rust_storage,
        "rust_safety_checks": "random_split_allowed" in rust_storage and "parquet.zstd" in rust_storage and "credential values" in rust_storage,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.storage_v2_smoke.v233",
        "milestone": "v233_storage_v2_big_data_foundation",
        "acceptance": checks,
        "current_pack": {
            "pack_name": current_manifest.get("pack_name"),
            "format": current_manifest.get("format"),
            "current_codec": current_policy.get("current_codec"),
            "future_preferred_codec": current_policy.get("future_preferred_codec"),
            "total_rows": current_manifest.get("total_rows"),
            "total_uncompressed_jsonl_bytes": current_manifest.get("total_uncompressed_jsonl_bytes"),
            "total_compressed_bytes": current_manifest.get("total_compressed_bytes"),
            "overall_compression_ratio": current_manifest.get("overall_compression_ratio"),
        },
        "safety": {
            "credential_values_stored": False,
            "random_split_allowed": False,
            "walk_forward_required": True,
            "jsonl_gzip_compat_preserved": True,
            "large_training_codec": "parquet.zstd",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v233_storage_v2.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
