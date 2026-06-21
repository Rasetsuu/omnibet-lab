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
    contract = read_json(root / "configs/historical_import_contract.v245.json")
    rust = (root / "rust-core/src/historical_import_v245.rs").read_text(encoding="utf-8")
    lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    windows = contract.get("import_windows", [])
    sources = contract.get("source_requirements", [])
    required_sources = [src for src in sources if src.get("required")]
    guards = contract.get("leakage_guards", {})
    settlement = contract.get("settlement_policy", {})
    checks = {
        "schema_ok": contract.get("schema") == "omnibet.historical_import_contract.v245",
        "paper_only": contract.get("paper_only") is True,
        "ci_network_forbidden": contract.get("network_calls_allowed_in_ci") is False,
        "target_layer_ok": contract.get("target_layer") == "historical_raw_to_bronze_candidate",
        "two_windows": len(windows) == 2,
        "window_counts_nonzero": all(w.get("min_fixture_count", 0) > 0 and w.get("min_odds_snapshots", 0) > 0 for w in windows),
        "required_sources_three": len(required_sources) == 3,
        "required_sources_timestamped": all(src.get("point_in_time_timestamp_required") is True for src in required_sources),
        "required_sources_identity_mapped": all(src.get("provider_identity_mapping_required") is True for src in required_sources),
        "odds_market_mapping_required": any(src.get("source_kind") == "odds" and src.get("market_mapping_required") is True for src in required_sources),
        "credentials_forbidden": all(src.get("credentials_must_not_be_persisted") is True for src in required_sources),
        "all_leakage_guards_enabled": all(guards.values()) and len(guards) == 9,
        "settlement_lag_ok": settlement.get("settlement_lag_hours", 0) >= 24,
        "settlement_guards_enabled": settlement.get("result_source_required") is True and settlement.get("void_postponed_abandoned_matches") is True and settlement.get("market_specific_rules_required") is True and settlement.get("label_generation_after_settlement_only") is True,
        "rust_types": "HistoricalImportContract" in rust and "HistoricalImportValidationReport" in rust,
        "rust_validation": "validate_historical_import_contract" in rust and "all leakage guards must be enabled" in rust,
        "rust_rejects_future_leakage": "future_lineup_info_forbidden" in rust and "settlement lag" in rust,
        "lib_exports": "pub mod historical_import_v245;" in lib and "pub use historical_import_v245::*;" in lib,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_import_contract_smoke.v245",
        "milestone": "v245_historical_import_contracts",
        "acceptance": checks,
        "summary": {
            "import_windows": len(windows),
            "required_sources": len(required_sources),
            "paper_only": True,
            "ci_network_calls_allowed": False,
            "settlement_lag_hours": settlement.get("settlement_lag_hours"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v245_historical_import_contract.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
