#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def no_secret_values(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False).lower()
    forbidden = ['"api_key":', '"secret":', '"bearer_token":', '"credential_value":', "secret_value", "bearer ", "sk-"]
    return not any(marker in serialized for marker in forbidden)


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


def required_subset(required: list[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def readme_mentions_generated_writer(readme: str) -> bool:
    lowered = readme.lower()
    return "v371-v380" in lowered and "generated report writer" in lowered and "desktop reload" in lowered


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/generated_report_writer.v371_v380.json")
    docs = (root / "docs/generated_report_writer_v371_v380.md").read_text(encoding="utf-8")
    readme = (root / "README.md").read_text(encoding="utf-8")
    cargo = (root / "rust-core/Cargo.toml").read_text(encoding="utf-8")
    cli = (root / "rust-core/src/bin/omnibet-local-import-runner.rs").read_text(encoding="utf-8")
    rust_module = (root / "rust-core/src/local_import_runner_v361.rs").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v371_v380_generated_report_writer.yml").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    renderer = (root / "tauri-app/src/generated_green.js").read_text(encoding="utf-8")

    report_path = root / "reports/generated_v371_v380_green_sample.json"
    desktop_path = root / "tauri-app/src/generated-green-sample.generated.json"
    storage_path = root / "reports/generated_v371_v380_storage_manifest.json"
    generated_report = read_json(report_path) if report_path.exists() else {}
    generated_desktop = read_json(desktop_path) if desktop_path.exists() else {}
    storage_manifest = read_json(storage_path) if storage_path.exists() else {}
    ids = html_ids(html)
    acceptance = contract.get("acceptance", {})
    storage_fields = contract.get("storage_manifest_required_fields", [])

    checks = {
        "schema_ok": contract.get("schema") == "omnibet.generated_report_writer_contract.v371_v380",
        "paper_local_only": contract.get("paper_only") is True and contract.get("local_first") is True,
        "safe_flags": contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("validated_paper_allowed") is False and contract.get("sample_only_allowed") is True,
        "cli_contract_defined": contract.get("cli_contract", {}).get("binary_name") == "omnibet-local-import-runner" and "--report-out" in contract.get("cli_contract", {}).get("accepted_args", []),
        "cargo_binary_defined": 'name = "omnibet-local-import-runner"' in cargo and 'src/bin/omnibet-local-import-runner.rs' in cargo,
        "cli_writes_generated_report": "write_generated_green_report" in cli and "generated-green-sample.generated.json" in cli and "generated_v371_v380_storage_manifest.json" in cli,
        "cli_failure_path_safe": "integrity_failed_sample_only" in cli and "validated_paper\": false" in cli and "recommendation_output_present\": false" in cli,
        "cli_uses_runner_module": "load_minipack" in cli and "sha256_hex" in cli and "storage_manifest_payload" in cli,
        "runner_module_still_present": "verify_manifest_hashes" in rust_module and "build_generated_green_report" in rust_module and "write_generated_green_report" in rust_module,
        "renderer_prefers_generated": "generated-green-sample.generated.json" in renderer and "generated-green-sample.sample.json" in renderer and "loadJsonWithFallback" in renderer,
        "desktop_reload_wired": "load-generated-green-status" in app_js and 'data-page="generated-green"' in html and 'src="generated_green.js"' in html,
        "html_ids_unique": len(ids) == len(set(ids)),
        "generated_report_exists": generated_report.get("schema") == "omnibet.generated_green_report.v361_v370" and generated_report.get("status") == "generated_sample_only",
        "generated_desktop_exists": generated_desktop.get("schema") == "omnibet.generated_green_sample_desktop.v371_v380" and generated_desktop.get("summary", {}).get("trust_status") == "sample_only",
        "generated_storage_manifest_exists": storage_manifest.get("schema") == "omnibet.generated_storage_manifest.v371_v380" and required_subset(storage_fields, storage_manifest),
        "generated_outputs_safe": generated_report.get("recommendation_output_present") is False and generated_desktop.get("recommendation_output_present") is False and storage_manifest.get("recommendation_output_present") is False and no_secret_values(generated_report) and no_secret_values(generated_desktop) and no_secret_values(storage_manifest),
        "trust_stays_sample_only": generated_report.get("trust_status") == "sample_only" and generated_desktop.get("trust_gate", {}).get("status") == "sample_only" and generated_desktop.get("trust_gate", {}).get("validated_paper") is False and generated_desktop.get("trust_gate", {}).get("terminal_prediction_allowed") is False and generated_desktop.get("trust_gate", {}).get("bilet_builder_allowed") is False,
        "ci_generates_artifacts": "cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-local-import-runner" in workflow and "generated_v371_v380_green_sample.json" in workflow and "generated_v371_v380_storage_manifest.json" in workflow and "upload-artifact" in workflow,
        "docs_updated": "v371-v380 Generated Report Writer" in docs and "sample_only" in docs and "integrity_failed_sample_only" in docs,
        "readme_updated": readme_mentions_generated_writer(readme),
        "workflow_runs_smoke": "generated_report_writer_smoke.py" in workflow,
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.generated_report_writer_smoke.v371_v380",
        "milestone": "v371_v380_real_generated_report_writer_and_desktop_reload",
        "acceptance": checks,
        "summary": {
            "generated_report_status": generated_report.get("status"),
            "desktop_schema": generated_desktop.get("schema"),
            "storage_schema": storage_manifest.get("schema"),
            "trust_status": generated_desktop.get("trust_gate", {}).get("status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v371_v380_generated_report_writer.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
