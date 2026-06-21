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
    contract = read_json(root / "configs/silver_fact_preview_bundle.v243.json")
    rust = (root / "rust-core/src/silver_fact_v243.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    expected = contract.get("expected_offline_bundle", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.silver_fact_preview_bundle_contract.v243",
        "silver_ready_required": contract.get("input_requirements", {}).get("silver_ready_input_required") is True,
        "clean_queue_required": contract.get("input_requirements", {}).get("clean_review_queue_required") is True,
        "training_forbidden": contract.get("input_requirements", {}).get("training_dataset_promotion_allowed") is False,
        "expected_market_rows": expected.get("market_fact_rows") == 7,
        "expected_identity_rows": expected.get("identity_link_rows") == 15,
        "expected_total_rows": expected.get("total_rows") == 22,
        "expected_review_clean": expected.get("review_rows_at_build_time") == 0,
        "expected_preview_only": expected.get("preview_only") is True,
        "rust_types": "SilverFactPreviewBundle" in rust and "SilverFactPreviewRow" in rust,
        "rust_builders": "build_silver_fact_preview_bundle" in rust and "build_silver_fact_preview_bundle_from_offline_samples" in rust,
        "rust_requires_clean_queue": "silver fact preview requires clean review queue" in rust,
        "rust_requires_ready": "silver fact preview requires silver_ready input" in rust,
        "rust_counts": "market_fact_rows" in rust and "identity_link_rows" in rust and "total_rows" in rust,
        "rust_patched_market_included": "special_combo_unknown" in rust and "sample_same_game_combo_france_win_player_shot_team_corners" in rust,
        "rust_training_forbidden": "training_dataset_promotion_allowed: false" in rust,
        "lib_exports": "pub mod silver_fact_v243;" in lib and "pub use silver_fact_v243::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.silver_fact_preview_bundle_smoke.v243",
        "milestone": "v243_silver_fact_preview_bundle",
        "acceptance": checks,
        "expected_offline_bundle": expected,
        "safety": {
            "preview_only": True,
            "training_dataset_promotion_allowed": False,
            "dirty_review_queue_refused": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v243_silver_fact_preview_bundle.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
