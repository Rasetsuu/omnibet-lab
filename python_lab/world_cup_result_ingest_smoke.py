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


def fixture_map(payload: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {row["fixture_id"]: row for row in payload.get("fixtures", [])}


def candidate_from_settlement(settlement: Dict[str, Any], fixture: Dict[str, Any]) -> Dict[str, Any] | None:
    if settlement.get("status") != "settled":
        return None
    required = ["home_score", "away_score", "label_available_after_utc"]
    if any(key not in settlement for key in required):
        raise ValueError(f"settled row missing required fields: {settlement.get('fixture_id')}")
    if settlement["label_available_after_utc"] <= fixture.get("kickoff_utc", ""):
        raise ValueError(f"label timestamp is not after kickoff: {settlement.get('fixture_id')}")
    return {
        "fixture_id": settlement["fixture_id"],
        "competition_id": fixture.get("competition_id"),
        "round": fixture.get("round"),
        "home_name": settlement.get("home_name") or fixture.get("home_name"),
        "away_name": settlement.get("away_name") or fixture.get("away_name"),
        "kickoff_utc": fixture.get("kickoff_utc"),
        "home_score": settlement["home_score"],
        "away_score": settlement["away_score"],
        "result_label": settlement.get("result_label"),
        "total_goals": settlement.get("total_goals"),
        "btts_label": settlement.get("btts_label"),
        "over_0_5_label": settlement.get("over_0_5_label"),
        "over_1_5_label": settlement.get("over_1_5_label"),
        "over_2_5_label": settlement.get("over_2_5_label"),
        "label_available_after_utc": settlement["label_available_after_utc"],
        "candidate_status": "ready_for_evaluation_preview_not_training",
    }


def build_report(root: Path) -> Dict[str, Any]:
    contract = read_json(root / "configs/world_cup_result_ingest.v543_v552.json")
    fixtures = read_json(root / contract["inputs"]["fixture_pack"])
    results = read_json(root / contract["inputs"]["result_pack"])
    fmap = fixture_map(fixtures)
    candidates: List[Dict[str, Any]] = []
    blocked: List[Dict[str, Any]] = []
    for row in results.get("settlements", []):
        fixture_id = row.get("fixture_id")
        if fixture_id not in fmap:
            raise ValueError(f"result row does not match fixture pack: {fixture_id}")
        candidate = candidate_from_settlement(row, fmap[fixture_id])
        if candidate is None:
            blocked.append({"fixture_id": fixture_id, "status": row.get("status"), "reason": "not_settled"})
        else:
            candidates.append(candidate)
    checks = {
        "contract_schema": contract.get("schema") == "omnibet.world_cup_result_ingest_contract.v543_v552",
        "result_pack_schema": results.get("schema") == "omnibet.world_cup_results_local.v543_v552",
        "has_settled_candidate": len(candidates) == 1,
        "pending_blocked": len(blocked) == 2,
        "brazil_japan_candidate": candidates[0]["fixture_id"] == "wc2026-r32-20260629-brazil-japan",
        "label_timestamp_after_kickoff": all(row["label_available_after_utc"] > row["kickoff_utc"] for row in candidates),
        "future_event_stats_slot": "future_event_stats_slot" in results,
    }
    candidate_payload = {
        "schema": "omnibet.world_cup_training_candidates_preview.v543_v552",
        "ready_for_training": False,
        "ready_for_evaluation_preview": True,
        "candidate_count": len(candidates),
        "blocked_count": len(blocked),
        "candidates": candidates,
        "blocked": blocked,
    }
    write_json(root / contract["outputs"]["candidate_preview"], candidate_payload)
    return {
        "ok": all(checks.values()),
        "schema": "omnibet.world_cup_result_ingest_smoke.v543_v552",
        "acceptance": checks,
        "summary": {
            "candidate_count": len(candidates),
            "blocked_count": len(blocked),
            "ready_for_training": False,
        },
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_v543_v552_world_cup_result_ingest.json")
    args = ap.parse_args()
    report = build_report(Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
