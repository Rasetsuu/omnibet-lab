#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

REQUIRED_MARKETS = {"1x2", "totals", "btts"}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def parse_utc(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.endswith("Z"):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        return None


def ordered(left: Any, right: Any) -> bool:
    left_dt = parse_utc(left)
    right_dt = parse_utc(right)
    return left_dt is not None and right_dt is not None and left_dt <= right_dt


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = [
        '"api_key":',
        '"secret":',
        '"bearer_token":',
        '"credential_value":',
        "secret_value",
        "bearer ",
        "sk-",
    ]
    return not any(marker in serialized for marker in forbidden)


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/baseline_training_evaluation.v281_v290.json")
    sample = read_json(root / "data/training/v281_v290/baseline_training_evaluation.sample.json")
    docs = (root / "docs/baseline_training_evaluation_v281_v290.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/baseline_eval_v281.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v281_v290_baseline_training_evaluation.yml").read_text(encoding="utf-8")

    dataset = contract.get("dataset_requirements", {})
    baselines = contract.get("baseline_models", [])
    metrics = contract.get("evaluation_metrics", {})
    walk_forward = contract.get("walk_forward_evaluation", {})
    clv = contract.get("paper_clv_report", {})
    trust_gate = contract.get("model_trust_gate", {})
    terminal = contract.get("market_terminal_prediction_table", {})
    acceptance = contract.get("acceptance", {})

    sample_models = sample.get("baseline_models", [])
    sample_wf = sample.get("walk_forward_report", {})
    sample_windows = sample_wf.get("windows", [])
    sample_clv = sample.get("paper_clv_report", {})
    sample_trust = sample.get("model_trust_gate_rows", [])
    sample_terminal = sample.get("market_terminal_prediction_table_sample", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.baseline_training_evaluation_contract.v281_v290",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "no_live_calls_credentials_recommendations": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and sample.get("credential_values_present") is False and sample.get("real_money_recommendations_present") is False and no_secret_values(sample),
        "no_random_or_unsettled_training": contract.get("random_split_allowed") is False and contract.get("training_on_unsettled_games_allowed") is False,
        "dataset_contracts_linked": dataset.get("storage_contract") == "omnibet.storage_v2_compression_contract.v266_v270" and dataset.get("historical_contract") == "omnibet.historical_dataset_foundation_contract.v271_v280",
        "dataset_time_columns": {"prediction_time", "feature_observed_at", "label_created_at", "settled_at"}.issubset(set(dataset.get("required_time_columns", []))),
        "dataset_thresholds": dataset.get("minimum_ready_rows_before_training", 0) >= 1000 and dataset.get("minimum_settlement_coverage_ratio", 0.0) >= 0.95,
        "baseline_markets_defined": REQUIRED_MARKETS.issubset({row.get("market_family") for row in baselines}),
        "baseline_no_vig_defined": any(row.get("model_family") == "market_baseline" and "no_vig" in row.get("baseline_id", "") for row in baselines),
        "sample_baselines_not_trusted": all(row.get("trust_status") == "sample_only" for row in sample_models),
        "metrics_required": {"log_loss", "brier_score", "calibration_ece", "paper_clv_avg", "trust_gate_status"}.issubset(set(metrics.get("required_report_fields", []))),
        "walk_forward_rust_no_random": walk_forward.get("target_runtime") == "rust" and walk_forward.get("random_split_allowed") is False,
        "walk_forward_safety_checks": {"feature_observed_at_lte_prediction_time", "label_created_after_settlement", "no_random_shuffle_split", "settlement_coverage_threshold_met"}.issubset(set(walk_forward.get("required_safety_checks", []))),
        "sample_walk_forward_ordered": all(ordered(row.get("train_start"), row.get("train_end")) and ordered(row.get("train_end"), row.get("validation_start")) and ordered(row.get("validation_end"), row.get("test_start")) and row.get("random_split_allowed") is False for row in sample_windows),
        "paper_clv_requires_closing_odds": clv.get("requires_closing_odds") is True and clv.get("real_stake_allowed") is False and sample_clv.get("requires_closing_odds") is True and sample_clv.get("real_stake_allowed") is False,
        "trust_gate_blocks_unvalidated": trust_gate.get("default_status") == "sample_only" and trust_gate.get("minimum_status_for_bilet_builder") == "validated_paper" and all(row.get("trust_status") == "sample_only" for row in sample_trust),
        "terminal_table_paper_only": set(["inspect", "paper_watch_only"]).issuperset(set(terminal.get("allowed_actions", []))) and {"recommend_real_bet", "place_bet", "auto_stake", "claim_profitability"}.issubset(set(terminal.get("forbidden_actions", []))) and all(row.get("allowed_action") in {"inspect", "paper_watch_only"} for row in sample_terminal),
        "sample_not_ready": sample.get("dataset_status", {}).get("ready_for_real_training") is False and sample.get("summary", {}).get("ready_for_market_terminal_predictions") is False,
        "rust_module_exposed": "pub mod baseline_eval_v281;" in rust_lib and "pub use baseline_eval_v281::*;" in rust_lib,
        "rust_module_validation": "validate_baseline_training_evaluation_contract" in rust_module and "no_vig" in rust_module and "random_split_allowed" in rust_module and "recommend_real_bet" in rust_module,
        "docs_updated": "v281-v290 Baseline Training and Evaluation" in docs and "No-vig" in docs and "Paper CLV" in docs,
        "readme_updated": "v281-v290 baseline training and evaluation" in readme,
        "workflow_updated": "baseline_training_evaluation_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 9,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.baseline_training_evaluation_smoke.v281_v290",
        "milestone": "v281_v290_baseline_training_evaluation",
        "acceptance": checks,
        "summary": {
            "baseline_contracts": len(baselines),
            "sample_models": len(sample_models),
            "evaluation_rows": len(sample.get("evaluation_rows", [])),
            "trust_gate_rows": len(sample_trust),
            "ready_for_training": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v281_v290_baseline_training_evaluation.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
