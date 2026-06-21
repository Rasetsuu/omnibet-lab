#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/silver_preview_cache.v244.json")
    rust = (root / "rust-core/src/silver_cache_v244.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    expected = contract.get("expected_offline_cache", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.silver_preview_cache_contract.v244",
        "codec_ok": contract.get("codec") == "jsonl.gzip",
        "layer_ok": contract.get("layer") == "silver_fact_preview",
        "expected_table_count": expected.get("tables") == 1,
        "expected_total_rows": expected.get("total_rows") == 22,
        "expected_preview_only": expected.get("preview_only") is True,
        "training_forbidden": expected.get("training_dataset_promotion_allowed") is False,
        "credential_values_absent": expected.get("credential_values_stored") is False,
        "network_calls_absent": expected.get("network_calls_performed") is False,
        "verify_manifest_sha": contract.get("verification_requirements", {}).get("manifest_sha256_required") is True,
        "verify_table_sha": contract.get("verification_requirements", {}).get("table_sha256_required") is True,
        "verify_rows": contract.get("verification_requirements", {}).get("row_count_check_required") is True,
        "rust_types": "SilverPreviewCacheManifest" in rust and "SilverPreviewCacheTable" in rust,
        "rust_writer": "write_silver_preview_cache" in rust and "write_silver_preview_cache_from_offline_samples" in rust,
        "rust_verifier": "verify_silver_preview_cache" in rust and "SilverPreviewCacheVerifyResult" in rust,
        "rust_table_name": "silver_fact_preview_rows" in rust,
        "rust_hashes": "manifest_sha256" in rust and "sha256_file" in rust,
        "rust_safety_flags": "training_dataset_promotion_allowed: false" in rust and "network_calls_performed: false" in rust,
        "rust_row_test": "assert_eq!(manifest.total_rows, 22)" in rust and "special_combo_unknown" in rust,
        "lib_exports": "pub mod silver_cache_v244;" in lib and "pub use silver_cache_v244::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.silver_preview_cache_smoke.v244",
        "milestone": "v244_silver_preview_cache",
        "acceptance": checks,
        "expected_offline_cache": expected,
        "safety": {
            "preview_only": True,
            "training_dataset_promotion_allowed": False,
            "network_calls_performed": False,
            "credential_values_stored": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v244_silver_preview_cache.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
