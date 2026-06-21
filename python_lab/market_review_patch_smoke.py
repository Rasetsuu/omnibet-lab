#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED = {
    "canonical_market_id",
    "family",
    "settlement_rule",
    "selection_scope",
    "correlation_group",
}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    patch = read_json(root / "configs/market_review_patch.v242.json")
    rust = (root / "rust-core/src/market_patch_v242.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    market = patch["canonical_markets_to_add"][0]
    alias = patch["provider_aliases_to_add"][0]
    expected = patch.get("expected_after_patch", {})
    checks = {
        "schema_ok": patch.get("schema") == "omnibet.market_review_patch.v242",
        "sample_only": patch.get("scope") == "offline_sample_only",
        "automatic_forbidden": patch.get("automatic_application_allowed") is False,
        "production_forbidden": patch.get("production_use_allowed") is False,
        "training_forbidden": patch.get("training_dataset_promotion_allowed") is False,
        "market_required_fields": all(market.get(field) not in (None, "") for field in REQUIRED),
        "market_is_sample_combo": market.get("canonical_market_id") == "sample_same_game_combo_france_win_player_shot_team_corners",
        "combo_requires_player_lineup": market.get("player_required") is True and market.get("lineup_required") is True,
        "alias_targets_blocked_key": alias.get("provider_market_key") == "special_combo_unknown",
        "alias_review_false": alias.get("review_required") is False,
        "expected_clears_market_review": expected.get("market_review_count") == 0,
        "expected_clears_total_review": expected.get("total_review_rows") == 0,
        "expected_silver_ready": expected.get("silver_ready") is True,
        "rust_types": "MarketReviewPatchContract" in rust and "MarketReviewRecord" in rust,
        "rust_validation": "validate_market_review_patch" in rust and "automatic, production, and training use must remain forbidden" in rust,
        "rust_application": "apply_market_review_patch" in rust and "build_patched_silver_preview_from_offline_samples" in rust,
        "rust_proves_both_states": "unpatched_preview_still_blocks_sample_market" in rust and "patch_clears_sample_review_queue" in rust,
        "lib_exports": "pub mod market_patch_v242;" in lib and "pub use market_patch_v242::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.market_review_patch_smoke.v242",
        "milestone": "v242_market_review_patch",
        "acceptance": checks,
        "expected_after_patch": expected,
        "safety": {
            "scope": "offline_sample_only",
            "automatic_application_allowed": False,
            "production_use_allowed": False,
            "training_dataset_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v242_market_review_patch.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
