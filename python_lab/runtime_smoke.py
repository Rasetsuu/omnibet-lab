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
    runtime_file = root / "rust-core/src/local_runtime.rs"
    lib_file = root / "rust-core/src/lib.rs"
    runtime = runtime_file.read_text(encoding="utf-8")
    lib = lib_file.read_text(encoding="utf-8")
    required_tokens = [
        "RuntimeFeatureRow",
        "RuntimeEvalRow",
        "RuntimeReport",
        "RuntimeBridgePayload",
        "parse_result_rows_from_jsonl",
        "training_to_feature_rows",
        "walk_forward_predictions",
        "runtime_eval_to_core",
        "build_runtime_report",
        "build_runtime_bridge_payload",
    ]
    checks = {
        "runtime_file_exists": runtime_file.exists(),
        "lib_exports_runtime": "pub mod local_runtime" in lib and "pub use local_runtime::*" in lib,
        "required_tokens_present": all(token in runtime for token in required_tokens),
        "uses_local_data_core": "crate::local_data_core" in runtime,
        "unit_tests_present": "#[cfg(test)]" in runtime and "builds_runtime_report_and_bridge_payload" in runtime,
        "serde_derives_present": "Serialize" in runtime and "Deserialize" in runtime,
        "no_shell_paths": "Command::new" not in runtime and "std::process" not in runtime,
    }
    report = {
        "ok": all(checks.values()),
        "schema": "omnibet.runtime_consolidation.v117_v124",
        "milestone": "v117_v124_rust_runtime_consolidation",
        "modules": {
            "runtime": "rust-core/src/local_runtime.rs",
            "core": "rust-core/src/local_data_core.rs",
            "lib": "rust-core/src/lib.rs",
        },
        "implemented": {
            "v117_loader": "parse_result_rows_from_jsonl",
            "v118_integrity": "dedupe_rows via local_data_core",
            "v119_training": "build_training_rows via local_data_core",
            "v120_coverage": "coverage_report via local_data_core",
            "v121_features": "training_to_feature_rows",
            "v122_walk_forward": "walk_forward_predictions",
            "v123_calibration": "calibration_bands via local_data_core",
            "v124_bridge": "build_runtime_bridge_payload",
        },
        "acceptance": checks,
        "policy": {"python_orchestrates": True, "rust_runtime_path_expanded": True},
    }
    if ui_sample:
        write_json(ui_sample, {"ok": report["ok"], "version": "omnibet.runtime.sample.v124", "runtime_consolidation": report})
    return report


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--ui-sample", default="tauri-app/src/runtime.sample.json")
    ap.add_argument("--out", default="reports/ci_v117_v124_runtime.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
