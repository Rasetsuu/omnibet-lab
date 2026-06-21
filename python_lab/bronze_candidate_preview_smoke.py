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
    contract = read_json(root / "configs/bronze_candidate_preview.v249.json")
    rust = (root / "rust-core/src/bronze_candidate_v249.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    row_fields = contract.get("row_fields_required", {})
    acceptance_cfg = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.bronze_candidate_preview_contract.v249",
        "offline_only": contract.get("offline_only") is True,
        "network_disabled": contract.get("network_calls_allowed") is False,
        "quarantine_only": contract.get("quarantine_only") is True,
        "import_disabled": contract.get("import_allowed_now") is False,
        "promotion_disabled": contract.get("promotion_allowed") is False,
        "evaluation_disabled": contract.get("evaluation_allowed") is False,
        "training_disabled": contract.get("training_dataset_promotion_allowed") is False,
        "row_fields": row_fields.get("row_id") is True and row_fields.get("raw_line_sha256") is True and row_fields.get("training_dataset_promotion_allowed") is False,
        "acceptance_enabled": all(acceptance_cfg.values()) and len(acceptance_cfg) == 7,
        "rust_bundle_type": "BronzeCandidatePreviewBundle" in rust,
        "rust_row_type": "BronzeCandidatePreviewRow" in rust,
        "rust_builder": "build_bronze_candidate_preview_bundle" in rust,
        "rust_requires_verification": "verify_historical_source_files" in rust and "if verification.ok" in rust,
        "rust_quarantine_flags": "quarantine_only: true" in rust and "training_dataset_promotion_allowed: false" in rust,
        "rust_hash_rows": "raw_line_sha256" in rust and "sha256_text" in rust,
        "rust_tests": "builds_quarantined_preview_rows_from_verified_source" in rust and "blocked_when_source_verification_fails" in rust,
        "lib_exports": "pub mod bronze_candidate_v249;" in lib and "pub use bronze_candidate_v249::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.bronze_candidate_preview_smoke.v249",
        "milestone": "v249_bronze_candidate_preview",
        "acceptance": checks,
        "summary": {
            "offline_only": True,
            "network_calls_allowed": False,
            "quarantine_only": True,
            "training_dataset_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v249_bronze_candidate_preview.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
