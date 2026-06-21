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
    contract = read_json(root / "configs/silver_promotion_preview.v240.json")
    rust = (root / "rust-core/src/silver_promote_v240.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    expected = contract.get("expected_offline_preview", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.silver_promotion_preview_contract.v240",
        "preview_only": contract.get("promotion_policy", {}).get("preview_only") is True,
        "market_must_resolve": contract.get("promotion_policy", {}).get("market_mapping_must_be_fully_resolved") is True,
        "identity_must_resolve": contract.get("promotion_policy", {}).get("identity_mapping_must_be_fully_resolved") is True,
        "blocked_prevents_ready": contract.get("promotion_policy", {}).get("blocked_rows_prevent_silver_ready") is True,
        "training_forbidden": contract.get("promotion_policy", {}).get("training_dataset_promotion_allowed") is False,
        "expected_market_review": expected.get("market_review_count") == 1,
        "expected_identity_review": expected.get("identity_review_count") == 0,
        "expected_not_ready": expected.get("silver_ready") is False,
        "expected_blocked_market": expected.get("known_blocked_market_key") == "special_combo_unknown",
        "rust_preview_type": "SilverPromotionPreview" in rust and "SilverFactBundlePreview" in rust and "SilverBlockedBundle" in rust,
        "rust_combines_previews": "SilverMarketMappingPreview" in rust and "IdentityMappingPreview" in rust,
        "rust_build_from_samples": "build_silver_promotion_preview_from_offline_samples" in rust,
        "rust_blocks_unknown_market": "unresolved_market_mappings" in rust and "special_combo_unknown" in rust,
        "rust_preview_only": "preview_only: true" in rust,
        "lib_exports_module": "pub mod silver_promote_v240;" in lib and "pub use silver_promote_v240::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.silver_promotion_preview_smoke.v240",
        "milestone": "v240_silver_promotion_preview",
        "acceptance": checks,
        "expected_offline_preview": expected,
        "safety": {
            "preview_only": True,
            "training_dataset_promotion_allowed": False,
            "unknown_market_blocks_silver_ready": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v240_silver_promotion_preview.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
