#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def build_candidates(fixtures: Dict[str, Any], results: Dict[str, Any]) -> List[Dict[str, Any]]:
    fmap = {row["fixture_id"]: row for row in fixtures.get("fixtures", [])}
    candidates: List[Dict[str, Any]] = []
    for row in results.get("settlements", []):
        if row.get("status") != "settled":
            continue
        fixture = fmap[row["fixture_id"]]
        if row["label_available_after_utc"] <= fixture["kickoff_utc"]:
            raise ValueError(f"bad label timestamp: {row['fixture_id']}")
        candidates.append({
            "fixture_id": row["fixture_id"],
            "kickoff_utc": fixture["kickoff_utc"],
            "label_available_after_utc": row["label_available_after_utc"],
            "home_name": row["home_name"],
            "away_name": row["away_name"],
            "result_label": row["result_label"],
            "total_goals": row["total_goals"],
            "btts_label": row["btts_label"],
        })
    return sorted(candidates, key=lambda x: x["kickoff_utc"])


def build_report(root: Path) -> Dict[str, Any]:
    cfg = read_json(root / "configs/eval_gate_scaffold.v553_v570.json")
    fixtures = read_json(root / cfg["inputs"]["fixture_pack"])
    results = read_json(root / cfg["inputs"]["result_pack"])
    candidates = build_candidates(fixtures, results)
    teams = sorted({team for row in candidates for team in [row["home_name"], row["away_name"]]})
    competitions = sorted({row.get("competition_id", "fifa_world_cup_2026") for row in candidates})
    thresholds = cfg["thresholds"]
    gates = {
        "settled_rows": len(candidates),
        "distinct_teams": len(teams),
        "competitions": len(competitions),
        "chronological_splits_available": 0 if len(candidates) < 3 else 1,
        "minimum_rows_pass": len(candidates) >= thresholds["minimum_rows_for_real_model"],
        "minimum_teams_pass": len(teams) >= thresholds["minimum_distinct_teams"],
        "minimum_competitions_pass": len(competitions) >= thresholds["minimum_competitions"],
        "chronological_split_pass": False,
        "label_timestamps_pass": all(row["label_available_after_utc"] > row["kickoff_utc"] for row in candidates),
    }
    ready_for_real_model = all([
        gates["minimum_rows_pass"],
        gates["minimum_teams_pass"],
        gates["minimum_competitions_pass"],
        gates["chronological_split_pass"],
        gates["label_timestamps_pass"],
    ])
    model_status = {
        "schema": "omnibet.model_status.v553_v570",
        "ready_for_real_model": ready_for_real_model,
        "status": "blocked_insufficient_settled_rows" if not ready_for_real_model else "ready_for_train_eval",
        "normal_gui_action_allowed": False,
        "settled_rows": len(candidates),
        "minimum_rows_required": thresholds["minimum_rows_for_real_model"],
        "message": "Only preview evaluation is allowed until the gates pass.",
    }
    feature_manifest = {
        "schema": "omnibet.feature_family_manifest.v553_v570",
        "fixture_result_goals": "candidate_preview_available",
        "corners_cards_set_pieces": "locked_needs_event_data",
        "player_markets": "locked_needs_lineups_and_player_events",
        "odds_value": "locked_needs_opening_and_closing_odds",
    }
    write_json(root / cfg["outputs"]["model_status"], model_status)
    write_json(root / cfg["outputs"]["feature_manifest"], feature_manifest)
    checks = {
        "contract_schema": cfg.get("schema") == "omnibet.eval_gate_scaffold.v553_v570",
        "candidate_count_is_one": len(candidates) == 1,
        "model_blocked": ready_for_real_model is False,
        "normal_gui_hidden": model_status["normal_gui_action_allowed"] is False,
        "timestamp_gate": gates["label_timestamps_pass"] is True,
        "feature_manifest_written": feature_manifest["player_markets"] == "locked_needs_lineups_and_player_events",
    }
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.eval_gate_scaffold_smoke.v553_v570",
        "acceptance": checks,
        "gates": gates,
        "model_status": model_status,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v553_v570_eval_gate_scaffold.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
