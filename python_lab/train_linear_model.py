#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

FEATURES = [
    {"name": "goals_for_avg_diff", "path": "features.goals_for_avg_diff", "default": 0.0},
    {"name": "goals_against_avg_diff", "path": "features.goals_against_avg_diff", "default": 0.0},
    {"name": "points_avg_diff", "path": "features.points_avg_diff", "default": 0.0},
    {"name": "rest_days_diff", "path": "features.rest_days_diff", "default": 0.0},
    {"name": "xg_for_avg_diff", "path": "features.xg_for_avg_diff", "fallback_home": "home_snapshot.xg_for_avg", "fallback_away": "away_snapshot.xg_for_avg", "default": 0.0},
    {"name": "xg_against_avg_diff", "path": "features.xg_against_avg_diff", "fallback_home": "home_snapshot.xg_against_avg", "fallback_away": "away_snapshot.xg_against_avg", "default": 0.0},
    {"name": "shots_for_avg_diff", "path": "features.shots_for_avg_diff", "fallback_home": "home_snapshot.shots_for_avg", "fallback_away": "away_snapshot.shots_for_avg", "default": 0.0},
    {"name": "shots_against_avg_diff", "path": "features.shots_against_avg_diff", "fallback_home": "home_snapshot.shots_against_avg", "fallback_away": "away_snapshot.shots_against_avg", "default": 0.0},
    {"name": "cards_for_avg_diff", "path": "features.cards_for_avg_diff", "fallback_home": "home_snapshot.cards_for_avg", "fallback_away": "away_snapshot.cards_for_avg", "default": 0.0},
]
CLASSES = ["H", "D", "A"]


def opt_num(obj: Dict[str, Any], path: str) -> Optional[float]:
    cur: Any = obj
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur or cur[part] is None:
            return None
        cur = cur[part]
    try:
        x = float(cur)
        return x if math.isfinite(x) else None
    except Exception:
        return None


def feature_value(obj: Dict[str, Any], spec: Dict[str, Any]) -> float:
    x = opt_num(obj, spec["path"])
    if x is not None:
        return x
    hp = spec.get("fallback_home")
    ap = spec.get("fallback_away")
    if hp and ap:
        h = opt_num(obj, hp)
        a = opt_num(obj, ap)
        if h is not None and a is not None:
            return h - a
        if h is not None:
            return h
        if a is not None:
            return -a
    return float(spec.get("default", 0.0))


def actual_class(hg: int, ag: int) -> int:
    if hg > ag:
        return 0
    if hg == ag:
        return 1
    return 2


def softmax(logits: List[float]) -> List[float]:
    m = max(logits)
    es = [math.exp(x - m) for x in logits]
    s = sum(es)
    return [x / s for x in es]


def log_loss(probs: List[float], y: int) -> float:
    return -math.log(max(1e-12, probs[y]))


def brier(probs: List[float], y: int) -> float:
    return sum((p - (1.0 if i == y else 0.0)) ** 2 for i, p in enumerate(probs))


def predict(x: List[float], intercept: List[float], weights: List[List[float]]) -> List[float]:
    logits = intercept[:]
    for j, val in enumerate(x):
        for c in range(3):
            logits[c] += val * weights[j][c]
    return softmax(logits)


def normalize(xs: List[List[float]]) -> Tuple[List[List[float]], List[float], List[float]]:
    if not xs:
        return xs, [], []
    cols = len(xs[0])
    means = [sum(row[j] for row in xs) / len(xs) for j in range(cols)]
    stds = []
    for j in range(cols):
        var = sum((row[j] - means[j]) ** 2 for row in xs) / max(1, len(xs) - 1)
        stds.append(math.sqrt(var) if var > 1e-12 else 1.0)
    norm = [[(row[j] - means[j]) / stds[j] for j in range(cols)] for row in xs]
    return norm, means, stds


def denormalize_params(intercept_norm: List[float], weights_norm: List[List[float]], means: List[float], stds: List[float]) -> Tuple[List[float], List[List[float]]]:
    weights = [[weights_norm[j][c] / stds[j] for c in range(3)] for j in range(len(weights_norm))]
    intercept = intercept_norm[:]
    for c in range(3):
        intercept[c] -= sum((means[j] / stds[j]) * weights_norm[j][c] for j in range(len(means)))
    return intercept, weights


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
        x = [feature_value(f, spec) for spec in FEATURES]
        y = actual_class(int(hg), int(ag))
        out.append({"match_id": mid, "date": date, "home": home, "away": away, "x": x, "y": y, "score": [hg, ag]})
    return out


def train(xs: List[List[float]], ys: List[int], epochs: int, lr: float, l2: float) -> Tuple[List[float], List[List[float]]]:
    intercept = [0.0, 0.0, 0.0]
    weights = [[0.0, 0.0, 0.0] for _ in range(len(xs[0]))]
    n = max(1, len(xs))
    for _ in range(epochs):
        gi = [0.0, 0.0, 0.0]
        gw = [[0.0, 0.0, 0.0] for _ in range(len(weights))]
        for x, y in zip(xs, ys):
            p = predict(x, intercept, weights)
            for c in range(3):
                err = p[c] - (1.0 if c == y else 0.0)
                gi[c] += err
                for j, v in enumerate(x):
                    gw[j][c] += err * v
        for c in range(3):
            intercept[c] -= lr * gi[c] / n
        for j in range(len(weights)):
            for c in range(3):
                weights[j][c] -= lr * ((gw[j][c] / n) + l2 * weights[j][c])
    return intercept, weights


def evaluate(rows: List[dict], intercept: List[float], weights: List[List[float]]) -> dict:
    if not rows:
        return {"rows": 0, "accuracy": None, "log_loss": None, "brier": None}
    losses = []
    briers = []
    correct = 0
    samples = []
    for r in rows:
        p = predict(r["x"], intercept, weights)
        pred = max(range(3), key=lambda i: p[i])
        correct += int(pred == r["y"])
        losses.append(log_loss(p, r["y"]))
        briers.append(brier(p, r["y"]))
        if len(samples) < 8:
            samples.append({"match_id": r["match_id"], "home": r["home"], "away": r["away"], "actual": CLASSES[r["y"]], "pick": CLASSES[pred], "probs": p})
    return {"rows": len(rows), "accuracy": correct / len(rows), "log_loss": sum(losses) / len(losses), "brier": sum(briers) / len(briers), "samples": samples}


def run(args: argparse.Namespace) -> dict:
    rows = load_rows(Path(args.db))
    split = max(1, int(len(rows) * args.train_ratio))
    split = min(split, max(1, len(rows) - 1)) if len(rows) > 1 else len(rows)
    train_rows = rows[:split]
    test_rows = rows[split:]
    x_train_raw = [r["x"] for r in train_rows]
    y_train = [r["y"] for r in train_rows]
    x_train_norm, means, stds = normalize(x_train_raw)
    intercept_n, weights_n = train(x_train_norm, y_train, args.epochs, args.lr, args.l2)
    intercept, weights = denormalize_params(intercept_n, weights_n, means, stds)

    model = {
        "name": args.model_name,
        "version": "0.22.0",
        "sport": "football",
        "target_market": "football.1x2",
        "settlement_scope": "regulation_time",
        "phase_scope": ["regulation_first_half", "regulation_first_half_stoppage", "regulation_second_half", "regulation_second_half_stoppage"],
        "model_trust": args.model_trust,
        "classes": CLASSES,
        "intercept": intercept,
        "features": FEATURES,
        "weights": weights,
        "calibration": {"shrink_alpha": args.shrink_alpha, "base_probs": [0.44, 0.27, 0.29]},
        "training_metadata": {
            "source_db": str(args.db),
            "rows_total": len(rows),
            "rows_train": len(train_rows),
            "rows_test": len(test_rows),
            "train_ratio": args.train_ratio,
            "epochs": args.epochs,
            "lr": args.lr,
            "l2": args.l2,
            "normalization": {"means": means, "stds": stds},
            "warning": "Tiny CI smoke training artifact; not a betting edge proof.",
        },
        "notes": "Phase-aware Python-trained multinomial logistic model artifact. Kept PAPER_ONLY by low trust.",
    }

    train_eval = evaluate(train_rows, intercept, weights)
    test_eval = evaluate(test_rows, intercept, weights)
    report = {
        "ok": len(rows) > 3 and len(train_rows) > 0 and len(test_rows) > 0,
        "model_path": str(args.out_model),
        "model_name": args.model_name,
        "settlement_scope": "regulation_time",
        "phase_aware": True,
        "rows_total": len(rows),
        "train": train_eval,
        "test": test_eval,
        "model_trust": args.model_trust,
        "trust_decision": "PAPER_ONLY" if args.model_trust < 0.5 else "TRUSTED_FOR_STAKING_LABELS",
    }

    Path(args.out_model).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_model).write_text(json.dumps(model, indent=2), encoding="utf-8")
    Path(args.out_report).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out_report).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Train/export a phase-aware football linear model artifact.")
    ap.add_argument("--db", default="../build/omnibet_v20_statsbomb_scale.sqlite")
    ap.add_argument("--out-model", default="../build/models/football_regulation_linear_trained_v1.json")
    ap.add_argument("--out-report", default="../reports/ci_v22_train_export.json")
    ap.add_argument("--model-name", default="football_regulation_linear_trained_v1")
    ap.add_argument("--train-ratio", type=float, default=0.75)
    ap.add_argument("--epochs", type=int, default=500)
    ap.add_argument("--lr", type=float, default=0.08)
    ap.add_argument("--l2", type=float, default=0.02)
    ap.add_argument("--shrink-alpha", type=float, default=0.20)
    ap.add_argument("--model-trust", type=float, default=0.35)
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
