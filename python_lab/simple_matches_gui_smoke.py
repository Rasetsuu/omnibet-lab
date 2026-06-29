#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v501_v510_simple_matches_gui.json")
    args = ap.parse_args()
    root = Path(args.root)
    contract = json.loads((root / "configs/simple_matches_gui.v501_v510.json").read_text(encoding="utf-8"))
    fixtures = json.loads((root / "tauri-app/src/world-cup-fixtures.local.json").read_text(encoding="utf-8"))
    renderer = (root / "tauri-app/src/simple_matches.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    docs = (root / "docs/simple_matches_gui_v501_v510.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v501_v510_simple_matches_gui.yml").read_text(encoding="utf-8")
    checks = {
        "contract": contract.get("schema") == "omnibet.simple_matches_gui_contract.v501_v510",
        "fixtures": fixtures.get("schema") == "omnibet.world_cup_local_fixture_pack.v501_v510" and len(fixtures.get("fixtures", [])) >= 3,
        "renderer": "compactNormalMode" in renderer and "loadAndRenderSimpleMatches" in renderer and "matches-predict-selected" in renderer,
        "default_page": "showPage('matches')" in app_js and "./simple_matches.js" in app_js,
        "docs": "v501-v510 Simple Matches GUI" in docs,
        "workflow": "simple_matches_gui_smoke.py" in workflow,
    }
    report = {"ok": all(checks.values()), "schema": "omnibet.simple_matches_gui_smoke.v501_v510", "acceptance": checks}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
