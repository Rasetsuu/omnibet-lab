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
    local_import = (root / "tauri-app/src/local_import.js").read_text(encoding="utf-8")
    checks = {
        "paper_only_preserved": has(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(has(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "desktop_beta_page_preserved": has(index, 'id="desktop-beta"') and has(index, 'id="desktop-beta-panel"'),
        "file_input_exists": has(index, 'id="local-import-file"') and has(index, 'accept=".csv,.json,.jsonl"'),
        "preview_button_exists": has(index, 'id="run-local-import-preview"'),
        "export_button_exists": has(index, 'id="export-local-import-bundle"'),
        "preview_panels_exist": all(has(index, marker) for marker in ["local-import-preview", "local-import-integrity", "local-import-bundle"]),
        "script_included": has(index, 'src="local_import.js"'),
        "app_imports_local_import": has(app, "./local_import.js") and has(app, "runLocalImportPreview") and has(app, "exportLocalImportBundle"),
        "app_binds_preview": has(app, "run-local-import-preview") and has(app, "selectedLocalImportFile()"),
        "app_binds_export": has(app, "export-local-import-bundle"),
        "csv_parser_exists": has(local_import, "export function parseCsvRows") and has(local_import, "splitCsvLine"),
        "json_parser_exists": has(local_import, "export function parseJsonRows"),
        "normalizer_exists": has(local_import, "export function normalizeImportRows"),
        "integrity_exists": has(local_import, "export function integrityReport"),
        "bundle_exists": has(local_import, "export function buildLocalImportBundle"),
        "preview_render_exists": has(local_import, "renderLocalImportBundle") and has(local_import, "v143 Row preview"),
        "download_exists": has(local_import, "downloadBundle") and has(local_import, "omnibet-local-import-bundle.json"),
        "offline_policy_present": has(local_import, "local_only") and has(local_import, "no_credentials"),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.local_import_ui.v141_v148",
        "milestone": "v141_v148_local_import_workflow",
        "acceptance": checks,
        "files": {
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js",
            "local_import": "tauri-app/src/local_import.js",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v141_v148_local_import_ui.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
