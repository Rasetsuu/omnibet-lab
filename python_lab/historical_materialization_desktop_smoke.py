#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def html_ids(text: str) -> list[str]:
    return re.findall(r'id="([^"]+)"', text)


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
    contract = read_json(root / "configs/historical_materialization_desktop.v431_v440.json")
    sample = read_json(root / "tauri-app/src/historical-materialization.sample.json")
    renderer = (root / "tauri-app/src/historical_materialization.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    html = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    docs = (root / "docs/historical_materialization_desktop_v431_v440.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v431_v440_historical_materialization_desktop.yml").read_text(encoding="utf-8")
    ids = html_ids(html)
    acceptance = contract.get("acceptance", {})
    desktop = contract.get("desktop", {})
    panel_ids = desktop.get("panel_ids", [])

    checks = {
        "contract_schema_ok": contract.get("schema") == "omnibet.historical_materialization_desktop_contract.v431_v440",
        "contract_safety_flags": contract.get("paper_only") is True and contract.get("local_first") is True and contract.get("live_provider_calls_allowed") is False and contract.get("credential_values_allowed") is False and contract.get("real_money_recommendations_allowed") is False and contract.get("training_allowed") is False,
        "desktop_contract_ok": desktop.get("page_id") == "historical-materialization" and desktop.get("renderer") == "tauri-app/src/historical_materialization.js" and desktop.get("fallback_sample_path") == "tauri-app/src/historical-materialization.sample.json",
        "sample_schema_ok": sample.get("schema") == "omnibet.historical_materialization_command_report.v421_v430",
        "sample_required_fields_ok": required_subset(contract.get("report_required_fields", []), sample),
        "sample_safe": sample.get("ready_for_walk_forward") is True and sample.get("ready_for_training") is False and sample.get("trust_status") == "sample_only" and sample.get("recommendation_output_present") is False,
        "renderer_loads_generated_with_fallback": "reports/generated_historical_materialization_v421_v430_report.json" in renderer and "historical-materialization.sample.json" in renderer and "loadJsonWithFallback" in renderer,
        "renderer_panels_present": all(panel_id in renderer for panel_id in panel_ids),
        "renderer_exports_loader": "loadAndRenderHistoricalMaterializationStatus" in renderer and "renderHistoricalMaterializationStatus" in renderer,
        "app_imports_and_binds_loader": "./historical_materialization.js" in app_js and "loadAndRenderHistoricalMaterializationStatus" in app_js and "load-historical-materialization-status" in app_js and "load-historical-materialization-status-page" in app_js,
        "html_page_and_nav_wired": 'data-page="historical-materialization"' in html and 'id="historical-materialization"' in html and 'src="historical_materialization.js"' in html,
        "html_buttons_wired": 'id="load-historical-materialization-status"' in html and 'id="load-historical-materialization-status-page"' in html,
        "html_panels_wired": all(f'id="{panel_id}"' in html for panel_id in panel_ids),
        "html_ids_unique": len(ids) == len(set(ids)),
        "docs_updated": "v431-v440 Historical Materialization Desktop Reload" in docs and "ready_for_training = false" in docs and "Historical Materialization" in docs,
        "workflow_updated": "historical_materialization_desktop_smoke.py" in workflow and "compile_python_sources.py" in workflow and "upload-artifact" in workflow,
        "explicit_safety_flags_ok": explicit_safety_flags_ok(contract) and explicit_safety_flags_ok(sample),
        "acceptance_enabled": all(acceptance.values()) and len(acceptance) == 11,
    }

    return {
        "ok": all(checks.values()),
        "schema": "omnibet.historical_materialization_desktop_smoke.v431_v440",
        "milestone": "v431_v440_historical_materialization_desktop_reload_panel",
        "acceptance": checks,
        "summary": {
            "page_id": desktop.get("page_id"),
            "panel_count": len(panel_ids),
            "sample_status": sample.get("status"),
            "ready_for_walk_forward": sample.get("ready_for_walk_forward"),
            "ready_for_training": sample.get("ready_for_training"),
            "trust_status": sample.get("trust_status"),
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v431_v440_historical_materialization_desktop.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
