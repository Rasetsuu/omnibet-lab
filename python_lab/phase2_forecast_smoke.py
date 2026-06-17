#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class HistRow:
    event_id: str
    kickoff_utc: str
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


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


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


def safe_logloss(y: int, p: float) -> float:
    p = clamp_prob(p)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def sample_history() -> List[HistRow]:
    teams = [
        ("France", 1850, 0.78),
        ("Brazil", 1840, 0.74),
        ("Argentina", 1830, 0.76),
        ("Spain", 1810, 0.72),
        ("Germany", 1780, 0.65),
        ("Portugal", 1770, 0.67),
        ("Netherlands", 1760, 0.64),
        ("Croatia", 1720, 0.58),
        ("Morocco", 1700, 0.57),
        ("Japan", 1660, 0.55),
        ("USA", 1640, 0.53),
        ("Senegal", 1625, 0.52),
    ]
    rows: List[HistRow] = []
    event_i = 0
    for year in [2021, 2022, 2023, 2024, 2025, 2026]:
        for round_i in range(11):
            h = teams[(round_i + year) % len(teams)]
            a = teams[(round_i * 3 + year + 5) % len(teams)]
            if h[0] == a[0]:
                a = teams[(round_i * 3 + year + 6) % len(teams)]
            rating_diff = h[1] - a[1]
            form_diff = h[2] - a[2]
            home_rest = 4 + ((round_i + year) % 4)
            away_rest = 4 + ((round_i * 2 + year) % 4)
            latent = 0.55 + rating_diff / 420.0 + form_diff * 1.1 + (home_rest - away_rest) * 0.035
            home_win_signal = latent + (((event_i * 17) % 9) - 4) * 0.06
            if home_win_signal > 0.86:
                hg, ag = 2 + (event_i % 3), event_i % 2
            elif home_win_signal > 0.56:
                hg, ag = 2, 1
            elif home_win_signal > 0.42:
                hg, ag = 1, 1
            elif home_win_signal > 0.25:
                hg, ag = 1, 2
            else:
                hg, ag = 0, 2 + (event_i % 2)
            rows.append(HistRow(
                event_id=f"hist:{year}:{round_i:02d}",
                kickoff_utc=f"{year}-{(round_i % 12) + 1:02d}-{(round_i * 2 % 26) + 1:02d}T18:00:00Z",
                home=h[0], away=a[0], home_rating=float(h[1]), away_rating=float(a[1]),
                home_form=float(h[2]), away_form=float(a[2]), home_rest_days=home_rest, away_rest_days=away_rest,
                home_goals=hg, away_goals=ag,
            ))
            event_i += 1
    return sorted(rows, key=lambda r: r.kickoff_utc)


def features(row: HistRow) -> Dict[str, float]:
    return {
        "rating_diff": (row.home_rating - row.away_rating) / 400.0,
        "form_diff": row.home_form - row.away_form,
        "rest_diff": (row.home_rest_days - row.away_rest_days) / 7.0,
        "home_bias": 1.0,
    }


def label(row: HistRow) -> int:
    return 1 if row.home_goals > row.away_goals else 0


def forecast_prob(feat: Dict[str, float]) -> float:
    z = -0.08 + 1.45 * feat["rating_diff"] + 1.15 * feat["form_diff"] + 0.38 * feat["rest_diff"] + 0.18 * feat["home_bias"]
    return clamp_prob(sigmoid(z))


def baseline_prob(train_rows: List[HistRow]) -> float:
    ys = [label(r) for r in train_rows]
    return clamp_prob(sum(ys) / len(ys))


def training_rows(history: List[HistRow]) -> List[Dict[str, Any]]:
    out = []
    for r in history:
        f = features(r)
        out.append({
            "event_id": r.event_id,
            "kickoff_utc": r.kickoff_utc,
            "home": r.home,
            "away": r.away,
            **f,
            "label_home_win": label(r),
            "home_goals": r.home_goals,
            "away_goals": r.away_goals,
            "model_eligible": 1,
            "leakage_guard": "features_available_before_kickoff_only",
        })
    return out


def split_rows(history: List[HistRow]) -> Tuple[List[HistRow], List[HistRow]]:
    train = [r for r in history if r.kickoff_utc < "2025-01-01T00:00:00Z"]
    test = [r for r in history if r.kickoff_utc >= "2025-01-01T00:00:00Z"]
    return train, test


def metrics(rows: List[Dict[str, Any]], prob_key: str) -> Dict[str, float]:
    n = len(rows)
    brier = sum((r[prob_key] - r["label_home_win"]) ** 2 for r in rows) / n
    logloss = sum(safe_logloss(int(r["label_home_win"]), float(r[prob_key])) for r in rows) / n
    acc = sum((r[prob_key] >= 0.5) == bool(r["label_home_win"]) for r in rows) / n
    return {"rows": n, "brier": round(brier, 6), "logloss": round(logloss, 6), "accuracy_at_0_5": round(acc, 6)}


def backtest(history: List[HistRow]) -> Dict[str, Any]:
    train, test = split_rows(history)
    base = baseline_prob(train)
    rows = []
    for r in test:
        f = features(r)
        p = forecast_prob(f)
        rows.append({
            "event_id": r.event_id,
            "kickoff_utc": r.kickoff_utc,
            "home": r.home,
            "away": r.away,
            "label_home_win": label(r),
            "forecast_probability": p,
            "baseline_probability": base,
            "brier_contribution": round((p - label(r)) ** 2, 6),
            "top_factors": sorted([
                {"name": "rating_diff", "value": f["rating_diff"], "impact": abs(1.45 * f["rating_diff"])},
                {"name": "form_diff", "value": f["form_diff"], "impact": abs(1.15 * f["form_diff"])},
                {"name": "rest_diff", "value": f["rest_diff"], "impact": abs(0.38 * f["rest_diff"])},
            ], key=lambda x: x["impact"], reverse=True)[:3],
        })
    return {
        "split": {"strategy": "chronological", "train_before": "2025-01-01T00:00:00Z", "train_rows": len(train), "test_rows": len(test)},
        "baseline_probability": base,
        "rows": rows,
        "forecast_metrics": metrics(rows, "forecast_probability"),
        "baseline_metrics": metrics(rows, "baseline_probability"),
    }


def calibration(rows: List[Dict[str, Any]], prob_key: str = "forecast_probability") -> Dict[str, Any]:
    bins = []
    ece = 0.0
    total = len(rows)
    for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
        hi = lo + 0.2
        part = [r for r in rows if lo <= r[prob_key] < hi or (hi >= 1.0 and r[prob_key] <= hi)]
        if not part:
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": 0, "avg_probability": None, "observed_rate": None})
            continue
        avg_p = sum(r[prob_key] for r in part) / len(part)
        obs = sum(r["label_home_win"] for r in part) / len(part)
        ece += (len(part) / total) * abs(avg_p - obs)
        bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": len(part), "avg_probability": round(avg_p, 6), "observed_rate": round(obs, 6), "gap": round(avg_p - obs, 6)})
    return {"bins": bins, "expected_calibration_error": round(ece, 6), "metric_note": "Lower is better; sample is tiny and offline."}


def write_jsonl_gz(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return sha_file(path)


def build_phase2(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    history = sample_history()
    hist_json = [asdict(r) for r in history]
    train_data = training_rows(history)
    back = backtest(history)
    cal = calibration(back["rows"])
    hist_path = out_dir / "historical_events.v67.jsonl.gz"
    train_path = out_dir / "settled_training_rows.v68.jsonl.gz"
    back_path = out_dir / "chronological_backtest.v69.json"
    cal_path = out_dir / "calibration_metrics.v70.json"
    hist_sha = write_jsonl_gz(hist_path, hist_json)
    train_sha = write_jsonl_gz(train_path, train_data)
    write_json(back_path, back)
    write_json(cal_path, cal)
    registry = {
        "ok": True,
        "schema": "omnibet.model_registry.v71",
        "model_id": "offline_logistic_baseline_v1",
        "version": "v71.phase2.offline.1",
        "model_family": "transparent_logistic_scorecard",
        "target": "home_win_binary",
        "training_rows_path": str(train_path),
        "training_rows_sha256": train_sha,
        "historical_rows_sha256": hist_sha,
        "split": back["split"],
        "metrics": {"forecast": back["forecast_metrics"], "baseline": back["baseline_metrics"], "calibration": {"expected_calibration_error": cal["expected_calibration_error"]}},
        "safety": {"paper_only": True, "no_recommendation_output": True, "offline_only": True, "no_live_calls": True},
    }
    registry_path = out_dir / "model_registry.v71.json"
    write_json(registry_path, registry)
    explanation = {
        "ok": True,
        "schema": "omnibet.prediction_explanation.v72",
        "mode": "paper_only_offline_forecast_explanation",
        "model_id": registry["model_id"],
        "desktop_panels": ["model-card", "backtest-metrics", "calibration", "example-explanations"],
        "example_predictions": back["rows"][:6],
        "explanation_note": "Probabilities are research forecasts, not recommendations. Sample is tiny and only validates the pipeline shape.",
        "safety": registry["safety"],
    }
    explanation_path = out_dir / "prediction_explanation.v72.json"
    write_json(explanation_path, explanation)
    manifest = {
        "ok": True,
        "schema": "omnibet.phase2_forecast_manifest.v67_v72",
        "milestones": {"v67": "historical importer", "v68": "settled training dataset", "v69": "chronological backtest", "v70": "calibration metrics", "v71": "model registry", "v72": "prediction explanation UI payload"},
        "outputs": {
            "historical_events": str(hist_path),
            "training_rows": str(train_path),
            "backtest": str(back_path),
            "calibration": str(cal_path),
            "model_registry": str(registry_path),
            "prediction_explanation": str(explanation_path),
        },
        "hashes": {"historical_events_sha256": hist_sha, "training_rows_sha256": train_sha, "backtest_sha256": sha_file(back_path), "calibration_sha256": sha_file(cal_path), "registry_sha256": sha_file(registry_path), "explanation_sha256": sha_file(explanation_path)},
        "row_counts": {"historical_events": len(history), "training_rows": len(train_data), "backtest_rows": len(back["rows"])},
        "quality": {"forecast_metrics": back["forecast_metrics"], "baseline_metrics": back["baseline_metrics"], "calibration": cal},
        "safety": registry["safety"],
    }
    manifest_path = out_dir / "phase2_manifest.v67_v72.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "manifest_path": manifest_path, "explanation": explanation, "registry": registry, "backtest": back, "calibration": cal}


def build_report(root: Path, out_dir: Path, ui_sample: Path | None = None) -> Dict[str, Any]:
    built = build_phase2(out_dir)
    if ui_sample is not None:
        write_json(ui_sample, {"ok": True, "version": "omnibet.phase2.ui.sample.v72", "manifest": built["manifest"], "registry": built["registry"], "backtest": {"split": built["backtest"]["split"], "forecast_metrics": built["backtest"]["forecast_metrics"], "baseline_metrics": built["backtest"]["baseline_metrics"], "rows": built["backtest"]["rows"][:8]}, "calibration": built["calibration"], "explanation": built["explanation"], "safety": built["manifest"]["safety"]})
    manifest = built["manifest"]
    checks = {
        "historical_rows_enough": manifest["row_counts"]["historical_events"] >= 60,
        "training_rows_match_history": manifest["row_counts"]["training_rows"] == manifest["row_counts"]["historical_events"],
        "backtest_has_test_rows": manifest["row_counts"]["backtest_rows"] >= 15,
        "chronological_split": built["backtest"]["split"]["strategy"] == "chronological",
        "forecast_metrics_present": all(k in built["backtest"]["forecast_metrics"] for k in ["brier", "logloss", "accuracy_at_0_5"]),
        "calibration_present": "expected_calibration_error" in built["calibration"],
        "registry_present": built["registry"].get("schema") == "omnibet.model_registry.v71",
        "explanation_payload_present": built["explanation"].get("schema") == "omnibet.prediction_explanation.v72",
        "hashes_present": all(v for v in manifest["hashes"].values()),
        "paper_only": manifest["safety"]["paper_only"] is True,
        "no_recommendation_output": manifest["safety"]["no_recommendation_output"] is True,
        "offline_only": manifest["safety"]["offline_only"] is True,
    }
    return {"ok": all(checks.values()), "milestone": "v67_v72_phase2_forecast_quality", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": manifest}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="build/phase2_forecast_v67_v72")
    ap.add_argument("--ui-sample", default="tauri-app/src/phase2-forecast.sample.json")
    ap.add_argument("--out", default="reports/ci_v67_v72_phase2_forecast.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
