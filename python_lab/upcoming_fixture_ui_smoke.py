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
    sample_path = root / "tauri-app/src/upcoming-fixtures.sample.json"
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    checks = {
        "paper_only_preserved": has(index, "PAPER_ONLY"),
        "legacy_markers_preserved": all(has(index, marker) for marker in ["simple", "detailed", "advanced", "builder", "ping pack_summary predict_fixture value_report model_trust"]),
        "upcoming_nav_exists": has(index, 'data-page="upcoming"'),
        "upcoming_page_exists": has(index, 'id="upcoming"') and has(index, 'id="upcoming-fixtures-panel"'),
        "selected_panel_exists": has(index, 'id="upcoming-selected-fixture"'),
        "snapshot_panel_exists": has(index, 'id="upcoming-forecast-snapshot"'),
        "load_button_exists": has(index, 'id="load-upcoming-fixtures"'),
        "predict_selected_button_exists": has(index, 'id="predict-selected-upcoming-fixture"'),
        "script_included": has(index, 'src="upcoming.js"'),
        "app_imports_upcoming": has(app, "./upcoming.js") and has(app, "loadAndRenderUpcomingFixtures") and has(app, "predictSelectedUpcomingFixture"),
        "app_binds_load": has(app, "load-upcoming-fixtures") and has(app, "loadAndRenderUpcomingFixtures()"),
        "app_binds_predict": has(app, "predict-selected-upcoming-fixture") and has(app, "predictSelectedUpcomingFixture()"),
        "sample_ok": sample.get("ok") is True and sample.get("schema") == "omnibet.upcoming_fixtures.v157",
        "sample_has_fixtures": len(sample.get("fixtures", [])) >= 3,
        "normalizer_exists": has(upcoming, "normalizeUpcomingFixtures"),
        "renderer_exists": has(upcoming, "renderUpcomingFixtures") and has(upcoming, "select-upcoming-fixture"),
        "fills_prediction_inputs": has(upcoming, "setPredictionInputs") and has(upcoming, "home.value") and has(upcoming, "away.value"),
        "predicts_selected": has(upcoming, "predictSelectedUpcomingFixture") and has(upcoming, "predict_fixture"),
        "forecast_snapshot_exists": has(upcoming, "buildForecastSnapshot") and has(upcoming, "omnibet.forecast_snapshot.v162"),
        "policy_present": has(upcoming, "paper_only") and has(upcoming, "no_recommendation"),
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.upcoming_fixture_ui.v157_v164",
        "milestone": "v157_v164_upcoming_fixture_prediction_flow",
        "acceptance": checks,
        "files": {
            "index": "tauri-app/src/index.html",
            "app": "tauri-app/src/app.js",
            "upcoming": "tauri-app/src/upcoming.js",
            "sample": "tauri-app/src/upcoming-fixtures.sample.json",
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v157_v164_upcoming_fixture_ui.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
