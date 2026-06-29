#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v521_v530_paper_market_builder_preview.json")
    args = ap.parse_args()
    root = Path(args.root)
    contract = json.loads((root / "configs/paper_market_builder_preview.v521_v530.json").read_text(encoding="utf-8"))
    renderer = (root / "tauri-app/src/simple_matches.js").read_text(encoding="utf-8")
    roadmap = (root / "docs/roadmap_after_market_builder_v521_v530.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v521_v530_paper_market_builder_preview.yml").read_text(encoding="utf-8")
    labels = contract.get("desktop", {}).get("required_labels", [])
    checks = {
        "contract": contract.get("schema") == "omnibet.paper_market_builder_preview_contract.v521_v530",
        "labels": all(label in renderer for label in labels),
        "lean": "Paper lean:" in renderer,
        "builder": "Paper Market Builder" in renderer,
        "debug_output_hidden": "output-panel" in renderer and "display = 'none'" in renderer,
        "raw_snapshot_hidden": "<details>" in renderer and "Raw snapshot" in renderer,
        "roadmap": "Rust migration direction" in roadmap and "Immediate next phases" in roadmap,
        "workflow": "paper_market_builder_preview_smoke.py" in workflow,
    }
    report = {"ok": all(checks.values()), "schema": "omnibet.paper_market_builder_preview_smoke.v521_v530", "acceptance": checks}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
