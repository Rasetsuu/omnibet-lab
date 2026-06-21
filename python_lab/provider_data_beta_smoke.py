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
    matrix = read_json(root / "configs/provider_data_beta_matrix.v253.json")
    rust = (root / "rust-core/src/provider_beta_v253.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    providers = matrix.get("providers", [])
    targets = matrix.get("historical_coverage_targets", [])
    desktop = matrix.get("desktop_surface", {})
    acceptance = matrix.get("acceptance", {})
    credential_envs = [provider.get("credential_env_var") for provider in providers if provider.get("credential_env_var")]
    priority_one = [provider for provider in providers if provider.get("beta_priority") == 1]
    checks = {
        "schema_ok": matrix.get("schema") == "omnibet.provider_data_beta_matrix.v253",
        "paper_only": matrix.get("paper_only") is True,
        "ci_offline": matrix.get("network_calls_allowed_in_ci") is False,
        "no_repo_credentials": matrix.get("credentials_stored_in_repo") is False,
        "provider_count": len(providers) >= 5,
        "priority_one_sources": len(priority_one) >= 2,
        "odds_source_present": any(provider.get("supports_odds_snapshots") for provider in providers),
        "results_source_present": any(provider.get("supports_results") for provider in providers),
        "lineups_source_present": any(provider.get("supports_lineups_events") for provider in providers),
        "credential_envs_declared": "THE_ODDS_API_KEY" in credential_envs and "API_FOOTBALL_KEY" in credential_envs,
        "no_ci_live_calls": all(provider.get("ci_live_calls_allowed") is False for provider in providers),
        "historical_targets": len(targets) >= 2 and all(target.get("requires_results") and target.get("requires_odds_snapshots") for target in targets if target.get("use_for_beta_evaluation")),
        "desktop_panels": desktop.get("provider_health_panel") is True and desktop.get("credential_status_panel") is True and desktop.get("historical_coverage_panel") is True and desktop.get("adapter_gap_panel") is True,
        "desktop_safe_actions": desktop.get("live_fetch_button_enabled") is False and desktop.get("manual_manifest_import_enabled") is True and desktop.get("paper_only_banner_required") is True,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 6,
        "rust_types": "ProviderDataBetaMatrix" in rust and "ProviderDataBetaReadinessReport" in rust,
        "rust_validator": "validate_provider_data_beta_matrix" in rust and "parse_provider_data_beta_matrix" in rust,
        "rust_safety": "network_calls_allowed_in_ci" in rust and "credentials_stored_in_repo" in rust and "ci_live_calls_allowed" in rust,
        "rust_tests": "validates_provider_data_beta_matrix" in rust and "rejects_network_credentials_and_weak_coverage" in rust,
        "lib_exports": "pub mod provider_beta_v253;" in lib and "pub use provider_beta_v253::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.provider_data_beta_smoke.v253",
        "milestone": "v253_provider_data_beta_slice",
        "acceptance": checks,
        "summary": {
            "provider_count": len(providers),
            "priority_one_provider_ids": [provider.get("provider_id") for provider in priority_one],
            "credential_env_vars": credential_envs,
            "historical_target_count": len(targets),
            "ci_live_calls_allowed": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v253_provider_data_beta.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
