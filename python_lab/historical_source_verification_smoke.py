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
    contract = read_json(root / "configs/historical_source_verification.v248.json")
    rust = (root / "rust-core/src/historical_verify_v248.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    checks_cfg = contract.get("verification_checks", {})
    acceptance_cfg = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.historical_source_verification_contract.v248",
        "offline_only": contract.get("offline_only") is True,
        "network_disabled": contract.get("network_calls_allowed") is False,
        "paper_only": contract.get("paper_only") is True,
        "import_still_disabled": contract.get("import_allowed_after_verification") is False,
        "promotion_still_disabled": contract.get("promotion_allowed_after_verification") is False,
        "all_verification_checks_enabled": all(checks_cfg.values()) and len(checks_cfg) == 7,
        "supported_codecs": contract.get("supported_codecs") == ["csv", "json", "jsonl.gzip"],
        "acceptance_enabled": all(acceptance_cfg.values()) and len(acceptance_cfg) == 7,
        "rust_report_type": "HistoricalSourceVerificationReport" in rust,
        "rust_verifier": "verify_historical_source_files" in rust and "verify_one_source_file" in rust,
        "rust_sha256": "sha256_path" in rust and "Sha256::new" in rust,
        "rust_row_count": "count_rows_for_codec" in rust,
        "rust_path_guard": "ParentDir" in rust and "relative path must not contain parent traversal" in rust,
        "rust_no_promotion": "promotion_allowed: false" in rust and "import_allowed_now: false" in rust,
        "rust_tests": "verifies_existing_file_hash_and_rows" in rust and "rejects_path_traversal" in rust,
        "lib_exports": "pub mod historical_verify_v248;" in lib and "pub use historical_verify_v248::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_source_verification_smoke.v248",
        "milestone": "v248_local_source_verification",
        "acceptance": checks,
        "summary": {
            "offline_only": True,
            "network_calls_allowed": False,
            "import_allowed_after_verification": False,
            "promotion_allowed_after_verification": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v248_historical_source_verification.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
