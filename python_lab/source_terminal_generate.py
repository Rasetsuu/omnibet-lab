#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def timestamp_ok(value: Any) -> bool:
    return isinstance(value, str) and len(value) >= 20 and "T" in value and value.endswith("Z")


def normalize_source_counts(odds_fixture: Any, football_fixture: Dict[str, Any]) -> tuple[Dict[str, int], List[str]]:
    blockers: List[str] = []
    counts = {
        "odds_snapshot_candidate": 0,
        "fixture_result_candidate": 0,
        "event_context_candidate": 0,
    }
    if not isinstance(odds_fixture, list) or not odds_fixture:
        blockers.append("odds_fixture_empty_or_invalid")
    else:
        for fixture in odds_fixture:
            if not timestamp_ok(fixture.get("commence_time")):
                blockers.append("odds_commence_time_invalid")
            for bookmaker in fixture.get("bookmakers", []) or []:
                if not timestamp_ok(bookmaker.get("last_update")):
                    blockers.append("odds_last_update_invalid")
                for market in bookmaker.get("markets", []) or []:
                    for outcome in market.get("outcomes", []) or []:
                        if isinstance(outcome.get("price"), (int, float)) and 1.0 < float(outcome["price"]) < 1000.0:
                            counts["odds_snapshot_candidate"] += 1
                        else:
                            blockers.append("odds_price_invalid")
    response = football_fixture.get("response")
    if not isinstance(response, list) or not response:
        blockers.append("football_response_empty_or_invalid")
    else:
        for item in response:
            fixture = item.get("fixture", {})
            if fixture.get("id") is None:
                blockers.append("football_fixture_id_missing")
            if not timestamp_ok(fixture.get("date")):
                blockers.append("football_fixture_date_invalid")
            counts["fixture_result_candidate"] += 1
            events = item.get("events", []) or []
            counts["event_context_candidate"] += len(events)
    return counts, sorted(set(blockers))


def build_source_terminal_report(root: Path) -> Dict[str, Any]:
    odds_path = root / "data/provider_fixtures/v254/odds_provider_snapshot.sample.json"
    football_path = root / "data/provider_fixtures/v254/football_fixture_event.sample.json"
    odds_fixture = read_json(odds_path)
    football_fixture = read_json(football_path)
    counts, blockers = normalize_source_counts(odds_fixture, football_fixture)
    adapter_count = 2
    adapter_ok_count = 0 if blockers else 2
    total_rows = sum(counts.values())
    ready_for_source_panel = not blockers and total_rows > 0
    return {
        "schema": "omnibet.source_terminal_report.v256",
        "report_id": "v258_generated_local_source_terminal_report",
        "created_by": "python_lab/source_terminal_generate.py",
        "paper_only": True,
        "quarantine_only": True,
        "source_terminal_visible": ready_for_source_panel,
        "adapter_count": adapter_count,
        "adapter_ok_count": adapter_ok_count,
        "normalized_total_rows": total_rows,
        "normalized_row_counts": counts,
        "readiness": {
            "adapter_health_ok": not blockers,
            "normalization_preview_ok": not blockers and total_rows > 0,
            "ready_for_source_panel": ready_for_source_panel,
            "ready_for_downstream_use": False,
            "reason": "generated_local_source_terminal_report" if ready_for_source_panel else "generated_report_has_blockers",
        },
        "allowed_ui_actions": ["inspect_adapters", "inspect_rows", "export_report"],
        "locked_ui_actions": ["provider_call", "bronze_write", "evaluation_run", "model_fit", "external_execution"],
        "blocker_summary": blockers,
        "input_fixtures": [str(odds_path), str(football_path)],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default=".omnibet-local/reports/local_v256_source_terminal_report.json")
    args = ap.parse_args()
    root = Path(args.root)
    report = build_source_terminal_report(root)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report.get("blocker_summary"):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
