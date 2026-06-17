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
class Competition:
    competition_id: str
    name: str
    country: str
    tier: int
    style: str
    base_home_edge: float
    base_goal_rate: float
    base_draw_rate: float


@dataclass(frozen=True)
class MatchRow:
    event_id: str
    kickoff_utc: str
    season: int
    round_no: int
    competition_id: str
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


COMPETITIONS = [
    Competition("eng_premier", "England Premier", "England", 1, "pace_transition", 0.20, 2.78, 0.24),
    Competition("esp_laliga", "Spain LaLiga", "Spain", 1, "possession_control", 0.16, 2.52, 0.28),
    Competition("ita_serie_a", "Italy Serie A", "Italy", 1, "tactical_balance", 0.14, 2.44, 0.30),
    Competition("ger_bundesliga", "Germany Bundesliga", "Germany", 1, "high_event", 0.18, 3.04, 0.22),
    Competition("fra_ligue1", "France Ligue 1", "France", 1, "physical_transition", 0.15, 2.50, 0.29),
    Competition("int_world", "International Senior", "International", 0, "national_team", 0.10, 2.36, 0.27),
]

BASE_TEAMS = [
    ("Alpha", 1840, 0.76), ("Bravo", 1800, 0.70), ("Cobalt", 1765, 0.65), ("Delta", 1735, 0.60),
    ("Eagle", 1700, 0.56), ("Falcon", 1665, 0.53), ("Granite", 1635, 0.50), ("Harbor", 1600, 0.47),
]

MODEL_IDS = ["global_baseline", "global_scorecard", "league_prior_scorecard", "league_tuned_scorecard"]


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


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 20), -20)))


def clamp_prob(p: float) -> float:
    return max(0.02, min(0.98, p))


def label(row: MatchRow) -> int:
    return int(row.home_goals > row.away_goals)


def competition_map() -> Dict[str, Competition]:
    return {c.competition_id: c for c in COMPETITIONS}


def features(row: MatchRow) -> Dict[str, float]:
    comp = competition_map()[row.competition_id]
    return {
        "rating_diff": (row.home_rating - row.away_rating) / 400.0,
        "form_diff": row.home_form - row.away_form,
        "rest_diff": (row.home_rest_days - row.away_rest_days) / 7.0,
        "home_edge": comp.base_home_edge,
        "goal_rate": comp.base_goal_rate / 3.0,
        "draw_rate": comp.base_draw_rate,
    }


def teams_for_comp(comp: Competition) -> List[Tuple[str, float, float]]:
    rows = []
    offset = sum(ord(ch) for ch in comp.competition_id) % 37
    for i, (name, rating, form) in enumerate(BASE_TEAMS):
        rows.append((f"{comp.country[:3]} {name}", rating + offset - i * 6, min(0.88, max(0.34, form + (offset % 7 - 3) * 0.01))))
    return rows


def generate_history() -> List[MatchRow]:
    rows: List[MatchRow] = []
    event_i = 0
    for comp in COMPETITIONS:
        teams = teams_for_comp(comp)
        for season in range(2018, 2027):
            season_drift = (season - 2018) * 4
            for round_no in range(20):
                h_idx = (round_no + season + event_i) % len(teams)
                a_idx = (round_no * 3 + season + 2) % len(teams)
                if h_idx == a_idx:
                    a_idx = (a_idx + 1) % len(teams)
                h = teams[h_idx]
                a = teams[a_idx]
                home_rating = h[1] + season_drift * ((h_idx % 3) - 1) + ((round_no % 5) - 2) * 4
                away_rating = a[1] + season_drift * ((a_idx % 3) - 1) + (((round_no + 1) % 5) - 2) * 4
                home_form = min(0.90, max(0.30, h[2] + ((round_no % 9) - 4) * 0.012))
                away_form = min(0.90, max(0.30, a[2] + (((round_no + 3) % 9) - 4) * 0.012))
                home_rest = 3 + ((season + round_no + h_idx) % 6)
                away_rest = 3 + ((season + round_no * 2 + a_idx) % 6)
                feat = {
                    "rating_diff": (home_rating - away_rating) / 400.0,
                    "form_diff": home_form - away_form,
                    "rest_diff": (home_rest - away_rest) / 7.0,
                }
                z = -0.18 + 1.25 * feat["rating_diff"] + 0.95 * feat["form_diff"] + 0.28 * feat["rest_diff"] + comp.base_home_edge
                jitter = (((event_i * 11 + season) % 13) - 6) * 0.045
                signal = z + jitter
                if signal > 0.70:
                    hg, ag = 2 + (event_i % 3), event_i % 2
                elif signal > 0.35:
                    hg, ag = 2, 1
                elif signal > comp.base_draw_rate - 0.34:
                    hg, ag = 1, 1
                elif signal > -0.22:
                    hg, ag = 1, 2
                else:
                    hg, ag = 0, 2 + (event_i % 2)
                rows.append(MatchRow(
                    event_id=f"league:{comp.competition_id}:{season}:{round_no:02d}",
                    kickoff_utc=f"{season}-{(round_no % 12) + 1:02d}-{(round_no * 2 % 26) + 1:02d}T18:00:00Z",
                    season=season,
                    round_no=round_no,
                    competition_id=comp.competition_id,
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
    return sorted(rows, key=lambda r: (r.kickoff_utc, r.event_id))


def base_rate(rows: List[MatchRow]) -> float:
    return clamp_prob(sum(label(r) for r in rows) / len(rows))


def predict(model_id: str, row: MatchRow, train_rows: List[MatchRow]) -> float:
    feat = features(row)
    global_base = base_rate(train_rows)
    league_train = [r for r in train_rows if r.competition_id == row.competition_id]
    league_base = base_rate(league_train) if league_train else global_base
    comp = competition_map()[row.competition_id]
    if model_id == "global_baseline":
        return global_base
    if model_id == "global_scorecard":
        z = -0.08 + 1.30 * feat["rating_diff"] + 0.92 * feat["form_diff"] + 0.22 * feat["rest_diff"] + 0.14
        return clamp_prob(sigmoid(z))
    if model_id == "league_prior_scorecard":
        z = math.log(league_base / (1 - league_base)) + 1.05 * feat["rating_diff"] + 0.74 * feat["form_diff"] + 0.18 * feat["rest_diff"]
        return clamp_prob(sigmoid(z))
    z = math.log(league_base / (1 - league_base)) + 1.18 * feat["rating_diff"] + 0.86 * feat["form_diff"] + 0.24 * feat["rest_diff"] + (comp.base_home_edge - 0.16) * 0.8
    return clamp_prob(sigmoid(z))


def safe_logloss(y: int, p: float) -> float:
    p = clamp_prob(p)
    return -(y * math.log(p) + (1 - y) * math.log(1 - p))


def metrics(rows: List[Dict[str, Any]]) -> Dict[str, float]:
    n = len(rows)
    brier = sum((r["probability"] - r["label_home_win"]) ** 2 for r in rows) / n
    ll = sum(safe_logloss(int(r["label_home_win"]), float(r["probability"])) for r in rows) / n
    acc = sum((r["probability"] >= 0.5) == bool(r["label_home_win"]) for r in rows) / n
    return {"rows": n, "brier": round(brier, 6), "logloss": round(ll, 6), "accuracy_at_0_5": round(acc, 6)}


def calibration(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    bins = []
    total = len(rows)
    ece = 0.0
    for lo in [0.0, 0.2, 0.4, 0.6, 0.8]:
        hi = lo + 0.2
        part = [r for r in rows if lo <= r["probability"] < hi or (hi >= 1.0 and r["probability"] <= hi)]
        if not part:
            bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": 0, "avg_probability": None, "observed_rate": None})
            continue
        avg_p = sum(r["probability"] for r in part) / len(part)
        obs = sum(r["label_home_win"] for r in part) / len(part)
        ece += (len(part) / total) * abs(avg_p - obs)
        bins.append({"bin": f"{lo:.1f}-{hi:.1f}", "rows": len(part), "avg_probability": round(avg_p, 6), "observed_rate": round(obs, 6), "gap": round(avg_p - obs, 6)})
    return {"expected_calibration_error": round(ece, 6), "bins": bins}


def evaluate(history: List[MatchRow]) -> Dict[str, Any]:
    folds = []
    all_predictions: List[Dict[str, Any]] = []
    for season in range(2021, 2027):
        train_rows = [r for r in history if r.season < season]
        test_rows = [r for r in history if r.season == season]
        for comp in COMPETITIONS:
            comp_test = [r for r in test_rows if r.competition_id == comp.competition_id]
            if not comp_test:
                continue
            for model_id in MODEL_IDS:
                preds = []
                for row in comp_test:
                    feat = features(row)
                    pred = {
                        "event_id": row.event_id,
                        "season": row.season,
                        "competition_id": row.competition_id,
                        "model_id": model_id,
                        "home": row.home,
                        "away": row.away,
                        "label_home_win": label(row),
                        "probability": predict(model_id, row, train_rows),
                        "top_factors": [
                            {"name": "competition", "value": row.competition_id, "impact": round(abs(feat["home_edge"]), 6)},
                            {"name": "rating_diff", "value": round(feat["rating_diff"], 6), "impact": round(abs(feat["rating_diff"]), 6)},
                            {"name": "form_diff", "value": round(feat["form_diff"], 6), "impact": round(abs(feat["form_diff"]), 6)},
                        ],
                    }
                    preds.append(pred)
                    all_predictions.append(pred)
                folds.append({
                    "season": season,
                    "competition_id": comp.competition_id,
                    "model_id": model_id,
                    "train_rows": len(train_rows),
                    "test_rows": len(comp_test),
                    "metrics": metrics(preds),
                })
    return {"folds": folds, "predictions": all_predictions}


def aggregate(eval_report: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    rows = []
    league_rows = []
    preds = eval_report["predictions"]
    for model_id in MODEL_IDS:
        part = [p for p in preds if p["model_id"] == model_id]
        rows.append({"model_id": model_id, **metrics(part), "calibration_ece": calibration(part)["expected_calibration_error"]})
        for comp in COMPETITIONS:
            cpart = [p for p in part if p["competition_id"] == comp.competition_id]
            league_rows.append({"competition_id": comp.competition_id, "model_id": model_id, **metrics(cpart), "calibration_ece": calibration(cpart)["expected_calibration_error"]})
    rows.sort(key=lambda r: (r["brier"], r["logloss"], r["calibration_ece"]))
    league_rows.sort(key=lambda r: (r["competition_id"], r["brier"]))
    return {"schema": "omnibet.model_comparison.v85", "models": rows, "best_model": rows[0]["model_id"]}, {"schema": "omnibet.per_competition_eval.v82", "rows": league_rows}


def registry_rows(history: List[MatchRow]) -> List[Dict[str, Any]]:
    counts = {c.competition_id: 0 for c in COMPETITIONS}
    for row in history:
        counts[row.competition_id] += 1
    return [{**asdict(c), "historical_rows": counts[c.competition_id], "train_separately": True, "calibrate_separately": True} for c in COMPETITIONS]


def source_matrix() -> Dict[str, Any]:
    rows = [
        ("openfootball", "results", "planned_adapter", "league fixtures/results"),
        ("football_data_csv", "results_and_market_columns", "planned_adapter", "CSV historical rows"),
        ("football_data_org", "fixtures_results", "planned_api", "official API style adapter"),
        ("statsbomb_open", "event_data", "planned_adapter", "open event data"),
        ("understat_style", "xg", "planned_adapter", "xG history"),
        ("api_football_style", "state_and_fixtures", "sample_shape_exists", "offline state sample exists"),
        ("the_odds_api_style", "market_snapshots", "sample_shape_exists", "offline market sample exists"),
        ("flashscore_reference", "scores_reference", "manual_or_allowed_snapshot_only", "reference layer, no automation in CI"),
        ("sofascore_reference", "stats_reference", "manual_or_allowed_snapshot_only", "reference layer"),
        ("superbet_reference", "market_reference", "manual_or_allowed_snapshot_only", "reference layer"),
        ("oddsportal_reference", "market_history_reference", "manual_or_allowed_snapshot_only", "reference layer"),
        ("betfair_exchange", "exchange_market_reference", "future_opt_in", "opt-in only"),
        ("pinnacle_reference", "sharp_market_reference", "future_opt_in", "opt-in only"),
        ("fbref_reference", "team_player_stats", "planned_adapter", "stats reference"),
        ("worldfootball_reference", "fixtures_results", "planned_adapter", "results reference"),
    ]
    return {"schema": "omnibet.source_coverage.v83", "rows": [{"source_id": a, "data_kind": b, "status": c, "note": d} for a, b, c, d in rows], "ci_policy": {"live_calls": False, "website_automation": False, "credential_values": False}}


def adapter_contracts() -> Dict[str, Any]:
    fields = ["source_id", "competition_id", "season", "kickoff_utc", "home_name", "away_name", "home_score", "away_score", "source_event_id", "source_payload_sha256"]
    market_fields = ["source_id", "competition_id", "source_event_id", "snapshot_time_utc", "market_name", "selection_name", "decimal_odds", "line_value", "payload_sha256"]
    return {"schema": "omnibet.adapter_contracts.v84", "historical_result_fields": fields, "market_snapshot_fields": market_fields, "rules": ["competition_id required", "source_event_id required", "payload sha required", "no final-state fields inside pre-event features"]}


def build_phase(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    history = generate_history()
    train = [{**asdict(r), **features(r), "label_home_win": label(r), "leakage_guard": "pre_event_features_only"} for r in history]
    eval_report = evaluate(history)
    comparison, per_comp = aggregate(eval_report)
    best_model = comparison["best_model"]
    best_preds = [p for p in eval_report["predictions"] if p["model_id"] == best_model]
    comp_cal = [{"competition_id": comp.competition_id, **calibration([p for p in best_preds if p["competition_id"] == comp.competition_id])} for comp in COMPETITIONS]
    outputs = {
        "registry": out_dir / "competition_registry.v79.json",
        "history": out_dir / "competition_history.v80.jsonl.gz",
        "training": out_dir / "competition_training.v80.jsonl.gz",
        "per_comp_eval": out_dir / "per_competition_eval.v82.json",
        "comparison": out_dir / "competition_model_comparison.v85.json",
        "calibration": out_dir / "per_competition_calibration.v81_v82.json",
        "source_matrix": out_dir / "source_coverage_matrix.v83.json",
        "adapter_contracts": out_dir / "adapter_contracts.v84.json",
        "model_lab": out_dir / "competition_model_lab.v86.json",
    }
    hashes = {}
    write_json(outputs["registry"], {"schema": "omnibet.competition_registry.v79", "competitions": registry_rows(history)})
    hashes["registry_sha256"] = sha_file(outputs["registry"])
    hashes["history_sha256"] = write_jsonl_gz(outputs["history"], [asdict(r) for r in history])
    hashes["training_sha256"] = write_jsonl_gz(outputs["training"], train)
    write_json(outputs["per_comp_eval"], per_comp)
    write_json(outputs["comparison"], comparison)
    write_json(outputs["calibration"], {"schema": "omnibet.per_competition_calibration.v81_v82", "rows": comp_cal})
    write_json(outputs["source_matrix"], source_matrix())
    write_json(outputs["adapter_contracts"], adapter_contracts())
    model_lab = {
        "ok": True,
        "schema": "omnibet.competition_model_lab.v86",
        "best_model": best_model,
        "competition_registry_rows": len(COMPETITIONS),
        "model_comparison": comparison["models"],
        "per_competition_eval": per_comp["rows"],
        "per_competition_calibration": comp_cal,
        "source_coverage": source_matrix()["rows"],
        "adapter_contracts": adapter_contracts(),
        "example_predictions": best_preds[:10],
        "rust_migration": {"eval_core_skeleton": "rust-core/src/competition_eval.rs", "manifest_reader_skeleton": "rust-core/src/model_lab_manifest.rs"},
        "safety": {"paper_only": True, "offline_only": True, "no_recommendation_output": True, "no_live_calls": True},
    }
    write_json(outputs["model_lab"], model_lab)
    for key, path in outputs.items():
        hashes.setdefault(f"{key}_sha256", sha_file(path))
    manifest = {
        "ok": True,
        "schema": "omnibet.competition_phase_manifest.v79_v86",
        "milestones": {"v79": "competition registry", "v80": "competition-aware historical import contract", "v81": "per-competition priors/calibration", "v82": "per-competition rolling evaluation", "v83": "source coverage matrix", "v84": "adapter contracts", "v85": "Rust eval/calibration skeleton", "v86": "Rust model-lab reader skeleton"},
        "outputs": {k: str(v) for k, v in outputs.items()},
        "hashes": hashes,
        "row_counts": {"competitions": len(COMPETITIONS), "history": len(history), "training": len(train), "eval_predictions": len(eval_report["predictions"]), "source_coverage_rows": len(source_matrix()["rows"])},
        "best_model": best_model,
        "safety": model_lab["safety"],
    }
    manifest_path = out_dir / "competition_phase_manifest.v79_v86.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "model_lab": model_lab, "manifest_path": manifest_path}


def build_report(out_dir: Path, ui_sample: Path | None, root: Path) -> Dict[str, Any]:
    built = build_phase(out_dir)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.competition_lab.sample.v86", "manifest": built["manifest"], "competition_lab": built["model_lab"], "model_lab": {"ok": True, "schema": "omnibet.model_lab_payload.v78", "best_model": built["model_lab"]["best_model"], "models": built["model_lab"]["model_comparison"], "ablation": [], "stability": {}, "example_predictions": built["model_lab"]["example_predictions"], "safety": built["model_lab"]["safety"]}, "safety": built["model_lab"]["safety"]})
    rust_eval = root / "rust-core/src/competition_eval.rs"
    rust_manifest = root / "rust-core/src/model_lab_manifest.rs"
    manifest = built["manifest"]
    checks = {
        "competition_registry_rows": manifest["row_counts"]["competitions"] >= 6,
        "history_rows_scaled": manifest["row_counts"]["history"] >= 1000,
        "training_matches_history": manifest["row_counts"]["training"] == manifest["row_counts"]["history"],
        "eval_predictions_present": manifest["row_counts"]["eval_predictions"] >= 500,
        "source_matrix_broad": manifest["row_counts"]["source_coverage_rows"] >= 12,
        "best_model_present": bool(manifest["best_model"]),
        "ui_sample_written": ui_sample is not None and ui_sample.exists(),
        "rust_eval_skeleton_exists": rust_eval.exists() and "LeagueCalibrationBin" in rust_eval.read_text(encoding="utf-8"),
        "rust_manifest_skeleton_exists": rust_manifest.exists() and "CompetitionModelLabManifest" in rust_manifest.read_text(encoding="utf-8"),
        "paper_only": manifest["safety"]["paper_only"] is True,
        "offline_only": manifest["safety"]["offline_only"] is True,
        "no_recommendation_output": manifest["safety"]["no_recommendation_output"] is True,
    }
    return {"ok": all(checks.values()), "milestone": "v79_v86_competition_phase", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": manifest}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--out-dir", default="build/competition_phase_v79_v86")
    ap.add_argument("--ui-sample", default="tauri-app/src/competition-lab.sample.json")
    ap.add_argument("--out", default="reports/ci_v79_v86_competition_phase.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None, Path(args.root))
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
