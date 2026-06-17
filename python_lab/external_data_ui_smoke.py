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
    ext = (root / "tauri-app/src/external_data.js").read_text(encoding="utf-8")
    sample = json.loads((root / "tauri-app/src/external-data.sample.json").read_text(encoding="utf-8"))
    checks = {
        "paper_only_preserved": has(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(has(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "sample_ok": sample.get("ok") is True and sample.get("schema") == "omnibet.external_data_contracts.v165_v172",
        "sample_policy": sample.get("policy", {}).get("manual_opt_in") is True and sample.get("policy", {}).get("no_secret_values") is True,
        "sample_has_capabilities": len(sample.get("capabilities", [])) >= 2,
        "sample_has_connectors": len(sample.get("connectors", [])) >= 2,
        "sample_has_fixture_cache": len(sample.get("fixture_cache_sample", {}).get("rows", [])) >= 2,
        "nav_exists": has(index, 'data-page="external-data"'),
        "page_exists": has(index, 'id="external-data"'),
        "panels_exist": all(has(index, marker) for marker in ["external-data-capabilities", "external-data-connectors", "external-data-cache"]),
        "buttons_exist": has(index, 'id="load-external-data"') and has(index, 'id="import-external-fixtures"'),
        "script_included": has(index, 'src="external_data.js"'),
        "app_imports_module": has(app, "./external_data.js") and has(app, "loadAndRenderExternalData") and has(app, "importExternalFixtureCacheToUpcoming"),
        "app_binds_buttons": has(app, "load-external-data") and has(app, "import-external-fixtures"),
        "mapper_exists": has(ext, "mapExternalFixtureCacheToUpcoming") and has(ext, "fixture_id") and has(ext, "competition_id"),
        "renderer_exists": has(ext, "renderExternalData") and has(ext, "external-data-capabilities"),
        "upcoming_import_exists": has(ext, "importExternalFixtureCacheToUpcoming") and has(ext, "renderUpcomingFixtures"),
        "local_policy_present": has(ext, "local_cache_first") and has(ext, "no_secret_values"),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.external_data_ui.v165_v172",
        "milestone": "v165_v172_external_data_contracts",
        "acceptance": checks,
        "files": {
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js",
            "module": "tauri-app/src/external_data.js",
            "sample": "tauri-app/src/external-data.sample.json",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v165_v172_external_data_ui.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
