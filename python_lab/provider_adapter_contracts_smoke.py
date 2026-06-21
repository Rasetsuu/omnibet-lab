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
    contract = read_json(root / "configs/provider_adapter_contracts.v254.json")
    odds_fixture = read_json(root / "data/provider_fixtures/v254/odds_provider_snapshot.sample.json")
    football_fixture = read_json(root / "data/provider_fixtures/v254/football_fixture_event.sample.json")
    rust = (root / "rust-core/src/provider_adapter_v254.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    adapters = contract.get("adapters", [])
    acceptance = contract.get("acceptance", {})
    desktop = contract.get("desktop_surface", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.provider_adapter_contracts.v254",
        "paper_only": contract.get("paper_only") is True,
        "ci_offline": contract.get("network_calls_allowed_in_ci") is False,
        "no_repo_credentials": contract.get("credentials_stored_in_repo") is False,
        "live_fetch_disabled": contract.get("live_fetch_enabled") is False,
        "adapter_count": len(adapters) == 2,
        "priority_provider_ids": {a.get("provider_id") for a in adapters} == {"the_odds_api", "api_football"},
        "fixture_paths_declared": all(a.get("response_contract", {}).get("fixture_path", "").startswith("data/provider_fixtures/v254/") for a in adapters),
        "ci_fixture_only": all(a.get("ci_fixture_only") is True and a.get("request_contract", {}).get("live_network_allowed_in_ci") is False for a in adapters),
        "normalization_targets": all(len(a.get("normalization_targets", [])) >= 4 for a in adapters),
        "odds_fixture_shape": isinstance(odds_fixture, list) and len(odds_fixture) == 1 and bool(odds_fixture[0].get("bookmakers")),
        "football_fixture_shape": isinstance(football_fixture.get("response"), list) and len(football_fixture["response"]) == 1 and bool(football_fixture["response"][0].get("events")),
        "desktop_visible_readonly": desktop.get("show_adapter_contracts") is True and desktop.get("show_fixture_status") is True and desktop.get("show_missing_fields") is True and desktop.get("show_normalization_targets") is True and desktop.get("live_fetch_button_enabled") is False and desktop.get("credentials_editable_in_repo") is False,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 8,
        "rust_types": "ProviderAdapterContractsV254" in rust and "ProviderAdapterValidationReportV254" in rust and "ProviderAdapterHealthRowV254" in rust,
        "rust_validator": "validate_provider_adapter_contracts_v254" in rust and "validate_adapter_health_row" in rust,
        "rust_fixture_checks": "validate_odds_fixture" in rust and "validate_football_fixture" in rust,
        "rust_safety": "live_network_allowed_in_ci" in rust and "credentials_stored_in_repo" in rust and "live_fetch_enabled" in rust,
        "rust_tests": "validates_offline_priority_adapter_contracts" in rust and "rejects_bad_fixture_and_live_ci_flag" in rust,
        "lib_exports": "pub mod provider_adapter_v254;" in lib and "pub use provider_adapter_v254::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.provider_adapter_contracts_smoke.v254",
        "milestone": "v254_offline_adapter_contracts",
        "acceptance": checks,
        "summary": {
            "adapter_count": len(adapters),
            "fixtures": [a.get("response_contract", {}).get("fixture_path") for a in adapters],
            "ci_live_calls_allowed": False,
            "live_fetch_enabled": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v254_provider_adapter_contracts.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
