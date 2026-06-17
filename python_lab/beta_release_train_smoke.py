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
    module = (root / "tauri-app/src/beta_release_train.js").read_text(encoding="utf-8")
    sample = json.loads((root / "tauri-app/src/beta-release-train.sample.json").read_text(encoding="utf-8"))
    phase_ranges = [phase.get("range") for phase in sample.get("phases", [])]
    checks = {
        "paper_only_preserved": has(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(has(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "sample_ok": sample.get("ok") is True and sample.get("schema") == "omnibet.beta_release_train.v181_v228",
        "six_phases_present": len(sample.get("phases", [])) == 6,
        "all_phase_ranges_present": all(rng in phase_ranges for rng in ["v181-v188", "v189-v196", "v197-v204", "v205-v212", "v213-v220", "v221-v228"]),
        "qa_checklist_present": len(sample.get("qa_checklist", [])) >= 8,
        "persistence_contract_present": sample.get("local_persistence_contract", {}).get("root") == ".omnibet-local",
        "evaluation_contract_present": "metrics" in sample.get("evaluation_contract", {}),
        "release_gate_present": sample.get("release_gate", {}).get("ci_green") is True,
        "boundary_policy_present": sample.get("boundaries", {}).get("paper_only") is True and sample.get("boundaries", {}).get("no_secret_values") is True,
        "panel_exists": has(index, 'id="beta-release-train-panel"'),
        "button_exists": has(index, 'id="load-beta-release-train"'),
        "script_included": has(index, 'src="beta_release_train.js"'),
        "app_imports_module": has(app, "./beta_release_train.js") and has(app, "loadAndRenderBetaReleaseTrain"),
        "app_binds_button": has(app, "load-beta-release-train") and has(app, "loadAndRenderBetaReleaseTrain()"),
        "renderer_exports": has(module, "export async function loadAndRenderBetaReleaseTrain") and has(module, "renderBetaReleaseTrain"),
        "renderer_sections": all(has(module, marker) for marker in ["v181-v188 QA checklist", "v197-v204 Local persistence", "v205-v212 Evaluation path", "v221-v228 Beta release gate"]),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.beta_release_train_smoke.v181_v228",
        "milestone": "v181_v228_beta_release_train",
        "acceptance": checks,
        "files": {
            "sample": "tauri-app/src/beta-release-train.sample.json",
            "module": "tauri-app/src/beta_release_train.js",
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js"
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v181_v228_beta_release_train.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
