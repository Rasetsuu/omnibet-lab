#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict

REQUIRED_SOURCES = ["the_odds_api", "api_football", "sportmonks", "betfair_exchange"]
REQUIRED_PIPELINE = [
    "provider_status",
    "fixture_discovery",
    "odds_snapshot_capture",
    "live_state_capture",
    "lineup_event_capture",
    "canonical_identity_resolution",
    "paper_prediction_snapshot",
    "post_match_settlement",
    "clv_and_outcome_report",
    "training_dataset_promotion",
]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_report(root: Path) -> Dict[str, Any]:
    capture = read_json(root / "configs/world_cup_live_capture.v231.json")
    release = read_json(root / "configs/release_channels.v231.json")
    source_rows = capture.get("sources", [])
    source_ids = [row.get("source_id") for row in source_rows]
    env_names = [row.get("credential_env", "") for row in source_rows]
    checks = {
        "capture_schema": capture.get("schema") == "omnibet.world_cup_live_capture.v231",
        "release_schema": release.get("schema") == "omnibet.release_channels.v231",
        "competition_is_world_cup": "World Cup 2026" in capture.get("competition", {}).get("name", ""),
        "paper_only": capture.get("competition", {}).get("paper_only") is True and release.get("safety", {}).get("paper_only") is True,
        "required_sources_present": all(src in source_ids for src in REQUIRED_SOURCES),
        "sources_disabled_by_default": all(row.get("enabled_by_default") is False for row in source_rows),
        "no_live_calls_in_ci": all(row.get("ci_live_calls") is False for row in source_rows),
        "credential_env_names_only": all(name.endswith(("_KEY", "_TOKEN")) or name == "BETFAIR_APP_KEY" for name in env_names),
        "no_credential_values": not any("value" in row for row in source_rows),
        "pipeline_complete": all(step in capture.get("pipeline", []) for step in REQUIRED_PIPELINE),
        "prediction_time_required": capture.get("capture_policy", {}).get("prediction_time_required") is True,
        "observed_at_required": capture.get("capture_policy", {}).get("observed_at_required") is True,
        "raw_retention_policy": capture.get("capture_policy", {}).get("delete_or_compress_raw_after_promotion") is True,
        "keep_reproducibility_artifacts": capture.get("capture_policy", {}).get("keep_manifests_hashes_features_labels") is True,
        "no_future_leakage": capture.get("capture_policy", {}).get("no_future_leakage") is True,
        "train_after_final_only": capture.get("training_policy", {}).get("train_only_after_match_final") is True,
        "future_predictions_only": capture.get("training_policy", {}).get("train_only_for_future_predictions") is True,
        "walk_forward_required": capture.get("training_policy", {}).get("walk_forward_required") is True,
        "no_random_split": capture.get("training_policy", {}).get("random_split_allowed") is False,
        "no_vig_baseline_required": capture.get("training_policy", {}).get("bookmaker_no_vig_baseline_required") is True,
        "release_manual_only": release.get("github_releases", {}).get("manual_only") is True,
        "release_draft_prerelease": release.get("github_releases", {}).get("default_draft") is True and release.get("github_releases", {}).get("default_prerelease") is True,
        "release_entrypoints": release.get("github_releases", {}).get("asset_policy", {}).get("windows", {}).get("entrypoint") == "OmniBet-Lab.exe" and release.get("github_releases", {}).get("asset_policy", {}).get("linux", {}).get("entrypoint") == "./omnibet-lab",
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.world_cup_live_capture_smoke.v231",
        "milestone": "v231_release_and_world_cup_capture_foundation",
        "source_ids": source_ids,
        "pipeline": capture.get("pipeline", []),
        "acceptance": checks,
        "safety": {
            "paper_only": True,
            "external_calls_in_ci": False,
            "credential_values_displayed": False,
            "train_only_after_final": True,
            "future_predictions_only": True,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v231_world_cup_live_capture.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
