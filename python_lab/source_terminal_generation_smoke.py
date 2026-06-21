#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any, Dict

from source_terminal_generate import build_source_terminal_report, write_json


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/source_terminal_generation.v258.json")
    main_rs = (root / "tauri-app/src-tauri/src/main.rs").read_text(encoding="utf-8")
    settings = read_json(root / "tauri-app/src/settings-data.sample.json")
    generator = (root / "python_lab/source_terminal_generate.py").read_text(encoding="utf-8")
    with tempfile.TemporaryDirectory() as tmp:
        generated_path = Path(tmp) / "local_v256_source_terminal_report.json"
        generated = build_source_terminal_report(root)
        write_json(generated_path, generated)
        generated_again = read_json(generated_path)
    workflows = settings.get("local_workflows", [])
    workflow_ids = {row.get("workflow_id") for row in workflows}
    expected = contract.get("expected_counts", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.source_terminal_generation_contract.v258",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_only") is True,
        "network_disabled": contract.get("network_calls_allowed") is False,
        "credentials_not_stored": contract.get("credentials_stored") is False,
        "generator_script_present": "build_source_terminal_report" in generator and "normalize_source_counts" in generator,
        "generated_schema": generated_again.get("schema") == "omnibet.source_terminal_report.v256",
        "generated_counts": generated_again.get("adapter_count") == expected.get("adapter_count") and generated_again.get("adapter_ok_count") == expected.get("adapter_ok_count") and generated_again.get("normalized_total_rows") == expected.get("normalized_total_rows"),
        "generated_row_counts": generated_again.get("normalized_row_counts", {}).get("odds_snapshot_candidate") == expected.get("odds_snapshot_candidate") and generated_again.get("normalized_row_counts", {}).get("fixture_result_candidate") == expected.get("fixture_result_candidate") and generated_again.get("normalized_row_counts", {}).get("event_context_candidate") == expected.get("event_context_candidate"),
        "generated_visible": generated_again.get("source_terminal_visible") is True and not generated_again.get("blocker_summary"),
        "main_workflow": "generate_source_terminal_report" in main_rs and "source_terminal_generate.py" in main_rs and "local_v256_source_terminal_report.json" in main_rs,
        "settings_workflow": "generate_source_terminal_report" in workflow_ids and settings.get("paths", {}).get("source_terminal_report") == ".omnibet-local/reports/local_v256_source_terminal_report.json",
        "settings_safety": settings.get("safety", {}).get("paper_only") is True and settings.get("safety", {}).get("no_network") is True and settings.get("safety", {}).get("allowlisted_workflows_only") is True,
        "acceptance_enabled": all(contract.get("acceptance", {}).values()) and len(contract.get("acceptance", {})) == 8,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.source_terminal_generation_smoke.v258",
        "milestone": "v258_source_report_generation",
        "acceptance": checks,
        "generated_summary": {
            "adapter_count": generated_again.get("adapter_count"),
            "adapter_ok_count": generated_again.get("adapter_ok_count"),
            "normalized_total_rows": generated_again.get("normalized_total_rows"),
            "row_counts": generated_again.get("normalized_row_counts", {}),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v258_source_terminal_generation.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_report(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
