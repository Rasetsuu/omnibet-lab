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


def counts_from_v13(synth: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "matches_norm": synth.get("counts_final", {}).get("matches_norm"),
        "match_events": synth.get("counts_final", {}).get("match_events"),
        "lineups": synth.get("counts_final", {}).get("lineups"),
        "players": synth.get("counts_final", {}).get("players"),
        "gold_goal_timing_features": synth.get("gold", {}).get("counts", {}).get("gold_goal_timing_features"),
        "gold_player_snapshots": synth.get("player_score", {}).get("snapshots_written"),
    }


def counts_from_statsbomb(report: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "matches_norm": report.get("after_counts", {}).get("matches_norm"),
        "match_events": report.get("after_counts", {}).get("match_events"),
        "lineups": report.get("after_counts", {}).get("lineups"),
        "players": report.get("after_counts", {}).get("players"),
        "gold_goal_timing_features": report.get("gold", {}).get("counts", {}).get("gold_goal_timing_features"),
        "gold_player_snapshots": report.get("player_score", {}).get("snapshots_written"),
    }


def all_positive(d: Dict[str, Any]) -> bool:
    return all(int(v or 0) > 0 for v in d.values())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out", default="reports/ci_summary.json")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    reports = root / "reports"

    ui = load_json(reports / "ci_ui_wiring.json")
    core_verify = load_json(reports / "ci_verify_core_pack.json")
    event_verify = load_json(reports / "ci_verify_event_demo_pack.json")
    statsbomb_verify = load_json(reports / "ci_verify_statsbomb_sample_pack.json")
    statsbomb_scale_verify = load_json(reports / "ci_verify_statsbomb_scale_pack.json")
    synth = load_json(reports / "v13_synthetic_event_pipeline.json")
    statsbomb = load_json(reports / "v14_statsbomb_public_sample.json")
    statsbomb_scale = load_json(reports / "ci_v20_data_scale.json")
    event_compare = load_json(reports / "ci_event_aware_compare.json")
    rust_linear = load_json(reports / "ci_rust_event_linear_model.json")
    rust_compare = load_json(reports / "ci_rust_compare.json")
    rust_value = load_json(reports / "ci_rust_value_report.json")
    paper = load_json(reports / "ci_paper_ledger.json")

    value_report = rust_value.get("report", {}) if isinstance(rust_value, dict) else {}
    selections = value_report.get("selections", []) if isinstance(value_report, dict) else []
    tickets = value_report.get("tickets", []) if isinstance(value_report, dict) else []

    paper_only_selections = all(str(x.get("decision", "")).startswith("PAPER ONLY") for x in selections) if selections else False
    paper_only_tickets = all(str(x.get("decision", "")).startswith("PAPER ONLY") for x in tickets) if tickets else False

    comparison = rust_compare.get("comparison", {}) if isinstance(rust_compare, dict) else {}
    baseline = comparison.get("baseline", {}) if isinstance(comparison, dict) else {}
    gold = comparison.get("gold_feature_heuristic", {}) if isinstance(comparison, dict) else {}
    linear_report = rust_linear.get("linear_model_backtest", {}) if isinstance(rust_linear, dict) else {}

    synthetic_counts = counts_from_v13(synth)
    statsbomb_counts = counts_from_statsbomb(statsbomb)
    scale_required = statsbomb_scale.get("required_positive", {}) if isinstance(statsbomb_scale, dict) else {}
    scale_pack = statsbomb_scale.get("pack_summary", {}) if isinstance(statsbomb_scale, dict) else {}
    scale_quality = statsbomb_scale.get("quality", {}) if isinstance(statsbomb_scale, dict) else {}

    event_compare_summary = {
        "ok": bool(event_compare.get("ok")),
        "gold_rows": event_compare.get("gold_rows"),
        "event_history_rows": event_compare.get("event_history_rows"),
        "match_only_log_loss": event_compare.get("match_only_on_event_rows", {}).get("log_loss"),
        "event_aware_log_loss": event_compare.get("event_aware_on_event_rows", {}).get("log_loss"),
        "event_minus_match_log_loss": event_compare.get("event_minus_match_log_loss"),
    }

    rust_linear_summary = {
        "ok": bool(rust_linear.get("ok")) and bool(linear_report.get("ok")),
        "model_name": linear_report.get("model_name"),
        "model_version": linear_report.get("model_version"),
        "model_trust": linear_report.get("model_trust"),
        "trust_decision": linear_report.get("trust_decision"),
        "rows_tested": linear_report.get("rows_tested"),
        "accuracy": linear_report.get("accuracy"),
        "log_loss": linear_report.get("log_loss"),
        "brier": linear_report.get("brier"),
    }

    paper_summary = {
        "ok": bool(paper.get("ok")),
        "paper_bets_written": paper.get("paper_bets_written"),
        "clv_rows_written": paper.get("clv_rows_written"),
        "all_paper_only": paper.get("all_paper_only"),
        "avg_clv_percent": paper.get("avg_clv_percent"),
        "positive_clv_rows": paper.get("positive_clv_rows"),
        "negative_clv_rows": paper.get("negative_clv_rows"),
    }

    scale_summary = {
        "ok": bool(statsbomb_scale.get("ok")) and bool(statsbomb_scale_verify.get("ok")),
        "profile": statsbomb_scale.get("profile"),
        "matches_norm": scale_required.get("matches_norm"),
        "match_events": scale_required.get("match_events"),
        "lineups": scale_required.get("lineups"),
        "players": scale_required.get("players"),
        "pack_rows": scale_required.get("pack_rows"),
        "compressed_bytes": scale_required.get("compressed_bytes"),
        "overall_compression_ratio": scale_pack.get("overall_compression_ratio"),
        "event_match_coverage": scale_quality.get("event_match_coverage"),
        "storage_plan": statsbomb_scale.get("storage_plan"),
    }

    summary = {
        "ok": True,
        "git_sha": git_rev(root),
        "ui_wiring": ui,
        "core_pack_ok": bool(core_verify.get("ok")),
        "event_demo_pack_ok": bool(event_verify.get("ok")),
        "statsbomb_sample_pack_ok": bool(statsbomb_verify.get("ok")),
        "statsbomb_scale_pack_ok": bool(statsbomb_scale_verify.get("ok")),
        "event_demo_counts": synthetic_counts,
        "statsbomb_public_sample_counts": statsbomb_counts,
        "statsbomb_selected_match_ids": statsbomb.get("sample", {}).get("selected_match_ids"),
        "statsbomb_scale": scale_summary,
        "event_aware_compare": event_compare_summary,
        "rust_linear_model": rust_linear_summary,
        "paper_ledger": paper_summary,
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
        summary["ui_wiring"].get("ok")
        and summary["core_pack_ok"]
        and summary["event_demo_pack_ok"]
        and summary["statsbomb_sample_pack_ok"]
        and summary["statsbomb_scale_pack_ok"]
        and all_positive(summary["event_demo_counts"])
        and all_positive(summary["statsbomb_public_sample_counts"])
        and summary["statsbomb_scale"]["ok"]
        and all_positive({k: v for k, v in scale_required.items() if k != "compressed_bytes"})
        and int(scale_required.get("compressed_bytes") or 0) > 0
        and summary["event_aware_compare"]["ok"]
        and int(summary["event_aware_compare"]["event_history_rows"] or 0) > 0
        and summary["rust_linear_model"]["ok"]
        and int(summary["rust_linear_model"]["rows_tested"] or 0) > 0
        and summary["rust_linear_model"]["trust_decision"] == "PAPER_ONLY"
        and summary["paper_ledger"]["ok"]
        and int(summary["paper_ledger"]["paper_bets_written"] or 0) > 0
        and int(summary["paper_ledger"]["clv_rows_written"] or 0) > 0
        and summary["paper_ledger"]["all_paper_only"] is True
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
