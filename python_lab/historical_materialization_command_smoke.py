#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def required_subset(required: Iterable[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def explicit_safety_flags_ok(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False)
    if '"credential_values_present": true' in serialized:
        return False
    if '"recommendation_output_present": true' in serialized:
        return False
    if '"ready_for_training": true' in serialized:
        return False
    return True


def build_report(root: Path, generated_report_path: Path, manifest_path: Path, artifact_dir: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_materialization_command.v421_v430.json")
    generated_report = read_json(generated_report_path)
    manifest = read_json(manifest_path)
    command_result = read_json(artifact_dir / "command_result.json")
    bronze_fixtures = read_json(artifact_dir / "bronze_fixtures.generated.json")
    bronze_odds = read_json(artifact_dir / "bronze_odds.generated.json")
    bronze_settlements = read_json(artifact_dir / "bronze_settlements.generated.json")
    silver_fixtures = read_json(artifact_dir / "silver_fixtures.generated.json")
    silver_odds = read_json(artifact_dir / "silver_odds.generated.json")
    gold_candidates = read_json(artifact_dir / "gold_evaluation_candidates.generated.json")
    cargo = (root / "rust-core/Cargo.toml").read_text(encoding="utf-8")
    runner = (root / "rust-core/src/bin/omnibet-historical-materialization-runner.rs").read_text(encoding="utf-8")
    docs = (root / "docs/historical_materialization_command_v421_v430.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v421_v430_historical_materialization_command.yml").read_text(encoding="utf-8")
    acceptance = contract.get("acceptance", {})

    generated_names = contract.get("generated_artifacts", {})
    expected_files = [
        generated_names["bronze_fixtures"],
        generated_names["bronze_odds"],
        generated_names["bronze_settlements"],
        generated_names["silver_fixtures"],
        generated_names["silver_odds"],
        generated_names["gold_candidates"],
        generated_names["command_result"],
    ]

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_materialization_command_contract.v421_v430",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("training_allowed") is False,
        "cli_contract_ok": contract.get("cli", {}).get("binary_name") == "omnibet-historical-materialization-runner" and contract.get("cli", {}).get("shell_passthrough_allowed") is False and contract.get("cli", {}).get("freeform_command_allowed") is False,
        "cargo_binary_registered": 'name = "omnibet-historical-materialization-runner"' in cargo and 'src/bin/omnibet-historical-materialization-runner.rs' in cargo,
        "runner_uses_v411_materializer": "build_historical_materialization_report_v411" in runner and "build_gold_candidate_rows_v411" in runner and "success_payload" in runner,
        "runner_failure_safe": "materialization_command_failed_sample_only" in runner and "ready_for_training\": false" in runner and "recommendation_output_present\": false" in runner,
        "generated_report_schema_ok": generated_report.get("schema") == "omnibet.historical_materialization_command_report.v421_v430",
        "generated_report_required_fields_ok": required_subset(contract.get("report_required_fields", []), generated_report),
        "generated_report_safe": generated_report.get("ready_for_walk_forward") is True and generated_report.get("ready_for_training") is False and generated_report.get("trust_status") == "sample_only" and generated_report.get("recommendation_output_present") is False,
        "manifest_generated": manifest.get("schema") == "omnibet.historical_materialization_manifest.v411_v420" and manifest.get("ready_for_training") is False,
        "command_result_matches_report": command_result.get("schema") == generated_report.get("schema") and command_result.get("run_id") == generated_report.get("run_id"),
        "artifact_files_exist": all((artifact_dir / file_name).exists() for file_name in expected_files),
        "bronze_artifacts_generated": len(bronze_fixtures) == 3 and len(bronze_odds) == 9 and len(bronze_settlements) == 9,
        "silver_artifacts_generated": len(silver_fixtures) == 3 and len(silver_odds) == 9,
        "gold_artifacts_generated": len(gold_candidates) == 9 and all(row.get("feature_leakage_safe") is True for row in gold_candidates),
        "docs_updated": "v421-v430 Historical Materialization Command Bridge" in docs and "omnibet-historical-materialization-runner" in docs and "ready_for_training = false" in docs,
        "workflow_updated": "omnibet-historical-materialization-runner" in workflow and "historical_materialization_command_smoke.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": all(explicit_safety_flags_ok(obj) for obj in [contract, generated_report, manifest, command_result, bronze_fixtures, bronze_odds, bronze_settlements, silver_fixtures, silver_odds, gold_candidates]),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_materialization_command_smoke.v421_v430",
        "milestone": "v421_v430_historical_materialization_command_bridge_and_generated_artifacts",
        "acceptance": checks,
        "summary": {
            "run_id": generated_report.get("run_id"),
            "status": generated_report.get("status"),
            "bronze_fixtures": len(bronze_fixtures),
            "bronze_odds": len(bronze_odds),
            "bronze_settlements": len(bronze_settlements),
            "silver_fixtures": len(silver_fixtures),
            "silver_odds": len(silver_odds),
            "gold_candidates": len(gold_candidates),
            "ready_for_walk_forward": generated_report.get("ready_for_walk_forward"),
            "ready_for_training": generated_report.get("ready_for_training"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--generated-report", default="reports/generated_historical_materialization_v421_v430_report.json")
    ap.add_argument("--manifest", default="reports/materialized/v421_v430/materialization_manifest.json")
    ap.add_argument("--artifact-dir", default="reports/materialized/v421_v430")
    ap.add_argument("--out", default="reports/ci_v421_v430_historical_materialization_command.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.generated_report), Path(args.manifest), Path(args.artifact_dir))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
