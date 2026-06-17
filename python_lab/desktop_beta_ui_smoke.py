#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def contains(text: str, needle: str) -> bool:
    return needle in text


def build_report(root: Path) -> Dict[str, Any]:
    index = (root / "tauri-app/src/index.html").read_text(encoding="utf-8")
    app = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    beta = (root / "tauri-app/src/desktop_beta.js").read_text(encoding="utf-8")
    sample_path = root / "tauri-app/src/desktop-beta.sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    checks = {
        "paper_only_preserved": contains(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(contains(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "desktop_beta_nav": contains(index, 'data-page="desktop-beta"'),
        "desktop_beta_page": contains(index, 'id="desktop-beta"') and contains(index, 'id="desktop-beta-panel"'),
        "load_button": contains(index, 'id="load-desktop-beta"'),
        "script_included": contains(index, 'src="desktop_beta.js"'),
        "app_imports_renderer": contains(app, "loadAndRenderDesktopBeta") and contains(app, "./desktop_beta.js"),
        "app_binds_button": contains(app, "load-desktop-beta") and contains(app, "loadAndRenderDesktopBeta()"),
        "renderer_exports": contains(beta, "export async function loadAndRenderDesktopBeta") and contains(beta, "export function renderDesktopBeta"),
        "import_wizard_render": contains(beta, "desktop-beta-import-wizard") and contains(beta, "v134 Import wizard"),
        "coverage_render": contains(beta, "desktop-beta-coverage") and contains(beta, "v135 Coverage"),
        "evaluation_render": contains(beta, "desktop-beta-evaluation") and contains(beta, "v136 Evaluation"),
        "report_render": contains(beta, "desktop-beta-reports") and contains(beta, "v137 Report viewer"),
        "backup_render": contains(beta, "desktop-beta-backup") and contains(beta, "v138 Local bundle"),
        "checklist_render": contains(beta, "desktop-beta-checklist") and contains(beta, "v139 Readiness checklist"),
        "sample_payload_ok": sample.get("ok") is True and "desktop_beta" in sample,
        "sample_has_sections": all(k in sample["desktop_beta"] for k in ["import_wizard", "coverage", "evaluation", "report_viewer", "backup_contract", "release_checklist"]),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.desktop_beta_ui.v133_v140",
        "milestone": "v133_v140_desktop_beta_ui",
        "acceptance": checks,
        "files": {
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js",
            "renderer": "tauri-app/src/desktop_beta.js",
            "sample": "tauri-app/src/desktop-beta.sample.json",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v133_v140_desktop_beta_ui.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
