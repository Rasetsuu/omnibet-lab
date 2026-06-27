#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def ordered(left: Any, right: Any) -> bool:
    left_dt = parse_utc(left)
    right_dt = parse_utc(right)
    return left_dt is not None and right_dt is not None and left_dt <= right_dt


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = [
        '"api_key":',
        '"secret":',
        '"bearer_token":',
        '"credential_value":',
        "secret_value",
        "bearer ",
        "sk-",
    ]
    return not any(marker in serialized for marker in forbidden)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/storage_v2_compression.v266_v270.json")
    sample = read_json(root / "data/storage_v2/v266_v270/storage_v2_compression.sample.json")
    docs = (root / "docs/storage_v2_compression_v266_v270.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/storage_v2_compression_v266.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v266_v270_storage_v2_compression.yml").read_text(encoding="utf-8")

    runtime = contract.get("runtime_compatibility", {})
    layers = contract.get("layers", {})
    bronze = layers.get("bronze_raw_snapshots", {})
    silver = layers.get("silver_canonical_facts", {})
    gold = layers.get("gold_training_features", {})
    cache_contract = contract.get("provider_cache_manifest", {})
    writer_plan = contract.get("writer_migration_plan", {})
    loader = contract.get("walk_forward_dataset_loader", {})
    acceptance = contract.get("acceptance", {})

    bronze_sample = sample.get("bronze_raw_snapshot_manifest", {})
    silver_sample = sample.get("silver_table_manifest", {})
    gold_sample = sample.get("gold_feature_manifest", {})
    cache_sample = sample.get("provider_cache_manifest", {})
    wf_sample = sample.get("walk_forward_dataset_window", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.storage_v2_compression_contract.v266_v270",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "no_live_calls_or_credentials": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and sample.get("credential_values_present") is False and no_secret_values(sample),
        "runtime_compat_preserved": runtime.get("existing_pack_codec") == "jsonl.gzip" and runtime.get("keep_jsonl_gzip_for_ci_runtime_packs") is True,
        "bronze_contract_zstd_temporary": bronze.get("codec") == "jsonl.zstd" and bronze.get("retention_days_default") == 30 and bronze.get("delete_raw_after_verified_promotion") is True,
        "bronze_manifest_required_fields": required_subset(bronze.get("required_manifest_fields", []), bronze_sample),
        "bronze_sample_order_and_size": ordered(bronze_sample.get("observed_at"), bronze_sample.get("captured_at")) and bronze_sample.get("compressed_bytes", 0) < bronze_sample.get("uncompressed_bytes", 0),
        "silver_gold_parquet_zstd": silver.get("codec") == "parquet.zstd" and gold.get("codec") == "parquet.zstd" and silver_sample.get("codec") == "parquet.zstd" and gold_sample.get("codec") == "parquet.zstd",
        "silver_gold_long_term": silver.get("keep_long_term") is True and gold.get("keep_long_term") is True and silver_sample.get("keep_long_term") is True and gold_sample.get("keep_long_term") is True,
        "provider_cache_rust_target": cache_contract.get("target_runtime") == "rust" and cache_sample.get("codec") == "jsonl.zstd",
        "provider_cache_required_fields": required_subset(cache_contract.get("required_fields", []), cache_sample),
        "provider_cache_forbids_credentials": set(["api_key", "secret", "bearer_token", "credential_value"]).issubset(set(cache_contract.get("forbidden_fields", []))),
        "writer_plan_rust_target": writer_plan.get("target_runtime") == "rust" and "content_hashes" in writer_plan.get("writer_outputs", []) and "leakage_boundary_report" in writer_plan.get("writer_outputs", []),
        "walk_forward_rust_no_random": loader.get("target_runtime") == "rust" and loader.get("random_split_allowed") is False and wf_sample.get("random_split_allowed") is False,
        "walk_forward_windows_ordered": ordered(wf_sample.get("train_start"), wf_sample.get("train_end")) and ordered(wf_sample.get("train_end"), wf_sample.get("validation_start")) and ordered(wf_sample.get("validation_end"), wf_sample.get("test_start")),
        "walk_forward_safety_checks": set(loader.get("required_safety_checks", [])).issubset(set(wf_sample.get("safety_checks", []))),
        "rust_module_exposed": "pub mod storage_v2_compression_v266;" in rust_lib and "pub use storage_v2_compression_v266::*;" in rust_lib,
        "rust_module_validation": "StorageV2CompressionContract" in rust_module and "validate_storage_v2_compression_contract" in rust_module and "jsonl.zstd" in rust_module and "parquet.zstd" in rust_module and "random_split_allowed" in rust_module,
        "docs_updated": "v266-v270 Storage V2 Compression Foundation" in docs and "JSONL.Zstd" in docs and "Parquet.Zstd" in docs,
        "readme_updated": "v266-v270 storage v2 compression foundation" in readme,
        "workflow_updated": "storage_v2_compression_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 8,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.storage_v2_compression_smoke.v266_v270",
        "milestone": "v266_v270_storage_v2_compression_foundation",
        "acceptance": checks,
        "summary": {
            "bronze_codec": bronze.get("codec"),
            "silver_codec": silver.get("codec"),
            "gold_codec": gold.get("codec"),
            "runtime_compat_codec": runtime.get("existing_pack_codec"),
            "rust_targeted": True,
            "ready_for_real_training": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v266_v270_storage_v2_compression.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
