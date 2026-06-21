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
    contract = read_json(root / "configs/bronze_preview_classification.v250.json")
    rust = (root / "rust-core/src/bronze_classify_v250.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    classes = contract.get("source_kind_classes", {})
    acceptance = contract.get("acceptance", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.bronze_preview_classification_contract.v250",
        "quarantine_only": contract.get("quarantine_only") is True,
        "import_disabled": contract.get("import_allowed_now") is False,
        "promotion_disabled": contract.get("promotion_allowed") is False,
        "evaluation_disabled": contract.get("evaluation_allowed") is False,
        "training_disabled": contract.get("training_dataset_promotion_allowed") is False,
        "classes": classes.get("fixtures_results") == "fixture_result" and classes.get("odds") == "odds_snapshot" and classes.get("lineups_events") == "lineup_event_context",
        "unknown_policy": contract.get("unknown_source_kind_policy") == "review_required",
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 6,
        "rust_bundle_type": "BronzePreviewClassificationBundle" in rust,
        "rust_row_type": "BronzePreviewClassificationRow" in rust,
        "rust_classifier": "classify_bronze_candidate_preview_bundle" in rust and "classify_bronze_candidate_preview_row" in rust,
        "rust_known_classes": "fixture_result" in rust and "odds_snapshot" in rust and "lineup_event_context" in rust,
        "rust_unknown_review": "review_required" in rust and "unknown source kind" in rust,
        "rust_flags_locked": "quarantine_only: true" in rust and "training_dataset_promotion_allowed: false" in rust,
        "rust_tests": "classifies_known_source_kinds_and_reviews_unknowns" in rust and "classified_rows_keep_all_safety_flags_locked" in rust,
        "lib_exports": "pub mod bronze_classify_v250;" in lib and "pub use bronze_classify_v250::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.bronze_preview_classification_smoke.v250",
        "milestone": "v250_bronze_preview_classification",
        "acceptance": checks,
        "summary": {
            "known_classes": classes,
            "unknown_policy": contract.get("unknown_source_kind_policy"),
            "quarantine_only": True,
            "training_dataset_promotion_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v250_bronze_preview_classification.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
