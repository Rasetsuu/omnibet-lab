#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def has(text: str, needle: str) -> bool:
    return needle in text


def build_report(root: Path) -> Dict[str, Any]:
    index = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    upcoming = (root / "tauri-app/src/upcoming.js").read_text(encoding="utf-8")
    workflow = (root / "tauri-app/src/beta_workflow.js").read_text(encoding="utf-8")
    sample = json.loads((root / "tauri-app/src/beta-workflow.sample.json").read_text(encoding="utf-8"))
    checks = {
        "paper_only_preserved": has(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(has(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "sample_ok": sample.get("ok") is True and sample.get("schema") == "omnibet.beta_workflow.v173_v180",
        "sample_has_steps": len(sample.get("steps", [])) >= 5,
        "sample_boundaries": sample.get("boundaries", {}).get("paper_only") is True and sample.get("boundaries", {}).get("no_automatic_external_calls") is True,
        "workflow_panel_exists": has(index, 'id="beta-workflow-panel"'),
        "workflow_button_exists": has(index, 'id="load-beta-workflow"'),
        "forecast_export_button_exists": has(index, 'id="export-forecast-snapshot"'),
        "workflow_script_included": has(index, 'src="beta_workflow.js"'),
        "app_imports_workflow": has(app, "./beta_workflow.js") and has(app, "loadAndRenderBetaWorkflow"),
        "app_binds_workflow": has(app, "load-beta-workflow") and has(app, "loadAndRenderBetaWorkflow()"),
        "app_imports_export": has(app, "exportForecastSnapshot") and has(app, "export-forecast-snapshot"),
        "upcoming_export_exists": has(upcoming, "export function exportForecastSnapshot") and has(upcoming, "omnibet-forecast-snapshot.json"),
        "workflow_renderer_exists": has(workflow, "export async function loadAndRenderBetaWorkflow") and has(workflow, "renderBetaWorkflow"),
        "workflow_state_render": has(workflow, "v174 Workflow state"),
        "readiness_render": has(workflow, "v178 Readiness"),
        "boundaries_render": has(workflow, "v179 Boundaries"),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.beta_workflow_smoke.v173_v180",
        "milestone": "v173_v180_beta_workflow_hardening",
        "acceptance": checks,
        "files": {
            "sample": "tauri-app/src/beta-workflow.sample.json",
            "workflow": "tauri-app/src/beta_workflow.js",
            "upcoming": "tauri-app/src/upcoming.js",
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js"
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v173_v180_beta_workflow.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
