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


def hash_shape(value: str) -> bool:
    return len(value) == 64 and value.isalnum()


def build_report(root: Path) -> Dict[str, Any]:
    manifest = read_json(root / "configs/historical_source_files.v247.json")
    rust = (root / "rust-core/src/historical_sources_v247.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    files = manifest.get("files", [])
    checks = {
        "schema_ok": manifest.get("schema") == "omnibet.historical_source_file_manifest.v247",
        "offline_only": manifest.get("offline_only") is True,
        "network_disabled": manifest.get("network_calls_allowed") is False,
        "paper_only": manifest.get("paper_only") is True,
        "later_file_check_required": manifest.get("file_exists_check_required_for_real_import") is True,
        "file_count": len(files) == 6,
        "row_count": sum(row.get("row_count", 0) for row in files) == 600,
        "hash_shape": all(hash_shape(row.get("sha256", "")) for row in files),
        "safe_paths": all(row.get("relative_path") and not row.get("relative_path", "").startswith("/") for row in files),
        "timestamps_present": all(row.get("point_in_time_timestamp_present") is True for row in files),
        "identity_required": all(row.get("provider_identity_mapping_required") is True for row in files),
        "odds_mapping_required": all(row.get("market_mapping_required") is True for row in files if row.get("source_kind") == "odds"),
        "no_secret_rows": all(row.get("credentials_stored") is False for row in files),
        "no_network_rows": all(row.get("network_calls_performed") is False for row in files),
        "imports_wait": all(row.get("import_allowed_now") is False for row in files),
        "rust_module_present": "HistoricalSourceFileContract" in rust and "validate_historical_source_files_against_plan" in rust,
        "lib_exports": "pub mod historical_sources_v247;" in lib and "pub use historical_sources_v247::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_source_files_smoke.v247",
        "milestone": "v247_historical_source_files",
        "acceptance": checks,
        "summary": {
            "files": len(files),
            "total_rows": sum(row.get("row_count", 0) for row in files),
            "offline_only": True,
            "network_calls_allowed": False,
            "import_allowed_now": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v247_historical_source_files.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
