#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v491_v500_beta_open_walk_gui.json")
    args = ap.parse_args()
    root = Path(args.root)
    contract = json.loads((root / "configs/beta_open_walk_gui.v491_v500.json").read_text(encoding="utf-8"))
    sample = json.loads((root / "tauri-app/src/beta-home.sample.json").read_text(encoding="utf-8"))
    renderer = (root / "tauri-app/src/beta_home.js").read_text(encoding="utf-8")
    app_js = (root / "tauri-app/src/app.js").read_text(encoding="utf-8")
    docs = (root / "docs/beta_open_walk_gui_v491_v500.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v491_v500_beta_open_walk_gui.yml").read_text(encoding="utf-8")
    panels = contract.get("desktop", {}).get("panel_ids", [])
    checks = {
        "contract": contract.get("schema") == "omnibet.beta_open_walk_gui_contract.v491_v500",
        "sample": sample.get("schema") == "omnibet.beta_home_sample.v491_v500",
        "actions": len(sample.get("primary_actions", [])) == 4,
        "renderer": "ensureBetaHomePage" in renderer and all(panel in renderer for panel in panels),
        "default_page": "showPage('beta-home')" in app_js,
        "docs": "v491-v500 Beta Open-and-Walk GUI" in docs,
        "workflow": "beta_open_walk_gui_smoke.py" in workflow,
    }
    report = {
        "ok": all(checks.values()),
        "schema": "omnibet.beta_open_walk_gui_smoke.v491_v500",
        "acceptance": checks,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
