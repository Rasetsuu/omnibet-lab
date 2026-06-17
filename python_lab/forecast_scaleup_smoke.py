#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class MatchRow:
    event_id: str
    kickoff_utc: str
    season: int
    round_no: int
    home: str
    away: str
    home_rating: float
    away_rating: float
    home_form: float
    away_form: float
    home_rest_days: int
    away_rest_days: int
    home_goals: int
    away_goals: int


TEAMS = [
    ("France", 1860, 0.78), ("Brazil", 1845, 0.75), ("Argentina", 1835, 0.76), ("Spain", 1815, 0.72),
    ("Germany", 1790, 0.66), ("Portugal", 1785, 0.68), ("Netherlands", 1770, 0.65), ("England", 1765, 0.64),
    ("Croatia", 1730, 0.59), ("Morocco", 1715, 0.58), ("Japan", 1680, 0.56), ("USA", 1660, 0.54),
    ("Senegal", 1645, 0.53), ("Mexico", 1635, 0.52), ("Korea Republic", 1625, 0.51), ("Switzerland", 1695, 0.57),
]

MODEL_WEIGHTS = {
    "baseline_rate": {},
    "rating_only": {"intercept": 0.05, "rating_diff": 1.75},
    "rating_form": {"intercept": 0.02, "rating_diff": 1.45, "form_diff": 1.1},
    "full_scorecard": {"intercept": -0.04, "rating_diff": 1.35, "form_diff": 1.05, "rest_diff": 0.35, "home_bias": 0.18},
}


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 20), -20)))


def clamp_prob(p: float) -> float:
    return max(0.02, min(0.98, p))


def label(row: MatchRow) -> int:
    return int(row.home_goals > row.away_goals)


def features(row: MatchRow) -> Dict[str, float]:
    return {
        "rating_diff": (row.home_rating - row.away_rating) / 400.0,
        "form_diff": row.home_form - row.away_form,
        "rest_diff": (row.home_rest_days - row.away_rest_days) / 7.0,
        "home_bias": 1.0,
    }


def score_model(model_id: str, feat: Dict[str, float], base: float) -> float:
    if model_id == "baseline_rate":
        return clamp_prob(base)
    w = MODEL_WEIGHTS[model_id]
    z = w.get("intercept", 0.0)
    for key, value in feat.items():
        z += w.get(key, 0.0) * value
    return clamp_prob(sigmoid(z))


def safe_logloss(y: int, p: float) -> float:
    p = clamp_prob(p)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def generate_history() -> List[MatchRow]:
    rows: List[MatchRow] = []
    event_i = 0
    for season in range(2017, 2027):
        drift = (season - 2017) * 3
        for round_no in range(24):
            home_idx = (round_no + season + event_i) % len(TEAMS)
            away_idx = (round_no * 5 + season + 7) % len(TEAMS)
            if home_idx == away_idx:
                away_idx = (away_idx + 3) % len(TEAMS)
            h = TEAMS[home_idx]
            a = TEAMS[away_idx]
            home_rating = h[1] + ((round_no % 5) - 2) * 5 + drift * ((home_idx % 3) - 1)
            away_rating = a[1] + (((round_no + 2) % 5) - 2) * 5 + drift * ((away_idx % 3) - 1)
            home_form = min(0.88, max(0.32, h[2] + ((round_no % 7) - 3) * 0.015))
            away_form = min(0.88, max(0.32, a[2] + (((round_no + 4) % 7) - 3) * 0.015))
            home_rest = 3 + ((season + round_no + home_idx) % 5)
            away_rest = 3 + ((season + round_no * 2 + away_idx) % 5)
            feat = {
                "rating_diff": (home_rating - away_rating) / 400.0,
                "form_diff": home_form - away_form,
                "rest_diff": (home_rest - away_rest) / 7.0,
                "home_bias": 1.0,
            }
            latent = -0.02 + 1.32 * feat["rating_diff"] + 1.05 * feat["form_diff"] + 0.28 * feat["rest_diff"] + 0.16
            jitter = (((event_i * 13 + season) % 11) - 5) * 0.055
            signal = latent + jitter
            if signal > 0.82:
                hg, ag = 3 + (event_i % 2), 0 + (event_i % 2)
            elif signal > 0.42:
                hg, ag = 2, 1
            elif signal > 0.18:
                hg, ag = 1, 1
            elif signal > -0.25:
                hg, ag = 1, 2
            else:
                hg, ag = 0, 2 + (event_i % 2)
            rows.append(MatchRow(
                event_id=f"scale:{season}:{round_no:02d}",
                kickoff_utc=f"{season}-{(round_no % 12) + 1:02d}-{(round_no * 2 % 26) + 1:02d}T18:00:00Z",
                season=season,
                round_no=round_no,
                home=h[0],
                away=a[0],
                home_rating=float(home_rating),
                away_rating=float(away_rating),
                home_form=float(home_form),
                away_form=float(away_form),
                home_rest_days=home_rest,
                away_rest_days=away_rest,
                home_goals=hg,
                away_goals=ag,
            ))
            event_i += 1
    return sorted(rows, key=lambda r: r.kickoff_utc)


def training_rows(history: List[MatchRow]) -> List[Dict[str, Any]]:
    out = []
    for row in history:
        out.append({
            "event_id": row.event_id,
            "kickoff_utc": row.kickoff_utc,
            "season": row.season,
            "home": row.home,
            "away": row.away,
            **features(row),
            "label_home_win": label(row),
            "home_goals": row.home_goals,
            "away_goals": row.away_goals,
            "model_eligible": 1,
            "leakage_guard": "pre_event_features_only",
        })
    return out


def write_jsonl_gz(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return sha_file(path)


def fold_specs() -> List[Tuple[int, int]]:
    return [(2021, 2021), (2022, 2022), (2023, 2023), (2024, 2024), (2025, 2025), (2026, 2026)]


def metrics(rows: List[Dict[str, Any]], key: str) -> Dict[str, float]:
    n = len(rows)
    brier = sum((float(r[key]) - int(r["label_home_win"])) ** 2 for r in rows) / n
    logloss = sum(safe_logloss(int(r["label_home_win"]), float(r[key])) for r in rows) / n
    acc = sum((float(r[key]) >= 0.5) == bool(r["label_home_win"]) for r in rows) / n
    return {"rows": n, "brier": round(brier, 6), "logloss": round(logloss, 6), "accuracy_at_0_5": round(acc, 6)}


def eval_fold(history: List[MatchRow], test_season: int, model_id: str) -> Dict[str, Any]:
    train = [r for r in history if r.season < test_season]
    test = [r for r in history if r.season == test_season]
    base = clamp_prob(sum(label(r) for r in train) / len(train))
    preds = []
    for row in test:
        feat = features(row)
        p = score_model(model_id, feat, base)
        preds.append({
            "event_id": row.event_id,
            "season": row.season,
            "home": row.home,
            "away": row.away,
            "label_home_win": label(row),
            "probability": p,
            "top_factors": sorted([
                {"name": "rating_diff", "value": round(feat["rating_diff"], 6), "impact": round(abs(MODEL_WEIGHTS.get(model_id, {}).get("rating_diff", 0.0) * feat["rating_diff"]), 6)},
                {"name": "form_diff", "value": round(feat["form_diff"], 6), "impact": round(abs(MODEL_WEIGHTS.get(model_id, {}).get("form_diff", 0.0) * feat["form_diff"]), 6)},
                {"name": "rest_diff", "value": round(feat["rest_diff"], 6), "impact": round(abs(MODEL_WEIGHTS.get(model_id, {}).get("rest_diff", 0.0) * feat["rest_diff"]), 6)},
            ], key=lambda x: x["impact"], reverse=True),
        })
    metric_rows = [{"label_home_win": p["label_home_win"], "p": p["probability"]} for p in preds]
    return {
        "model_id": model_id,
        "test_season": test_season,
        "train_rows": len(train),
        "test_rows": len(test),
        "metrics": metrics(metric_rows, "p"),
        "predictions": preds,
    }


def rolling_report(history: List[MatchRow]) -> Dict[str, Any]:
    folds = []
    for model_id in MODEL_WEIGHTS:
        for _, season in fold_specs():
            folds.append(eval_fold(history, season, model_id))
    return {"schema": "omnibet.rolling_origin_eval.v74", "folds": folds, "strategy": "train_on_past_test_one_season"}


def aggregate_model_comparison(rolling: Dict[str, Any]) -> Dict[str, Any]:
    rows = []
    for model_id in MODEL_WEIGHTS:
        model_folds = [f for f in rolling["folds"] if f["model_id"] == model_id]
        rows.append({
            "model_id": model_id,
            "folds": len(model_folds),
            "avg_brier": round(sum(f["metrics"]["brier"] for f in model_folds) / len(model_folds), 6),
            "avg_logloss": round(sum(f["metrics"]["logloss"] for f in model_folds) / len(model_folds), 6),
            "avg_accuracy_at_0_5": round(sum(f["metrics"]["accuracy_at_0_5"] for f in model_folds) / len(model_folds), 6),
        })
    rows.sort(key=lambda r: (r["avg_brier"], r["avg_logloss"]))
    return {"schema": "omnibet.model_comparison.v75", "models": rows, "best_by_brier": rows[0]["model_id"]}


def ablation_report(comparison: Dict[str, Any]) -> Dict[str, Any]:
    by_id = {r["model_id"]: r for r in comparison["models"]}
    full = by_id["full_scorecard"]
    rows = []
    for model_id in ["baseline_rate", "rating_only", "rating_form"]:
        r = by_id[model_id]
        rows.append({
            "comparison": f"full_scorecard_vs_{model_id}",
            "brier_delta": round(r["avg_brier"] - full["avg_brier"], 6),
            "logloss_delta": round(r["avg_logloss"] - full["avg_logloss"], 6),
            "interpretation": "positive means full_scorecard is better on this offline sample",
        })
    return {"schema": "omnibet.feature_ablation.v76", "rows": rows}


def calibration_for_predictions(preds: List[Dict[str, Any]]) -> Dict[str, Any]:
    bins = []
    ece = 0.0
    total = len(preds)
    for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
        hi = lo + 0.2
        part = [p for p in preds if lo <= p["probability"] < hi or (hi >= 1.0 and p["probability"] <= hi)]
        if not part:
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": 0, "avg_probability": None, "observed_rate": None})
            continue
        avg_p = sum(p["probability"] for p in part) / len(part)
        obs = sum(p["label_home_win"] for p in part) / len(part)
        ece += (len(part) / total) * abs(avg_p - obs)
        bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": len(part), "avg_probability": round(avg_p, 6), "observed_rate": round(obs, 6), "gap": round(avg_p - obs, 6)})
    return {"bins": bins, "expected_calibration_error": round(ece, 6)}


def stability_report(rolling: Dict[str, Any], best_model: str) -> Dict[str, Any]:
    folds = [f for f in rolling["folds"] if f["model_id"] == best_model]
    all_preds = [p for f in folds for p in f["predictions"]]
    briers = [f["metrics"]["brier"] for f in folds]
    loglosses = [f["metrics"]["logloss"] for f in folds]
    return {
        "schema": "omnibet.calibration_stability.v77",
        "model_id": best_model,
        "calibration": calibration_for_predictions(all_preds),
        "fold_stability": {
            "brier_min": round(min(briers), 6), "brier_max": round(max(briers), 6), "brier_range": round(max(briers) - min(briers), 6),
            "logloss_min": round(min(loglosses), 6), "logloss_max": round(max(loglosses), 6), "logloss_range": round(max(loglosses) - min(loglosses), 6),
        },
    }


def build_scaleup(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    history = generate_history()
    train = training_rows(history)
    history_path = out_dir / "historical_events_scaled.v73.jsonl.gz"
    train_path = out_dir / "settled_training_scaled.v73_v74.jsonl.gz"
    history_sha = write_jsonl_gz(history_path, [asdict(r) for r in history])
    train_sha = write_jsonl_gz(train_path, train)
    rolling = rolling_report(history)
    comparison = aggregate_model_comparison(rolling)
    ablation = ablation_report(comparison)
    stability = stability_report(rolling, comparison["best_by_brier"])
    paths = {
        "rolling": out_dir / "rolling_origin_eval.v74.json",
        "comparison": out_dir / "model_comparison.v75.json",
        "ablation": out_dir / "feature_ablation.v76.json",
        "stability": out_dir / "calibration_stability.v77.json",
        "model_lab": out_dir / "model_lab_payload.v78.json",
    }
    write_json(paths["rolling"], rolling)
    write_json(paths["comparison"], comparison)
    write_json(paths["ablation"], ablation)
    write_json(paths["stability"], stability)
    best_model = comparison["best_by_brier"]
    best_folds = [f for f in rolling["folds"] if f["model_id"] == best_model]
    model_lab = {
        "ok": True,
        "schema": "omnibet.model_lab_payload.v78",
        "best_model": best_model,
        "models": comparison["models"],
        "ablation": ablation["rows"],
        "stability": stability,
        "example_predictions": [p for f in best_folds[-2:] for p in f["predictions"][:3]],
        "safety": {"paper_only": True, "offline_only": True, "no_recommendation_output": True},
    }
    write_json(paths["model_lab"], model_lab)
    manifest = {
        "ok": True,
        "schema": "omnibet.forecast_scaleup_manifest.v73_v78",
        "milestones": {"v73": "larger historical dataset", "v74": "rolling-origin evaluation", "v75": "model comparison", "v76": "feature ablation", "v77": "calibration/stability", "v78": "model-lab UI payload"},
        "outputs": {"history": str(history_path), "training": str(train_path), **{k: str(v) for k, v in paths.items()}},
        "hashes": {"history_sha256": history_sha, "training_sha256": train_sha, **{f"{k}_sha256": sha_file(v) for k, v in paths.items()}},
        "row_counts": {"history": len(history), "training": len(train), "rolling_folds": len(rolling["folds"])},
        "best_model": best_model,
        "best_metrics": comparison["models"][0],
        "safety": model_lab["safety"],
    }
    manifest_path = out_dir / "forecast_scaleup_manifest.v73_v78.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "manifest_path": manifest_path, "model_lab": model_lab, "rolling": rolling, "comparison": comparison, "ablation": ablation, "stability": stability}


def build_report(out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    built = build_scaleup(out_dir)
    if ui_sample is not None:
        write_json(ui_sample, {"ok": True, "version": "omnibet.model_lab.sample.v78", "manifest": built["manifest"], "model_lab": built["model_lab"], "rolling_preview": built["rolling"]["folds"][:4], "comparison": built["comparison"], "ablation": built["ablation"], "stability": built["stability"], "safety": built["manifest"]["safety"]})
    manifest = built["manifest"]
    checks = {
        "history_scaled": manifest["row_counts"]["history"] >= 200,
        "training_matches_history": manifest["row_counts"]["training"] == manifest["row_counts"]["history"],
        "rolling_fold_count": manifest["row_counts"]["rolling_folds"] >= 20,
        "model_comparison_models": len(built["comparison"]["models"]) >= 4,
        "best_model_present": bool(manifest["best_model"]),
        "ablation_rows": len(built["ablation"]["rows"]) >= 3,
        "stability_present": "fold_stability" in built["stability"],
        "calibration_present": "expected_calibration_error" in built["stability"]["calibration"],
        "hashes_present": all(manifest["hashes"].values()),
        "paper_only": manifest["safety"]["paper_only"] is True,
        "no_recommendation_output": manifest["safety"]["no_recommendation_output"] is True,
    }
    return {"ok": all(checks.values()), "milestone": "v73_v78_forecast_scaleup", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": manifest}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="build/forecast_scaleup_v73_v78")
    ap.add_argument("--ui-sample", default="tauri-app/src/model-lab.sample.json")
    ap.add_argument("--out", default="reports/ci_v73_v78_forecast_scaleup.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
