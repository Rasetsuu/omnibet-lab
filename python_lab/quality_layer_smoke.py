#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Dict, Iterable, List

COMPS = [
    ("eng_premier", "domestic"), ("esp_laliga", "domestic"), ("ita_serie_a", "domestic"), ("ger_bundesliga", "domestic"),
    ("fra_ligue1", "domestic"), ("por_primeira", "domestic"), ("ned_eredivisie", "domestic"), ("usa_mls", "domestic"),
    ("bra_serie_a", "domestic"), ("arg_primera", "domestic"), ("mex_liga_mx", "domestic"), ("jpn_j1", "domestic"),
    ("uefa_champions", "continental"), ("uefa_europa", "continental"),
]


def write_json(path: Path, obj: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    return sha_file(path)


def clamp(p: float) -> float:
    return max(0.02, min(0.98, p))


def sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(min(x, 20), -20)))


def generate_matches() -> List[Dict[str, Any]]:
    rows = []
    event_i = 0
    for comp_i, (comp, kind) in enumerate(COMPS):
        for season in range(2016, 2027):
            team_count = 10 if kind == "domestic" else 16
            for round_no in range(20 if kind == "domestic" else 14):
                h = (round_no + season + comp_i) % team_count
                a = (round_no * 3 + season + comp_i + 4) % team_count
                if h == a:
                    a = (a + 1) % team_count
                promoted_home = int(kind == "domestic" and season > 2016 and h in {(season + comp_i) % team_count, (season + comp_i + 3) % team_count})
                promoted_away = int(kind == "domestic" and season > 2016 and a in {(season + comp_i) % team_count, (season + comp_i + 3) % team_count})
                rating_signal = ((h - a) / max(team_count, 1)) + (comp_i % 5 - 2) * 0.04
                status_penalty = -0.10 * promoted_home + 0.08 * promoted_away
                kind_adjust = 0.05 if kind == "continental" else 0.0
                noise = (((event_i * 7 + season) % 11) - 5) * 0.035
                signal = -0.04 + rating_signal + status_penalty + kind_adjust + noise
                if signal > 0.55:
                    hg, ag = 3, 1
                elif signal > 0.22:
                    hg, ag = 2, 1
                elif signal > -0.08:
                    hg, ag = 1, 1
                elif signal > -0.35:
                    hg, ag = 1, 2
                else:
                    hg, ag = 0, 2
                rows.append({
                    "event_id": f"q:{comp}:{season}:{round_no:03d}",
                    "competition_id": comp,
                    "competition_kind": kind,
                    "season": season,
                    "round_no": round_no,
                    "kickoff_index": season * 1000 + round_no,
                    "home_team_id": f"{comp}_team_{h}",
                    "away_team_id": f"{comp}_team_{a}",
                    "promoted_home": promoted_home,
                    "promoted_away": promoted_away,
                    "home_goals": hg,
                    "away_goals": ag,
                })
                event_i += 1
    return sorted(rows, key=lambda r: (r["kickoff_index"], r["competition_id"], r["event_id"]))


def build_features(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    ratings: Dict[tuple[str, str], float] = defaultdict(lambda: 1500.0)
    form: Dict[tuple[str, str], deque[int]] = defaultdict(lambda: deque(maxlen=5))
    home_hist: Dict[tuple[str, str], deque[int]] = defaultdict(lambda: deque(maxlen=8))
    away_hist: Dict[tuple[str, str], deque[int]] = defaultdict(lambda: deque(maxlen=8))
    last_played: Dict[tuple[str, str], int] = {}
    out = []
    for row in rows:
        comp = row["competition_id"]
        h_key = (comp, row["home_team_id"])
        a_key = (comp, row["away_team_id"])
        h_rating = ratings[h_key]
        a_rating = ratings[a_key]
        h_form = sum(form[h_key]) / len(form[h_key]) if form[h_key] else 0.5
        a_form = sum(form[a_key]) / len(form[a_key]) if form[a_key] else 0.5
        h_home = sum(home_hist[h_key]) / len(home_hist[h_key]) if home_hist[h_key] else 0.5
        a_away = sum(away_hist[a_key]) / len(away_hist[a_key]) if away_hist[a_key] else 0.5
        h_rest = row["kickoff_index"] - last_played.get(h_key, row["kickoff_index"] - 7)
        a_rest = row["kickoff_index"] - last_played.get(a_key, row["kickoff_index"] - 7)
        h_congestion = int(h_rest <= 3)
        a_congestion = int(a_rest <= 3)
        label_home = int(row["home_goals"] > row["away_goals"])
        label_away = int(row["away_goals"] > row["home_goals"])
        label_draw = int(row["home_goals"] == row["away_goals"])
        feat = {
            **row,
            "rating_diff_pre": round((h_rating - a_rating) / 400.0, 6),
            "form_diff_pre": round(h_form - a_form, 6),
            "home_away_strength_diff_pre": round(h_home - a_away, 6),
            "rest_diff_pre": round((h_rest - a_rest) / 7.0, 6),
            "congestion_diff_pre": a_congestion - h_congestion,
            "promotion_status_diff": row["promoted_away"] - row["promoted_home"],
            "kind_continental": int(row["competition_kind"] == "continental"),
            "label_home_win": label_home,
            "label_draw": label_draw,
            "label_away_win": label_away,
            "feature_cutoff": "pre_event_only",
        }
        out.append(feat)
        actual = 1.0 if label_home else 0.0 if label_away else 0.5
        expected = 1.0 / (1.0 + 10 ** ((a_rating - h_rating) / 400.0))
        k = 18.0 if row["competition_kind"] == "domestic" else 14.0
        ratings[h_key] = h_rating + k * (actual - expected)
        ratings[a_key] = a_rating + k * ((1.0 - actual) - (1.0 - expected))
        form[h_key].append(1 if label_home else 0 if label_away else 0)
        form[a_key].append(1 if label_away else 0 if label_home else 0)
        home_hist[h_key].append(1 if label_home else 0)
        away_hist[a_key].append(1 if label_away else 0)
        last_played[h_key] = row["kickoff_index"]
        last_played[a_key] = row["kickoff_index"]
    return out


def predict(row: Dict[str, Any], train: List[Dict[str, Any]]) -> float:
    comp_train = [r for r in train if r["competition_id"] == row["competition_id"]]
    base = sum(r["label_home_win"] for r in comp_train) / len(comp_train) if comp_train else sum(r["label_home_win"] for r in train) / len(train)
    z = math.log(clamp(base) / (1 - clamp(base)))
    z += 0.95 * row["rating_diff_pre"]
    z += 0.62 * row["form_diff_pre"]
    z += 0.35 * row["home_away_strength_diff_pre"]
    z += 0.18 * row["rest_diff_pre"]
    z += 0.12 * row["congestion_diff_pre"]
    z += 0.20 * row["promotion_status_diff"]
    z += 0.08 * row["kind_continental"]
    return clamp(sigmoid(z))


def evaluate(features: List[Dict[str, Any]]) -> Dict[str, Any]:
    preds = []
    for test_season in range(2023, 2027):
        train = [r for r in features if r["season"] < test_season]
        test = [r for r in features if r["season"] == test_season]
        for row in test:
            p = predict(row, train)
            preds.append({"event_id": row["event_id"], "competition_id": row["competition_id"], "season": row["season"], "probability": p, "label_home_win": row["label_home_win"]})
    per_comp = []
    cal = []
    for comp in sorted({p["competition_id"] for p in preds}):
        part = [p for p in preds if p["competition_id"] == comp]
        brier = sum((p["probability"] - p["label_home_win"]) ** 2 for p in part) / len(part)
        acc = sum((p["probability"] >= 0.5) == bool(p["label_home_win"]) for p in part) / len(part)
        per_comp.append({"competition_id": comp, "rows": len(part), "brier": round(brier, 6), "accuracy_at_0_5": round(acc, 6)})
        for lo in [0.0, 0.25, 0.5, 0.75]:
            hi = lo + 0.25
            b = [p for p in part if lo <= p["probability"] < hi or (hi >= 1.0 and p["probability"] <= hi)]
            if not b:
                continue
            avg_p = sum(p["probability"] for p in b) / len(b)
            obs = sum(p["label_home_win"] for p in b) / len(b)
            margin = 1.96 * math.sqrt(max(obs * (1 - obs), 0.0001) / len(b))
            cal.append({"competition_id": comp, "bin": f"{lo:.2f}-{hi:.2f}", "rows": len(b), "avg_probability": round(avg_p, 6), "observed_rate": round(obs, 6), "lower_95": round(max(0.0, obs - margin), 6), "upper_95": round(min(1.0, obs + margin), 6)})
    return {"schema": "omnibet.quality_eval.v109_v110", "predictions": preds, "per_competition": per_comp, "calibration": cal}


def build(out_dir: Path) -> Dict[str, Any]:
    out_dir.mkdir(parents=True, exist_ok=True)
    matches = generate_matches()
    features = build_features(matches)
    eval_report = evaluate(features)
    feature_keys = ["rating_diff_pre", "form_diff_pre", "home_away_strength_diff_pre", "rest_diff_pre", "congestion_diff_pre", "promotion_status_diff", "kind_continental"]
    paths = {
        "matches": out_dir / "quality_matches.v103.jsonl",
        "features": out_dir / "quality_features.v103_v108.jsonl",
        "evaluation": out_dir / "quality_eval.v109_v110.json",
        "desktop": out_dir / "quality_payload.v110.json",
    }
    match_sha = write_jsonl(paths["matches"], matches)
    feature_sha = write_jsonl(paths["features"], features)
    write_json(paths["evaluation"], eval_report)
    desktop = {"ok": True, "schema": "omnibet.quality_payload.v110", "feature_keys": feature_keys, "feature_rows": len(features), "competitions": sorted({r["competition_id"] for r in features}), "evaluation_rows": len(eval_report["predictions"]), "per_competition_eval": eval_report["per_competition"], "calibration": eval_report["calibration"][:40], "policy": {"offline_only": True, "pre_event_features_only": True}}
    write_json(paths["desktop"], desktop)
    hashes = {f"{k}_sha256": sha_file(v) for k, v in paths.items()}
    hashes.update({"matches_sha256": match_sha, "features_sha256": feature_sha})
    manifest = {"ok": True, "schema": "omnibet.quality_manifest.v103_v110", "outputs": {k: str(v) for k, v in paths.items()}, "hashes": hashes, "row_counts": {"matches": len(matches), "features": len(features), "evaluation_rows": len(eval_report["predictions"]), "competitions": len(desktop["competitions"]), "calibration_rows": len(eval_report["calibration"])}, "feature_keys": feature_keys, "policy": desktop["policy"]}
    manifest_path = out_dir / "quality_manifest.v103_v110.json"
    write_json(manifest_path, manifest)
    return {"manifest": manifest, "manifest_path": manifest_path, "desktop": desktop}


def build_report(out_dir: Path, ui_sample: Path | None) -> Dict[str, Any]:
    built = build(out_dir)
    if ui_sample:
        write_json(ui_sample, {"ok": True, "version": "omnibet.quality.sample.v110", "manifest": built["manifest"], "quality_layer": built["desktop"]})
    m = built["manifest"]
    required = {"rating_diff_pre", "form_diff_pre", "home_away_strength_diff_pre", "rest_diff_pre", "congestion_diff_pre", "promotion_status_diff", "kind_continental"}
    checks = {"features_2000": m["row_counts"]["features"] >= 2000, "competitions_12": m["row_counts"]["competitions"] >= 12, "evaluation_500": m["row_counts"]["evaluation_rows"] >= 500, "calibration_present": m["row_counts"]["calibration_rows"] >= 20, "required_features": required.issubset(set(m["feature_keys"])), "hashes_present": all(m["hashes"].values()), "ui_sample_written": ui_sample is not None and ui_sample.exists(), "pre_event_only": m["policy"]["pre_event_features_only"] is True}
    return {"ok": all(checks.values()), "milestone": "v103_v110_quality_layer", "manifest_path": str(built["manifest_path"]), "ui_sample_path": str(ui_sample) if ui_sample else None, "acceptance": checks, "manifest": m}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="build/quality_layer_v103_v110")
    ap.add_argument("--ui-sample", default="tauri-app/src/quality-layer.sample.json")
    ap.add_argument("--out", default="reports/ci_v103_v110_quality_layer.json")
    args = ap.parse_args()
    report = build_report(Path(args.out_dir), Path(args.ui_sample) if args.ui_sample else None)
    write_json(Path(args.out), report)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if not report["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
