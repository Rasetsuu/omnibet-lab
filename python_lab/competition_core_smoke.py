#!/usr/bin/env python3
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Dict, Iterable, List

COMPS = [
    {"competition_id": "eng_premier", "name": "England Premier", "country": "England", "tier": 1, "home_edge": 0.20, "goal_rate": 2.78},
    {"competition_id": "esp_laliga", "name": "Spain LaLiga", "country": "Spain", "tier": 1, "home_edge": 0.16, "goal_rate": 2.52},
    {"competition_id": "ita_serie_a", "name": "Italy Serie A", "country": "Italy", "tier": 1, "home_edge": 0.14, "goal_rate": 2.44},
    {"competition_id": "ger_bundesliga", "name": "Germany Bundesliga", "country": "Germany", "tier": 1, "home_edge": 0.18, "goal_rate": 3.04},
    {"competition_id": "fra_ligue1", "name": "France Ligue 1", "country": "France", "tier": 1, "home_edge": 0.15, "goal_rate": 2.50},
    {"competition_id": "int_world", "name": "International Senior", "country": "International", "tier": 0, "home_edge": 0.10, "goal_rate": 2.36},
]
MODELS = ["global_baseline", "global_scorecard", "competition_prior_scorecard", "competition_tuned_scorecard"]
TEAM_RATINGS = [1840, 1800, 1760, 1720, 1680, 1640, 1600, 1560]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl_gz(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(path, "wt", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return sha_file(path)


def clamp(p: float) -> float:
    return max(0.02, min(0.98, p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 20), -20)))


def label(row: Dict[str, Any]) -> int:
    return int(row["home_goals"] > row["away_goals"])


def make_history() -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    idx = 0
    for comp in COMPS:
        for season in range(2015, 2027):
            for round_no in range(18):
                h = (round_no + season + idx) % 8
                a = (round_no * 3 + season + 2) % 8
                if h == a:
                    a = (a + 1) % 8
                home_rating = TEAM_RATINGS[h] + (season - 2015) * ((h % 3) - 1) * 3
                away_rating = TEAM_RATINGS[a] + (season - 2015) * ((a % 3) - 1) * 3
                rating_diff = (home_rating - away_rating) / 400.0
                form_diff = (0.45 + (h % 5) * 0.065) - (0.45 + (a % 5) * 0.065)
                rest_diff = (((round_no + h) % 5) - ((round_no + a + 1) % 5)) / 7.0
                signal = -0.14 + 1.15 * rating_diff + 0.86 * form_diff + 0.35 * rest_diff + comp["home_edge"]
                signal += (((idx * 7 + season) % 9) - 4) * 0.04
                if signal > 0.62:
                    hg, ag = 3, 1
                elif signal > 0.30:
                    hg, ag = 2, 1
                elif signal > 0.05:
                    hg, ag = 1, 1
                elif signal > -0.22:
                    hg, ag = 1, 2
                else:
                    hg, ag = 0, 2
                rows.append({"event_id": f"comp:{comp['competition_id']}:{season}:{round_no:02d}", "competition_id": comp["competition_id"], "season": season, "round_no": round_no, "kickoff_utc": f"{season}-{(round_no % 12) + 1:02d}-{(round_no * 2 % 26) + 1:02d}T18:00:00Z", "home": f"{comp['country'][:3]} Team {h}", "away": f"{comp['country'][:3]} Team {a}", "rating_diff": rating_diff, "form_diff": form_diff, "rest_diff": rest_diff, "home_edge": comp["home_edge"], "goal_rate": comp["goal_rate"], "home_goals": hg, "away_goals": ag})
                idx += 1
    return sorted(rows, key=lambda r: (r["kickoff_utc"], r["event_id"]))


def base_rate(rows: List[Dict[str, Any]], comp: str | None = None) -> float:
    part = [r for r in rows if comp is None or r["competition_id"] == comp]
    if not part:
        part = rows
    return clamp(sum(label(r) for r in part) / len(part))


def predict(model: str, row: Dict[str, Any], train: List[Dict[str, Any]]) -> float:
    global_base = base_rate(train)
    comp_base = base_rate(train, row["competition_id"])
    if model == "global_baseline":
        return global_base
    if model == "global_scorecard":
        return clamp(sigmoid(-0.06 + 1.18 * row["rating_diff"] + 0.78 * row["form_diff"] + 0.18 * row["rest_diff"] + 0.14))
    if model == "competition_prior_scorecard":
        return clamp(sigmoid(math.log(comp_base / (1 - comp_base)) + 0.92 * row["rating_diff"] + 0.62 * row["form_diff"]))
    return clamp(sigmoid(math.log(comp_base / (1 - comp_base)) + 1.08 * row["rating_diff"] + 0.76 * row["form_diff"] + 0.22 * row["rest_diff"] + (row["home_edge"] - 0.15) * 0.7))


def logloss(y: int, p: float) -> float:
    p = clamp(p)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def metrics(preds: List[Dict[str, Any]]) -> Dict[str, float]:
    n = len(preds)
    return {"rows": n, "brier": round(sum((p["probability"] - p["label_home_win"]) ** 2 for p in preds) / n, 6), "logloss": round(sum(logloss(int(p["label_home_win"]), float(p["probability"])) for p in preds) / n, 6), "accuracy_at_0_5": round(sum((p["probability"] >= 0.5) == bool(p["label_home_win"]) for p in preds) / n, 6)}


def calibration(preds: List[Dict[str, Any]]) -> Dict[str, Any]:
    bins = []
    ece = 0.0
    for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
        hi = lo + 0.2
        part = [p for p in preds if lo <= p["probability"] < hi or (hi >= 1.0 and p["probability"] <= hi)]
        if not part:
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": 0})
            continue
        avg_p = sum(p["probability"] for p in part) / len(part)
        obs = sum(p["label_home_win"] for p in part) / len(part)
        ece += (len(part) / len(preds)) * abs(avg_p - obs)
        bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": len(part), "avg_probability": round(avg_p, 6), "observed_rate": round(obs, 6), "gap": round(avg_p - obs, 6)})
    return {"expected_calibration_error": round(ece, 6), "bins": bins}


def evaluate(history: List[Dict[str, Any]]) -> Dict[str, Any]:
    folds = []
    preds = []
    for season in range(2019, 2027):
        train = [r for r in history if r["season"] < season]
        test = [r for r in history if r["season"] == season]
        for comp in [c["competition_id"] for c in COMPS]:
            comp_test = [r for r in test if r["competition_id"] == comp]
            for model in MODELS:
                fp = []
                for row in comp_test:
                    p = {"event_id": row["event_id"], "season": season, "competition_id": comp, "model_id": model, "home": row["home"], "away": row["away"], "label_home_win": label(row), "probability": predict(model, row, train), "top_factors": [{"name": "competition", "value": comp, "impact": row["home_edge"]}, {"name": "rating_diff", "value": round(row["rating_diff"], 6), "impact": abs(round(row["rating_diff"], 6))}]}
                    fp.append(p)
                    preds.append(p)
                folds.append({"season": season, "competition_id": comp, "model_id": model, "train_rows": len(train), "test_rows": len(comp_test), "metrics": metrics(fp)})
    return {"folds": folds, "predictions": preds}


def aggregate(eval_report: Dict[str, Any]) -> Dict[str, Any]:
    model_rows = []
    comp_rows = []
    for model in MODELS:
        mp = [p for p in eval_report["predictions"] if p["model_id"] == model]
        model_rows.append({"model_id": model, **metrics(mp), "calibration_ece": calibration(mp)["expected_calibration_error"]})
        for comp in [c["competition_id"] for c in COMPS]:
            cp = [p for p in mp if p["competition_id"] == comp]
            comp_rows.append({"competition_id": comp, "model_id": model, **metrics(cp), "calibration_ece": calibration(cp)["expected_calibration_error"]})
    model_rows.sort(key=lambda r: (r["brier"], r["logloss"], r["calibration_ece"]))
    return {"models": model_rows, "per_competition": comp_rows, "best_model": model_rows[0]["model_id"]}


def source_matrix() -> Dict[str, Any]:
    ids = [f"source_{i:02d}" for i in range(1, 16)]
    return {"schema": "omnibet.source_coverage.v83", "rows": [{"source_id": x, "status": "planned_or_reference", "manual_or_permitted_only": True} for x in ids], "ci_policy": {"external_calls": False, "website_automation": False}}


def adapter_contracts() -> Dict[str, Any]:
    return {"schema": "omnibet.adapter_contracts.v84", "historical_result_fields": ["source_id", "competition_id", "season", "kickoff_utc", "home_name", "away_name", "home_score", "away_score", "source_event_id", "payload_sha256"], "market_snapshot_fields": ["source_id", "competition_id", "source_event_id", "snapshot_time_utc", "market_name", "selection_name", "decimal_odds", "payload_sha256"], "rules": ["competition_id required", "source_event_id required", "payload hash required", "pre-event feature cutoff required"]}


def build(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    history = make_history()
    training = [{**r, "label_home_win": label(r), "model_eligible": 1, "leakage_guard": "pre_event_features_only"} for r in history]
    eval_report = evaluate(history)
    agg = aggregate(eval_report)
    best = agg["best_model"]
    best_preds = [p for p in eval_report["predictions"] if p["model_id"] == best]
    per_comp_cal = [{"competition_id": c["competition_id"], **calibration([p for p in best_preds if p["competition_id"] == c["competition_id"]])} for c in COMPS]
    registry = {"schema": "omnibet.competition_registry.v79", "competitions": [{**c, "historical_rows": len([r for r in history if r["competition_id"] == c["competition_id"]]), "train_separately": True, "calibrate_separately": True} for c in COMPS]}
    model_lab = {"ok": True, "schema": "omnibet.competition_model_lab.v86", "best_model": best, "model_comparison": agg["models"], "per_competition_eval": agg["per_competition"], "per_competition_calibration": per_comp_cal, "source_coverage": source_matrix()["rows"], "adapter_contracts": adapter_contracts(), "example_predictions": best_preds[:12], "rust_migration": {"eval_core_skeleton": "rust-core/src/competition_eval.rs", "report_reader_skeleton": "rust-core/src/competition_report.rs"}, "safety": {"paper_only": True, "offline_only": True, "no_recommendation_output": True, "no_external_calls": True}}
    paths = {"registry": out_dir / "competition_registry.v79.json", "history": out_dir / "competition_history.v80.jsonl.gz", "training": out_dir / "competition_training.v80.jsonl.gz", "eval": out_dir / "per_competition_eval.v82.json", "source_matrix": out_dir / "source_coverage_matrix.v83.json", "adapter_contracts": out_dir / "adapter_contracts.v84.json", "model_lab": out_dir / "competition_model_lab.v86.json"}
    write_json(paths["registry"], registry)
    hist_sha = write_jsonl_gz(paths["history"], history)
    train_sha = write_jsonl_gz(paths["training"], training)
    write_json(paths["eval"], {"schema": "omnibet.per_competition_eval.v82", **agg})
    write_json(paths["source_matrix"], source_matrix())
    write_json(paths["adapter_contracts"], adapter_contracts())
    write_json(paths["model_lab"], model_lab)
    hashes = {f"{k}_sha256": sha_file(v) for k, v in paths.items()}
    hashes["history_sha256"] = hist_sha
    hashes["training_sha256"] = train_sha
    manifest = {"ok": True, "schema": "omnibet.competition_phase_manifest.v79_v86", "outputs": {k: str(v) for k, v in paths.items()}, "hashes": hashes, "row_counts": {"competitions": len(COMPS), "history": len(history), "training": len(training), "eval_predictions": len(eval_report["predictions"]), "source_coverage_rows": len(source_matrix()["rows"])}, "best_model": best, "safety": model_lab["safety"]}
    manifest_path = out_dir / "competition_phase_manifest.v79_v86.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "model_lab": model_lab, "manifest_path": manifest_path}


def build_report(root: Path, out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    built = build(out_dir)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.competition_lab.sample.v86", "manifest": built["manifest"], "competition_lab": built["model_lab"], "model_lab": {"ok": True, "schema": "omnibet.model_lab_payload.v78", "best_model": built["model_lab"]["best_model"], "models": built["model_lab"]["model_comparison"], "ablation": [], "stability": {}, "example_predictions": built["model_lab"]["example_predictions"], "safety": built["model_lab"]["safety"]}, "safety": built["model_lab"]["safety"]})
    manifest = built["manifest"]
    eval_rs = root / "rust-core/src/competition_eval.rs"
    report_rs = root / "rust-core/src/competition_report.rs"
    checks = {"competition_registry_rows": manifest["row_counts"]["competitions"] >= 6, "history_rows_scaled": manifest["row_counts"]["history"] >= 1000, "training_matches_history": manifest["row_counts"]["training"] == manifest["row_counts"]["history"], "eval_predictions_present": manifest["row_counts"]["eval_predictions"] >= 500, "source_matrix_broad": manifest["row_counts"]["source_coverage_rows"] >= 12, "best_model_present": bool(manifest["best_model"]), "ui_sample_written": ui_sample is not None and ui_sample.exists(), "rust_eval_skeleton_exists": eval_rs.exists() and "LeagueCalibrationBin" in eval_rs.read_text(encoding="utf-8"), "rust_report_skeleton_exists": report_rs.exists() and "CompetitionReportManifest" in report_rs.read_text(encoding="utf-8"), "paper_only": manifest["safety"]["paper_only"] is True, "offline_only": manifest["safety"]["offline_only"] is True, "no_recommendation_output": manifest["safety"]["no_recommendation_output"] is True}
    return {"ok": all(checks.values()), "milestone": "v79_v86_competition_core", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": manifest}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="build/competition_phase_v79_v86")
    ap.add_argument("--ui-sample", default="tauri-app/src/competition-lab.sample.json")
    ap.add_argument("--out", default="reports/ci_v79_v86_competition_core.json")
    args = ap.parse_args()
    report = build_report(Path(args.root), Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
