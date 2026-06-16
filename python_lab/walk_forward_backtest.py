#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import List, Tuple

from train_linear_model import CLASSES, FEATURES, actual_class, brier, feature_value, log_loss, predict, train


def load_rows(db: Path) -> List[dict]:
    con = sqlite3.connect(str(db))
    rows = con.execute(
        """SELECT match_id, match_date, home_team_name, away_team_name,
                  target_home_goals, target_away_goals, features_json
           FROM gold_match_features
           WHERE target_home_goals IS NOT NULL AND target_away_goals IS NOT NULL
           ORDER BY match_date, match_id"""
    ).fetchall()
    con.close()
    out = []
    for mid, date, home, away, hg, ag, fj in rows:
        f = json.loads(fj)
        out.append({
            "match_id": mid,
            "date": date,
            "home": home,
            "away": away,
            "score": [hg, ag],
            "x": [feature_value(f, spec) for spec in FEATURES],
            "y": actual_class(int(hg), int(ag)),
        })
    return out


def normalize_with_train(train_x: List[List[float]], rows_x: List[List[float]]) -> Tuple[List[List[float]], List[float], List[float]]:
    cols = len(train_x[0])
    means = [sum(row[j] for row in train_x) / len(train_x) for j in range(cols)]
    stds = []
    for j in range(cols):
        var = sum((row[j] - means[j]) ** 2 for row in train_x) / max(1, len(train_x) - 1)
        stds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    norm = [[(row[j] - means[j]) / stds[j] for j in range(cols)] for row in rows_x]
    return norm, means, stds


def denorm(intercept_n: List[float], weights_n: List[List[float]], means: List[float], stds: List[float]) -> Tuple[List[float], List[List[float]]]:
    weights = [[weights_n[j][c] / stds[j] for c in range(3)] for j in range(len(weights_n))]
    intercept = intercept_n[:]
    for c in range(3):
        intercept[c] -= sum((means[j] / stds[j]) * weights_n[j][c] for j in range(len(means)))
    return intercept, weights


def baseline_probs(train_rows: List[dict]) -> List[float]:
    counts = [1.0, 1.0, 1.0]
    for r in train_rows:
        counts[r["y"]] += 1.0
    s = sum(counts)
    return [x / s for x in counts]


def evaluate_walk(rows: List[dict], args: argparse.Namespace) -> dict:
    preds = []
    for idx in range(args.min_train, len(rows)):
        train_rows = rows[:idx]
        test_row = rows[idx]
        x_train_raw = [r["x"] for r in train_rows]
        x_train_norm, means, stds = normalize_with_train(x_train_raw, x_train_raw)
        y_train = [r["y"] for r in train_rows]
        intercept_n, weights_n = train(x_train_norm, y_train, args.epochs, args.lr, args.l2)
        intercept, weights = denorm(intercept_n, weights_n, means, stds)
        p = predict(test_row["x"], intercept, weights)
        bp = baseline_probs(train_rows)
        pick_idx = max(range(3), key=lambda c: p[c])
        base_pick_idx = max(range(3), key=lambda c: bp[c])
        rec = {
            "step": idx - args.min_train + 1,
            "train_rows": idx,
            "match_id": test_row["match_id"],
            "date": test_row["date"],
            "home": test_row["home"],
            "away": test_row["away"],
            "score": test_row["score"],
            "actual": CLASSES[test_row["y"]],
            "walk_pick": CLASSES[pick_idx],
            "walk_probs": p,
            "walk_log_loss": log_loss(p, test_row["y"]),
            "walk_brier": brier(p, test_row["y"]),
            "baseline_pick": CLASSES[base_pick_idx],
            "baseline_probs": bp,
            "baseline_log_loss": log_loss(bp, test_row["y"]),
            "baseline_brier": brier(bp, test_row["y"]),
        }
        preds.append(rec)
    return summarize(preds)


def summarize(preds: List[dict]) -> dict:
    if not preds:
        return {"rows_tested": 0, "ok": False}
    n = len(preds)
    walk_acc = sum(1 for r in preds if r["walk_pick"] == r["actual"]) / n
    base_acc = sum(1 for r in preds if r["baseline_pick"] == r["actual"]) / n
    walk_ll = sum(r["walk_log_loss"] for r in preds) / n
    base_ll = sum(r["baseline_log_loss"] for r in preds) / n
    walk_brier = sum(r["walk_brier"] for r in preds) / n
    base_brier = sum(r["baseline_brier"] for r in preds) / n
    return {
        "ok": True,
        "rows_tested": n,
        "walk_forward": {"accuracy": walk_acc, "log_loss": walk_ll, "brier": walk_brier},
        "expanding_prior_baseline": {"accuracy": base_acc, "log_loss": base_ll, "brier": base_brier},
        "deltas": {
            "log_loss_minus_baseline": walk_ll - base_ll,
            "brier_minus_baseline": walk_brier - base_brier,
            "accuracy_minus_baseline": walk_acc - base_acc,
        },
        "samples": preds[:8],
    }


def run(args: argparse.Namespace) -> dict:
    rows = load_rows(Path(args.db))
    wf = evaluate_walk(rows, args)
    report = {
        "ok": bool(wf.get("ok")) and int(wf.get("rows_tested") or 0) >= args.min_test_rows,
        "warning": "Small CI walk-forward smoke. This validates no-future-leak evaluation shape, not betting edge.",
        "db": str(args.db),
        "target_market": "football.1x2",
        "settlement_scope": "regulation_time",
        "phase_scope": ["regulation_first_half", "regulation_first_half_stoppage", "regulation_second_half", "regulation_second_half_stoppage"],
        "model_trust": args.model_trust,
        "trust_decision": "PAPER_ONLY" if args.model_trust < 0.5 else "TRUSTED_FOR_STAKING_LABELS",
        "rows_total": len(rows),
        "min_train": args.min_train,
        "min_test_rows": args.min_test_rows,
        "walk_forward_report": wf,
        "leakage_guard": {
            "train_window": "expanding_past_only",
            "test_window": "next_future_match_only",
            "ordered_by": "match_date, match_id",
        },
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Run small expanding-window walk-forward backtest.")
    ap.add_argument("--db", default="../build/omnibet_v20_statsbomb_scale.sqlite")
    ap.add_argument("--out", default="../reports/ci_v24_walk_forward.json")
    ap.add_argument("--min-train", type=int, default=6)
    ap.add_argument("--min-test-rows", type=int, default=4)
    ap.add_argument("--epochs", type=int, default=250)
    ap.add_argument("--lr", type=float, default=0.08)
    ap.add_argument("--l2", type=float, default=0.03)
    ap.add_argument("--model-trust", type=float, default=0.35)
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
