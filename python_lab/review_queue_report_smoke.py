#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_MARKET_FIELDS = {
    "canonical_market_id",
    "market_family",
    "settlement_rule",
    "selection_scope",
    "line_required",
    "player_required",
    "lineup_required",
    "correlation_group",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/review_queue_report.v241.json")
    rust = (root / "rust-core/src/review_queue_v241.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    expected = contract.get("expected_offline_report", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.review_queue_report_contract.v241",
        "auto_approval_forbidden": contract.get("review_policy", {}).get("auto_approval_allowed") is False,
        "market_settlement_required": contract.get("review_policy", {}).get("market_review_requires_settlement_rule") is True,
        "market_canonical_required": contract.get("review_policy", {}).get("market_review_requires_canonical_market_id") is True,
        "market_correlation_required": contract.get("review_policy", {}).get("market_review_requires_correlation_group") is True,
        "identity_canonical_required": contract.get("review_policy", {}).get("identity_review_requires_canonical_id") is True,
        "review_blocks_ready": contract.get("review_policy", {}).get("review_rows_block_silver_ready") is True,
        "expected_one_row": expected.get("total_review_rows") == 1,
        "expected_market_row": expected.get("market_review_rows") == 1,
        "expected_identity_zero": expected.get("identity_review_rows") == 0,
        "expected_blocked_key": expected.get("blocked_provider_key") == "special_combo_unknown",
        "rust_types": "ReviewQueueReport" in rust and "ReviewQueueRow" in rust,
        "rust_builder": "build_review_queue_report" in rust and "build_review_queue_report_from_offline_samples" in rust,
        "rust_market_required_fields": all(field in rust for field in REQUIRED_MARKET_FIELDS),
        "rust_identity_path": "identity_mapping" in rust and "unmapped_provider_identity" in rust,
        "rust_no_auto_approval": "auto_approval_allowed: false" in rust and "promotion_allowed_before_review: false" in rust,
        "rust_blocked_key": "special_combo_unknown" in rust,
        "lib_exports": "pub mod review_queue_v241;" in lib and "pub use review_queue_v241::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.review_queue_report_smoke.v241",
        "milestone": "v241_review_queue_report",
        "acceptance": checks,
        "expected_offline_report": expected,
        "safety": {
            "auto_approval_allowed": False,
            "review_rows_block_silver_ready": True,
            "training_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v241_review_queue_report.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
