#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def required_subset(required: Iterable[str], row: Dict[str, Any]) -> bool:
    return set(required).issubset(set(row.keys()))


def explicit_safety_flags_ok(obj: Any) -> bool:
    serialized = json.dumps(obj, ensure_ascii=False)
    return (
        '"credential_values_present": true' not in serialized
        and '"recommendation_output_present": true' not in serialized
        and '"ready_for_training": true' not in serialized
    )


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/historical_file_adapter_desktop.v461_v470.json")
    sample = read_json(root / "tauri-app/src/historical-file-adapter.sample.json")
    renderer = (root / "tauri-app/src/historical_file_adapter.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    docs = (root / "docs/historical_file_adapter_desktop_v461_v470.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v461_v470_historical_file_adapter_desktop.yml").read_text(encoding="utf-8")
    desktop = contract.get("desktop", {})
    panel_ids = desktop.get("panel_ids", [])
    adapter_report = sample.get("adapter_report", {})
    normalized_preview = sample.get("normalized_preview", {})
    acceptance = contract.get("acceptance", {})

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_file_adapter_desktop_contract.v461_v470",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("training_allowed") is False,
        "desktop_contract_ok": desktop.get("page_id") == "historical-file-adapter" and desktop.get("renderer") == "tauri-app/src/historical_file_adapter.js" and desktop.get("fallback_sample_path") == "tauri-app/src/historical-file-adapter.sample.json",
        "sample_schema_ok": sample.get("schema") == "omnibet.historical_file_adapter_desktop_sample.v461_v470" and adapter_report.get("schema") == "omnibet.historical_file_adapter_report.v451_v460",
        "sample_required_fields_ok": required_subset(contract.get("report_required_fields", []), adapter_report),
        "sample_rows_ok": adapter_report.get("fixture_rows") == 3 and adapter_report.get("odds_rows") == 9 and adapter_report.get("settlement_rows") == 9 and adapter_report.get("identity_rows") == 6,
        "sample_safe": adapter_report.get("ready_for_materialization") is True and adapter_report.get("ready_for_training") is False and adapter_report.get("trust_status") == "sample_only" and adapter_report.get("recommendation_output_present") is False,
        "normalized_preview_ok": len(normalized_preview.get("fixtures", [])) >= 3 and len(normalized_preview.get("odds", [])) >= 3 and len(normalized_preview.get("settlements", [])) >= 3 and len(normalized_preview.get("identities", [])) >= 2,
        "renderer_self_registers_page": "ensureHistoricalFileAdapterPage" in renderer and "Historical File Adapter" in renderer and "historical-file-adapter" in renderer,
        "renderer_loads_generated_with_fallback": "reports/historical_file_adapter_v451_v460_report.json" in renderer and "reports/historical_file_adapter_v451_v460_normalized_preview.json" in renderer and "historical-file-adapter.sample.json" in renderer,
        "renderer_panels_present": all(panel_id in renderer for panel_id in panel_ids),
        "renderer_exports_loader": "loadAndRenderHistoricalFileAdapterStatus" in renderer and "renderHistoricalFileAdapterStatus" in renderer,
        "app_imports_and_binds_loader": "./historical_file_adapter.js" in app_js and "loadAndRenderHistoricalFileAdapterStatus" in app_js and "load-historical-file-adapter-status" in app_js and "load-historical-file-adapter-status-page" in app_js,
        "docs_updated": "v461-v470 Historical File Adapter Desktop" in docs and "ready_for_training = false" in docs and "Historical File Adapter" in docs,
        "workflow_updated": "historical_file_adapter_desktop_smoke.py" in workflow and "compile_python_sources.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract) and explicit_safety_flags_ok(sample),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_file_adapter_desktop_smoke.v461_v470",
        "milestone": "v461_v470_historical_file_adapter_desktop_panel",
        "acceptance": checks,
        "summary": {
            "page_id": desktop.get("page_id"),
            "panel_count": len(panel_ids),
            "fixture_rows": adapter_report.get("fixture_rows"),
            "odds_rows": adapter_report.get("odds_rows"),
            "ready_for_materialization": adapter_report.get("ready_for_materialization"),
            "ready_for_training": adapter_report.get("ready_for_training"),
            "trust_status": adapter_report.get("trust_status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v461_v470_historical_file_adapter_desktop.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
