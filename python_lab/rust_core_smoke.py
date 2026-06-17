#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path, ui_sample: Path | None) -> Dict[str, Any]:
    rust_file = root / "rust-core/src/local_data_core.rs"
    lib_file = root / "rust-core/src/lib.rs"
    rust = rust_file.read_text(encoding="utf-8")
    lib = lib_file.read_text(encoding="utf-8")
    required_tokens = [
        "LocalResultRow",
        "LocalTrainingRow",
        "LocalPredictionRow",
        "IntegrityReport",
        "MetricReport",
        "CalibrationBand",
        "CoverageReport",
        "dedupe_rows",
        "build_training_rows",
        "brier_score",
        "accuracy_at_half",
        "calibration_bands",
        "coverage_report",
        "metrics_by_competition",
    ]
    checks = {
        "rust_file_exists": rust_file.exists(),
        "lib_exports_module": "pub mod local_data_core" in lib and "pub use local_data_core::*" in lib,
        "required_tokens_present": all(token in rust for token in required_tokens),
        "unit_tests_present": "#[cfg(test)]" in rust and "dedupes_and_builds_training_rows" in rust,
        "serde_derives_present": "Serialize" in rust and "Deserialize" in rust,
        "no_shell_paths": "Command::new" not in rust and "std::process" not in rust,
    }
    report = {
        "ok": all(checks.values()),
        "schema": "omnibet.rust_core_migration.v111_v116",
        "milestone": "v111_v116_rust_core_migration",
        "modules": {
            "local_data_core": "rust-core/src/local_data_core.rs",
            "lib": "rust-core/src/lib.rs",
        },
        "implemented": {
            "v111_row_schemas": ["LocalResultRow", "LocalTrainingRow", "LocalPredictionRow"],
            "v112_integrity_dedupe": ["IntegrityReport", "dedupe_rows"],
            "v113_training_rows": ["build_training_rows"],
            "v114_metrics_calibration": ["brier_score", "accuracy_at_half", "calibration_bands"],
            "v115_coverage_report": ["CoverageReport", "coverage_report", "metrics_by_competition"],
            "v116_desktop_payload": "tauri-app/src/rust-core.sample.json",
        },
        "acceptance": checks,
        "policy": {"python_orchestrates": True, "rust_runtime_core_started": True},
    }
    if ui_sample:
        write_json(ui_sample, {"ok": report["ok"], "version": "omnibet.rust_core.sample.v116", "rust_core_migration": report})
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--ui-sample", default="tauri-app/src/rust-core.sample.json")
    ap.add_argument("--out", default="reports/ci_v111_v116_rust_core.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
