#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v511_v520_prediction_result_cards.json")
    args = ap.parse_args()
    root = Path(args.root)
    contract = json.loads((root / "configs/prediction_result_cards.v511_v520.json").read_text(encoding="utf-8"))
    renderer = (root / "tauri-app/src/simple_matches.js").read_text(encoding="utf-8")
    docs = (root / "docs/prediction_result_cards_v511_v520.md").read_text(encoding="utf-8")
    workflow = (root / ".github/workflows/v511_v520_prediction_result_cards.yml").read_text(encoding="utf-8")
    required = contract.get("desktop", {}).get("required_functions", [])
    checks = {
        "contract": contract.get("schema") == "omnibet.prediction_result_cards_contract.v511_v520",
        "functions": all(name in renderer for name in required),
        "selected_card": "Prediction result" in renderer and "renderPredictionCard(snapshot)" in renderer,
        "batch_cards": "runPredictAll" in renderer and "snapshots.map(renderPredictionCard)" in renderer,
        "raw_snapshot_hidden": "<details>" in renderer and "Raw snapshot" in renderer,
        "auto_scroll": "scrollIntoView" in renderer,
        "paper_only": "Paper-only preview" in renderer,
        "docs": "v511-v520 Prediction Result Cards" in docs,
        "workflow": "prediction_result_cards_smoke.py" in workflow,
    }
    report = {"ok": all(checks.values()), "schema": "omnibet.prediction_result_cards_smoke.v511_v520", "acceptance": checks}
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
