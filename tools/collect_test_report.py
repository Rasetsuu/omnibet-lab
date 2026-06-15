#!/usr/bin/env python3
"""Collect OmniBet CI outputs into one compact JSON summary."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any, Dict


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"ok": False, "missing": str(path)}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return {"ok": False, "error": f"failed to parse {path}: {e}"}


def git_rev(root: Path) -> str | None:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    except Exception:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_summary.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    reports = root / "reports"

    core_verify = load_json(reports / "ci_verify_core_pack.json")
    event_verify = load_json(reports / "ci_verify_event_demo_pack.json")
    synth = load_json(reports / "v13_synthetic_event_pipeline.json")
    rust_compare = load_json(reports / "ci_rust_compare.json")
    rust_value = load_json(reports / "ci_rust_value_report.json")

    value_report = rust_value.get("report", {}) if isinstance(rust_value, dict) else {}
    selections = value_report.get("selections", []) if isinstance(value_report, dict) else []
    tickets = value_report.get("tickets", []) if isinstance(value_report, dict) else []

    paper_only_selections = all(
        str(x.get("decision", "")).startswith("PAPER ONLY") for x in selections
    ) if selections else False
    paper_only_tickets = all(
        str(x.get("decision", "")).startswith("PAPER ONLY") for x in tickets
    ) if tickets else False

    comparison = rust_compare.get("comparison", {}) if isinstance(rust_compare, dict) else {}
    baseline = comparison.get("baseline", {}) if isinstance(comparison, dict) else {}
    gold = comparison.get("gold_feature_heuristic", {}) if isinstance(comparison, dict) else {}

    summary = {
        "ok": True,
        "git_sha": git_rev(root),
        "core_pack_ok": bool(core_verify.get("ok")),
        "event_demo_pack_ok": bool(event_verify.get("ok")),
        "event_demo_counts": {
            "matches_norm": synth.get("counts_final", {}).get("matches_norm"),
            "match_events": synth.get("counts_final", {}).get("match_events"),
            "lineups": synth.get("counts_final", {}).get("lineups"),
            "players": synth.get("counts_final", {}).get("players"),
            "gold_goal_timing_features": synth.get("gold", {}).get("counts", {}).get("gold_goal_timing_features"),
            "gold_player_snapshots": synth.get("player_score", {}).get("snapshots_written"),
        },
        "model_compare": {
            "aligned_test_window": comparison.get("aligned_test_window"),
            "baseline_matches_tested": baseline.get("matches_tested"),
            "gold_matches_tested": gold.get("matches_tested"),
            "baseline_log_loss": baseline.get("log_loss"),
            "gold_log_loss": gold.get("log_loss"),
            "baseline_1x2_accuracy": baseline.get("one_x_two_accuracy"),
            "gold_1x2_accuracy": gold.get("one_x_two_accuracy"),
        },
        "value_gate": {
            "selection_count": len(selections),
            "ticket_count": len(tickets),
            "paper_only_selections": paper_only_selections,
            "paper_only_tickets": paper_only_tickets,
        },
        "reports": sorted(p.name for p in reports.glob("ci_*.json")),
    }

    summary["ok"] = bool(
        summary["core_pack_ok"]
        and summary["event_demo_pack_ok"]
        and summary["event_demo_counts"]["match_events"]
        and summary["event_demo_counts"]["gold_goal_timing_features"]
        and summary["event_demo_counts"]["gold_player_snapshots"]
        and summary["model_compare"]["aligned_test_window"] is True
        and summary["value_gate"]["paper_only_selections"]
        and summary["value_gate"]["paper_only_tickets"]
    )

    out_path = root / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    if not summary["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
