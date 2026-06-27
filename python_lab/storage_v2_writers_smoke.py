#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/storage_v2_writers.v311_v320.json")
    sample = read_json(root / "data/storage_v2/v311_v320/storage_v2_writers.sample.json")
    desktop = read_json(root / "tauri-app/src/storage-writers.sample.json")
    docs = (root / "docs/storage_v2_writers_v311_v320.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    cargo = (root / "rust-core/Cargo.toml").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/storage_v2_writers_v311.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v311_v320_storage_v2_writers.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/storage_writers.js").read_text(encoding="utf-8")

    ids = html_ids(html)
    writer_targets = contract.get("writer_targets", [])
    table_manifests = sample.get("sample_table_manifests", [])
    acceptance = contract.get("acceptance", {})
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.storage_v2_writers_contract.v311_v320",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False,
        "sample_safe": sample.get("paper_only") is True and sample.get("credential_values_present") is False and sample.get("live_provider_calls_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "zstd_dependency_added": 'zstd = "0.13"' in cargo,
        "writer_targets_present": {"bronze_raw_jsonl_zstd_writer", "bronze_raw_json_zstd_writer", "ci_runtime_jsonl_gzip_writer", "silver_parquet_zstd_manifest_writer", "gold_parquet_zstd_manifest_writer"}.issubset({row.get("writer_id") for row in writer_targets}),
        "implemented_codecs": {"jsonl.zstd", "json.zstd", "jsonl.gzip"}.issubset(set(contract.get("implemented_codecs_now", []))),
        "parquet_manifest_only": contract.get("manifest_only_codecs_now") == ["parquet.zstd"] and any(row.get("status") == "manifest_writer_only" for row in sample.get("writer_status_rows", [])),
        "table_manifests_have_hashes_rows": all(row.get("row_count", 0) >= 0 and len(str(row.get("content_sha256", ""))) >= 32 for row in table_manifests),
        "sample_codecs_present": {"jsonl.zstd", "jsonl.gzip", "parquet.zstd"}.issubset({row.get("codec") for row in table_manifests}),
        "retention_gates": contract.get("retention_gates", {}).get("delete_requires_content_hash_match") is True and contract.get("retention_gates", {}).get("delete_requires_row_count_match") is True and contract.get("retention_gates", {}).get("delete_requires_promotion_state") == "verified_promoted",
        "desktop_sample_shape": desktop.get("schema") == "omnibet.storage_writers_desktop_sample.v311_v320" and len(desktop.get("writer_rows", [])) >= 5,
        "rust_module_exposed": "pub mod storage_v2_writers_v311;" in rust_lib and "pub use storage_v2_writers_v311::*;" in rust_lib,
        "rust_writers_defined": "write_jsonl_zstd_table" in rust_module and "write_json_zstd_payload" in rust_module and "write_jsonl_gzip_table" in rust_module and "build_parquet_zstd_manifest_only" in rust_module,
        "rust_verify_defined": "verify_storage_writer_bundle" in rust_module and "retention_gate_decision" in rust_module and "validate_storage_v2_writers_contract" in rust_module,
        "html_page_wired": 'data-page="storage-writers"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="storage_writers.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./storage_writers.js" in app_js and "loadAndRenderStorageWritersStatus" in app_js and "load-storage-writers-status" in app_js,
        "renderer_wired": "renderStorageWritersStatus" in renderer and "renderRetention" in renderer and "renderManifests" in renderer,
        "docs_updated": "v311-v320 Rust Storage V2 Writers" in docs and "JSONL.Zstd" in docs and "Parquet.Zstd remains manifest-only" in docs,
        "readme_updated": "v311-v320 Rust Storage V2 writers" in readme,
        "workflow_updated": "storage_v2_writers_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.storage_v2_writers_smoke.v311_v320",
        "milestone": "v311_v320_rust_storage_writers_compression",
        "acceptance": checks,
        "summary": {
            "writer_targets": len(writer_targets),
            "sample_table_manifests": len(table_manifests),
            "implemented_codecs_now": contract.get("implemented_codecs_now", []),
            "manifest_only_codecs_now": contract.get("manifest_only_codecs_now", []),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v311_v320_storage_v2_writers.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
