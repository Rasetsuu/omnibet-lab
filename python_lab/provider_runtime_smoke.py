#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_PROVIDERS = {"the_odds_api", "api_football", "sportmonks", "betfair_exchange"}
REQUIRED_OUTPUTS = {
    "provider_status",
    "fixture_snapshot",
    "live_state_snapshot",
    "odds_snapshot",
    "market_discovery_snapshot",
    "lineup_snapshot",
    "event_snapshot",
    "player_snapshot",
}
REQUIRED_SNAPSHOT_FIELDS = {"source_id", "request_kind", "captured_at", "observed_at", "payload_sha256", "payload_codec", "payload_path"}


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/provider_runtime.v234.json")
    rust_provider = (root / "rust-core/src/provider.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")

    providers = contract.get("providers", [])
    provider_ids = {row.get("provider_id") for row in providers}
    credential_envs = [row.get("credential_env", "") for row in providers]
    network = contract.get("network_policy", {})
    snapshot = contract.get("snapshot_contract", {})
    acceptance = contract.get("acceptance", {})

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.provider_runtime.v234",
        "required_providers_present": REQUIRED_PROVIDERS.issubset(provider_ids),
        "providers_disabled_by_default": all(row.get("enabled_by_default") is False for row in providers) and network.get("providers_disabled_by_default") is True,
        "manual_enable_required": network.get("manual_enable_required") is True,
        "no_live_calls_in_ci": network.get("ci_live_calls_allowed") is False,
        "no_credential_values": network.get("credential_values_stored") is False and network.get("credential_values_displayed") is False,
        "credential_env_names_only": all(name.endswith("_KEY") or name == "BETFAIR_APP_KEY" for name in credential_envs),
        "source_capabilities_declared": all(all(key in row for key in ["supports_live", "supports_historical", "supports_odds", "supports_fixtures", "supports_lineups", "supports_events", "supports_player_props"]) for row in providers),
        "planned_payloads_declared": all(len(row.get("planned_payloads", [])) > 0 for row in providers),
        "snapshot_fields_complete": REQUIRED_SNAPSHOT_FIELDS.issubset(set(snapshot.get("required_fields", []))),
        "snapshot_hash_required": snapshot.get("payload_hash_required") is True,
        "snapshot_observed_at_required": snapshot.get("observed_at_required") is True,
        "snapshot_prediction_boundary": snapshot.get("prediction_time_boundary_required") is True,
        "canonical_outputs_complete": REQUIRED_OUTPUTS.issubset(set(contract.get("canonical_outputs", []))),
        "adapter_stages_present": all(stage in contract.get("adapter_stages", []) for stage in ["contract_only", "offline_sample_parser", "manual_live_fetcher", "canonical_promotion", "training_dataset_promotion"]),
        "acceptance_safety": acceptance.get("credential_status_only") is True and acceptance.get("no_live_calls_in_ci") is True and acceptance.get("providers_disabled_by_default") is True,
        "rust_module_exposed": "pub mod provider;" in rust_lib and "pub use provider::*;" in rust_lib,
        "rust_contract_structs": "ProviderRuntimeContract" in rust_provider and "ProviderDefinition" in rust_provider and "SourceSnapshotManifest" in rust_provider,
        "rust_status_function": "provider_statuses" in rust_provider and "CredentialStatus" in rust_provider,
        "rust_no_secret_display": "credential_value_displayed: false" in rust_provider and "secret-do-not-display" in rust_provider,
        "rust_snapshot_hashing": "sha256_text" in rust_provider and "payload_sha256" in rust_provider,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.provider_runtime_smoke.v234",
        "milestone": "v234_rust_provider_runtime_foundation",
        "provider_ids": sorted(provider_ids),
        "canonical_outputs": contract.get("canonical_outputs", []),
        "acceptance": checks,
        "safety": {
            "credential_values_displayed": False,
            "credential_values_stored": False,
            "live_calls_in_ci": False,
            "providers_enabled_by_default": False,
            "network_implementation_added": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v234_provider_runtime.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
