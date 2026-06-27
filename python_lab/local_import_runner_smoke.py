#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_jsonl(path: Path) -> List[Dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha256_hex(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def readme_mentions_local_import_runner(readme: str) -> bool:
    lowered = readme.lower()
    return "v361-v370" in lowered and "local import" in lowered and "generated" in lowered


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/local_import_runner.v361_v370.json")
    manifest = read_json(root / "data/local_sources/v361_v370/source_manifest.json")
    fixtures = read_jsonl(root / "data/local_sources/v361_v370/fixtures.jsonl")
    odds_rows = read_jsonl(root / "data/local_sources/v361_v370/odds.jsonl")
    settlements = read_jsonl(root / "data/local_sources/v361_v370/settlements.jsonl")
    desktop = read_json(root / "tauri-app/src/generated-green-sample.sample.json")
    docs = (root / "docs/local_import_runner_v361_v370.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/local_import_runner_v361.rs").read_text(encoding="utf-8")
    rust_lib = (root / "rust-core/src/lib.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v361_v370_local_import_runner.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/generated_green.js").read_text(encoding="utf-8")

    acceptance = contract.get("acceptance", {})
    panel_ids = contract.get("desktop_status_panel", {}).get("panel_ids", [])
    button_ids = contract.get("desktop_status_panel", {}).get("button_ids", [])
    ids = html_ids(html)
    manifest_sources = manifest.get("sources", [])
    source_hashes_match = all(sha256_hex(root / source["local_path"]) == source.get("content_sha256") for source in manifest_sources)
    row_counts_match = all(len(read_jsonl(root / source["local_path"])) == source.get("row_count") for source in manifest_sources)
    market_families = {row.get("market_family") for row in odds_rows}

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.local_import_runner_contract.v361_v370" and manifest.get("schema") == "omnibet.local_import_source_manifest.v361_v370" and desktop.get("schema") == "omnibet.generated_green_sample_desktop.v361_v370",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True and manifest.get("paper_only") is True and desktop.get("paper_only") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and manifest.get("credential_values_present") is False and no_secret_values(manifest) and no_secret_values(desktop),
        "input_paths_defined": all(Path(path).as_posix().startswith("data/local_sources/v361_v370/") for path in contract.get("input_files", {}).values()),
        "output_paths_defined": "reports/generated_v361_v370_green_sample.json" in contract.get("generated_outputs", {}).values() and "tauri-app/src/generated-green-sample.sample.json" in contract.get("generated_outputs", {}).values(),
        "manifest_sources_complete": len(manifest_sources) >= 3 and all(required_subset(["source_id", "local_path", "codec", "content_sha256", "row_count", "observed_at_policy", "credential_values_present"], row) for row in manifest_sources),
        "manifest_hashes_match": source_hashes_match,
        "manifest_row_counts_match": row_counts_match,
        "fixtures_complete": len(fixtures) >= contract.get("green_gate_requirements", {}).get("minimum_fixture_rows", 0) and all(required_subset(contract.get("required_fixture_fields", []), row) for row in fixtures),
        "odds_complete": len(odds_rows) >= contract.get("green_gate_requirements", {}).get("minimum_odds_rows", 0) and all(required_subset(contract.get("required_odds_fields", []), row) and row.get("price_decimal", 0) > 1 and row.get("closing_price_decimal", 0) > 1 for row in odds_rows),
        "settlements_complete": len(settlements) >= contract.get("green_gate_requirements", {}).get("minimum_settlement_rows", 0) and all(required_subset(contract.get("required_settlement_fields", []), row) for row in settlements),
        "settlement_order_safe": all(row.get("label_created_at", "") >= row.get("settled_at", "") for row in settlements),
        "market_family_count": len(market_families) >= contract.get("green_gate_requirements", {}).get("minimum_market_families", 0),
        "desktop_generated_sample_ready": desktop.get("status") == "generated_sample_only" and desktop.get("source_manifest_verified") is True and desktop.get("summary", {}).get("trust_status") == "sample_only",
        "desktop_metrics_non_null": all(row.get("log_loss") is not None and row.get("brier_score") is not None for row in desktop.get("baseline_report", {}).get("metric_summary", [])) and all(row.get("calibration_gap") is not None for row in desktop.get("calibration_report", {}).get("bins", [])) and all(row.get("average_clv_decimal") is not None for row in desktop.get("paper_clv_summary", [])),
        "trust_locks_outputs": desktop.get("trust_gate", {}).get("status") == "sample_only" and desktop.get("trust_gate", {}).get("validated_paper") is False and desktop.get("trust_gate", {}).get("terminal_prediction_allowed") is False and desktop.get("trust_gate", {}).get("bilet_builder_allowed") is False,
        "storage_manifest_shape": desktop.get("storage_manifest", {}).get("preferred_output_codec") == "jsonl.zstd" and desktop.get("storage_manifest", {}).get("fallback_output_codec") == "jsonl.gzip" and len(desktop.get("storage_manifest", {}).get("content_sha256", "")) == 64,
        "rust_module_exposed": "pub mod local_import_runner_v361;" in rust_lib and "pub use local_import_runner_v361::*;" in rust_lib,
        "rust_module_defined": "verify_manifest_hashes" in rust_module and "parse_jsonl_rows" in rust_module and "build_generated_green_report" in rust_module and "load_minipack" in rust_module and "write_generated_green_report" in rust_module,
        "html_page_wired": 'data-page="generated-green"' in html and all(panel_id in html for panel_id in panel_ids) and all(button_id in html for button_id in button_ids) and 'src="generated_green.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "app_binding": "./generated_green.js" in app_js and "loadAndRenderGeneratedGreenStatus" in app_js and "load-generated-green-status" in app_js,
        "renderer_wired": "renderGeneratedGreenStatus" in renderer and "renderWalkForward" in renderer and "renderBaseline" in renderer and "renderCalibration" in renderer and "renderTrust" in renderer,
        "docs_updated": "v361-v370 Local Import Runner" in docs and "source manifest hash verifier" in docs and "sample_only" in docs,
        "readme_updated": readme_mentions_local_import_runner(readme),
        "workflow_updated": "local_import_runner_smoke.py" in workflow and "cargo test" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 13,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.local_import_runner_smoke.v361_v370",
        "milestone": "v361_v370_local_import_runner_storage_backed_green_sample",
        "acceptance": checks,
        "summary": {
            "fixtures": len(fixtures),
            "odds_rows": len(odds_rows),
            "settlement_rows": len(settlements),
            "market_families": len(market_families),
            "manifest_hashes_match": source_hashes_match,
            "trust_status": desktop.get("trust_gate", {}).get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v361_v370_local_import_runner.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
