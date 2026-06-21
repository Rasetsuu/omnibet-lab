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
    contract = read_json(root / "configs/bronze_validation_batch.v252.json")
    surface = read_json(root / "configs/desktop_bronze_validation_surface.v252.json")
    rust = (root / "rust-core/src/bronze_validation_v252.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    checks_cfg = contract.get("checks", {})
    safety = contract.get("safety", {})
    acceptance = contract.get("acceptance", {})
    actions = surface.get("actions_allowed", {})
    panels = surface.get("panels", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.bronze_validation_batch_contract.v252",
        "planned_outputs": len(contract.get("planned_outputs", [])) == 3,
        "batch_scope_all_enabled": all(contract.get("batch_scope", {}).values()),
        "checks_enabled": all(checks_cfg.values()) and len(checks_cfg) == 8,
        "safety_locked": safety.get("quarantine_only") is True and safety.get("import_allowed_now") is False and safety.get("promotion_allowed") is False and safety.get("evaluation_allowed") is False and safety.get("training_dataset_promotion_allowed") is False and safety.get("paper_only") is True,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 6,
        "desktop_schema_ok": surface.get("schema") == "omnibet.desktop_bronze_validation_surface.v252",
        "desktop_panels": all(panels.values()) and len(panels) == 4,
        "desktop_actions_locked": actions.get("inspect_rows") is True and actions.get("export_report") is True and actions.get("import_rows") is False and actions.get("promote_rows") is False and actions.get("run_evaluation") is False and actions.get("train_model") is False and actions.get("place_bets") is False,
        "rust_batch_report": "BronzeValidationBatchReport" in rust,
        "rust_value_validation": "BronzePreviewValueValidationBundle" in rust and "validate_bronze_preview_values" in rust,
        "rust_review_reasons": "BronzePreviewReviewReasonBundle" in rust and "summarize_bronze_preview_review_reasons" in rust,
        "rust_readiness": "BronzeCandidateReadinessSummary" in rust and "summarize_bronze_candidate_readiness" in rust,
        "rust_value_checks": "require_decimal_price" in rust and "require_timestamp_shape" in rust and "require_non_empty" in rust,
        "rust_safety_locked": "ready_for_training: false" in rust and "training_dataset_promotion_allowed: false" in rust,
        "rust_tests": "batch_validates_values_summarizes_reasons_and_blocks_readiness" in rust and "value_rows_keep_all_safety_flags_locked" in rust,
        "lib_exports": "pub mod bronze_validation_v252;" in lib and "pub use bronze_validation_v252::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.bronze_validation_batch_smoke.v252",
        "milestone": "v252_bronze_validation_batch",
        "acceptance": checks,
        "summary": {
            "batched_outputs": contract.get("planned_outputs", []),
            "desktop_read_only": surface.get("safety", {}).get("read_only_surface"),
            "disabled_actions": [key for key, value in actions.items() if value is False],
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v252_bronze_validation_batch.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
