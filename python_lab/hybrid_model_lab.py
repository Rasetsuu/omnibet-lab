#!/usr/bin/env python3
"""
OmniBet Lab v3A hybrid model lab.

Purpose:
- Combine football statistical priors with rolling-form features.
- Add a lightweight calibration layer.
- Compare hybrid model vs rolling Poisson baseline in walk-forward mode.

This is still a proof-of-concept, but it is the first "AI layer" in the project:
Dixon/Poisson style score features + rolling feature store style features + rank priors
+ calibrated logistic models.

No bookmaker odds are required. Later v3B will add odds-input and bet-builder generation.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer


ALIASES = {
    "USA": "United States",
    "United States of America": "United States",
    "U.S.A.": "United States",
    "Czech Republic": "Czechia",
    "Turkey": "Turkiye",
    "Türkiye": "Turkiye",
    "Ivory Coast": "Côte d'Ivoire",
    "Cote d'Ivoire": "Côte d'Ivoire",
    "Curacao": "Curaçao",
    "DR Congo": "Congo DR",
    "South Korea": "Korea Republic",
    "Cape Verde Islands": "Cape Verde",
    "UAE": "United Arab Emirates",
}

# Lightweight ranking prior. Lower is stronger. Unknowns default to 70.
RANKS = {
    "Argentina": 1, "Spain": 2, "France": 3, "England": 4, "Portugal": 5,
    "Brazil": 6, "Uruguay": 7, "Netherlands": 9, "Belgium": 10, "Croatia": 11,
    "Morocco": 12, "United States": 13, "Colombia": 14, "Mexico": 15, "Germany": 16,
    "Switzerland": 17, "Japan": 18, "Senegal": 19, "Denmark": 20, "Iran": 21,
    "Serbia": 22, "Ecuador": 23, "Korea Republic": 24, "Hungary": 25, "Ukraine": 26,
    "Australia": 27, "Algeria": 28, "Tunisia": 29, "Norway": 30, "Scotland": 35,
    "Romania": 36, "Czechia": 37, "Austria": 41, "Côte d'Ivoire": 43, "Egypt": 44,
    "Panama": 47, "Saudi Arabia": 48, "Uzbekistan": 50, "Qatar": 51, "Iraq": 52,
    "South Africa": 53, "Jordan": 54, "Bosnia and Herzegovina": 55, "Cape Verde": 56,
    "Ghana": 57, "Curaçao": 58, "Haiti": 59, "New Zealand": 60, "Congo DR": 61,
    "Turkiye": 32,
}


def canonical(name: str) -> str:
    name = (name or "").strip()
    return ALIASES.get(name, name)


def safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        x = float(v)
        if math.isnan(x):
            return None
        return x
    except Exception:
        return None


def avg(values: List[Optional[float]], default: Optional[float] = None) -> Optional[float]:
    vals = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    if not vals:
        return default
    return sum(vals) / len(vals)


def points_for(gf: int, ga: int) -> int:
    if gf > ga:
        return 3
    if gf == ga:
        return 1
    return 0


def poisson_pmf(k: int, lam: float) -> float:
    lam = max(float(lam), 1e-8)
    out = math.exp(-lam)
    for i in range(k):
        out *= lam / (i + 1)
    return out


def score_matrix(lam_h: float, lam_a: float, max_goals: int = 8) -> np.ndarray:
    mat = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            mat[i, j] = poisson_pmf(i, lam_h) * poisson_pmf(j, lam_a)
    s = mat.sum()
    if s > 0:
        mat /= s
    return mat


def outcome_probs(mat: np.ndarray) -> Dict[str, float]:
    n = mat.shape[0]
    h = sum(mat[i, j] for i in range(n) for j in range(n) if i > j)
    d = sum(mat[i, i] for i in range(n))
    a = sum(mat[i, j] for i in range(n) for j in range(n) if i < j)
    return {"H": float(h), "D": float(d), "A": float(a)}


def over25_prob(mat: np.ndarray) -> float:
    n = mat.shape[0]
    return float(sum(mat[i, j] for i in range(n) for j in range(n) if i + j >= 3))


def btts_prob(mat: np.ndarray) -> float:
    return float(1.0 - mat[0, :].sum() - mat[:, 0].sum() + mat[0, 0])


def logloss(probs: Dict[str, float], actual: str) -> float:
    return -math.log(max(1e-12, probs[actual]))


def brier(probs: Dict[str, float], actual: str) -> float:
    return sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ["H", "D", "A"])


def binary_logloss(prob: float, actual: int) -> float:
    prob = min(max(prob, 1e-12), 1.0 - 1e-12)
    return -(actual * math.log(prob) + (1 - actual) * math.log(1 - prob))


def actual_outcome(hg: int, ag: int) -> str:
    if hg > ag:
        return "H"
    if hg < ag:
        return "A"
    return "D"


def load_data(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df = df.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"]).copy()
    df["date"] = pd.to_datetime(df["date"].astype(str).str[:10])
    df["home_team"] = df["home_team"].map(canonical)
    df["away_team"] = df["away_team"].map(canonical)
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    df = df.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)
    return df


def build_features(df: pd.DataFrame, rolling_n: int = 10) -> pd.DataFrame:
    """Build leakage-safe rolling features. Each row uses history before the match."""
    hist = defaultdict(lambda: deque(maxlen=200))
    total_goals = []
    rows = []

    global_avg = max(1.0, (df["home_goals"].sum() + df["away_goals"].sum()) / (2 * len(df)))

    for idx, r in df.iterrows():
        date = r["date"]
        h, a = r["home_team"], r["away_team"]
        hg, ag = int(r["home_goals"]), int(r["away_goals"])

        def snapshot(team: str) -> dict:
            xs = list(hist[team])[-rolling_n:]
            if not xs:
                return {
                    "games": 0, "gf": global_avg, "ga": global_avg, "shots_for": None, "shots_against": None,
                    "sot_for": None, "sot_against": None, "corners_for": None, "corners_against": None,
                    "fouls_for": None, "fouls_against": None, "form_points": 1.0, "rest_days": None,
                }
            return {
                "games": len(xs),
                "gf": avg([x["gf"] for x in xs], global_avg),
                "ga": avg([x["ga"] for x in xs], global_avg),
                "shots_for": avg([x.get("shots_for") for x in xs]),
                "shots_against": avg([x.get("shots_against") for x in xs]),
                "sot_for": avg([x.get("sot_for") for x in xs]),
                "sot_against": avg([x.get("sot_against") for x in xs]),
                "corners_for": avg([x.get("corners_for") for x in xs]),
                "corners_against": avg([x.get("corners_against") for x in xs]),
                "fouls_for": avg([x.get("fouls_for") for x in xs]),
                "fouls_against": avg([x.get("fouls_against") for x in xs]),
                "form_points": avg([x.get("points") for x in xs], 1.0),
                "rest_days": (date - xs[-1]["date"]).days if xs[-1].get("date") is not None else None,
            }

        hs, as_ = snapshot(h), snapshot(a)
        lam_h = max(0.15, (hs["gf"] + as_["ga"]) / 2.0)
        lam_a = max(0.15, (as_["gf"] + hs["ga"]) / 2.0)
        mat = score_matrix(lam_h, lam_a)
        p1x2 = outcome_probs(mat)

        rank_h = RANKS.get(h, 70)
        rank_a = RANKS.get(a, 70)

        row = {
            "idx": idx,
            "date": date,
            "league": r.get("league", ""),
            "home_team": h,
            "away_team": a,
            "home_goals": hg,
            "away_goals": ag,
            "outcome": actual_outcome(hg, ag),
            "over25": int(hg + ag >= 3),
            "btts": int(hg > 0 and ag > 0),
            "lambda_home_roll": lam_h,
            "lambda_away_roll": lam_a,
            "pois_home_prob": p1x2["H"],
            "pois_draw_prob": p1x2["D"],
            "pois_away_prob": p1x2["A"],
            "pois_over25_prob": over25_prob(mat),
            "pois_btts_prob": btts_prob(mat),
            "rank_home": rank_h,
            "rank_away": rank_a,
            "rank_diff": rank_a - rank_h,  # positive means home is stronger
            "games_home": hs["games"],
            "games_away": as_["games"],
            "gf_diff": hs["gf"] - as_["gf"],
            "ga_diff": hs["ga"] - as_["ga"],
            "shots_for_diff": (hs["shots_for"] if hs["shots_for"] is not None else np.nan) - (as_["shots_for"] if as_["shots_for"] is not None else np.nan),
            "shots_against_diff": (hs["shots_against"] if hs["shots_against"] is not None else np.nan) - (as_["shots_against"] if as_["shots_against"] is not None else np.nan),
            "sot_for_diff": (hs["sot_for"] if hs["sot_for"] is not None else np.nan) - (as_["sot_for"] if as_["sot_for"] is not None else np.nan),
            "corners_for_diff": (hs["corners_for"] if hs["corners_for"] is not None else np.nan) - (as_["corners_for"] if as_["corners_for"] is not None else np.nan),
            "corners_against_diff": (hs["corners_against"] if hs["corners_against"] is not None else np.nan) - (as_["corners_against"] if as_["corners_against"] is not None else np.nan),
            "fouls_for_diff": (hs["fouls_for"] if hs["fouls_for"] is not None else np.nan) - (as_["fouls_for"] if as_["fouls_for"] is not None else np.nan),
            "form_points_diff": hs["form_points"] - as_["form_points"],
            "rest_days_diff": (hs["rest_days"] if hs["rest_days"] is not None else np.nan) - (as_["rest_days"] if as_["rest_days"] is not None else np.nan),
        }
        rows.append(row)

        # Update histories after building features.
        hist[h].append({
            "date": date, "gf": hg, "ga": ag,
            "shots_for": safe_float(r.get("home_shots")), "shots_against": safe_float(r.get("away_shots")),
            "sot_for": safe_float(r.get("home_sot")), "sot_against": safe_float(r.get("away_sot")),
            "corners_for": safe_float(r.get("home_corners")), "corners_against": safe_float(r.get("away_corners")),
            "fouls_for": safe_float(r.get("home_fouls")), "fouls_against": safe_float(r.get("away_fouls")),
            "points": points_for(hg, ag),
        })
        hist[a].append({
            "date": date, "gf": ag, "ga": hg,
            "shots_for": safe_float(r.get("away_shots")), "shots_against": safe_float(r.get("home_shots")),
            "sot_for": safe_float(r.get("away_sot")), "sot_against": safe_float(r.get("home_sot")),
            "corners_for": safe_float(r.get("away_corners")), "corners_against": safe_float(r.get("home_corners")),
            "fouls_for": safe_float(r.get("away_fouls")), "fouls_against": safe_float(r.get("home_fouls")),
            "points": points_for(ag, hg),
        })

    return pd.DataFrame(rows)


FEATURE_COLS = [
    "lambda_home_roll", "lambda_away_roll",
    "pois_home_prob", "pois_draw_prob", "pois_away_prob", "pois_over25_prob", "pois_btts_prob",
    "rank_home", "rank_away", "rank_diff",
    "games_home", "games_away",
    "gf_diff", "ga_diff", "shots_for_diff", "shots_against_diff", "sot_for_diff",
    "corners_for_diff", "corners_against_diff", "fouls_for_diff",
    "form_points_diff", "rest_days_diff",
]


class ShrinkCalibrator:
    """Simple robust probability calibration: p'=(1-a)p+a*base_rate.

    This is not fancy, but it is stable on small sports datasets. It reduces
    fake confidence and is easy to port to Rust/C++ later.
    """
    def __init__(self, classes: List[str], alpha: float, prior: Dict[str, float]):
        self.classes = classes
        self.alpha = alpha
        self.prior = prior

    def apply(self, probs: Dict[str, float]) -> Dict[str, float]:
        out = {}
        for c in self.classes:
            out[c] = (1.0 - self.alpha) * probs.get(c, 0.0) + self.alpha * self.prior.get(c, 1.0 / len(self.classes))
        s = sum(out.values())
        return {k: v / s for k, v in out.items()} if s > 0 else out


def fit_multiclass_model(train: pd.DataFrame, feature_cols: List[str]):
    clf = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=700, class_weight="balanced", C=0.7)),
    ])
    clf.fit(train[feature_cols], train["outcome"])
    return clf


def fit_binary_model(train: pd.DataFrame, feature_cols: List[str], target: str):
    clf = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(max_iter=700, class_weight="balanced", C=0.7)),
    ])
    clf.fit(train[feature_cols], train[target])
    return clf


def prob_dict_from_model(model, x: pd.DataFrame, classes: List[str]) -> Dict[str, float]:
    probs = model.predict_proba(x)[0]
    model_classes = list(model.named_steps["model"].classes_)
    raw = {c: 0.0 for c in classes}
    for c, p in zip(model_classes, probs):
        raw[str(c)] = float(p)
    s = sum(raw.values())
    if s > 0:
        raw = {k: v / s for k, v in raw.items()}
    return raw


def choose_alpha_multiclass(train: pd.DataFrame, feature_cols: List[str], min_cal: int = 25) -> Tuple[float, Dict[str, float]]:
    classes = ["H", "D", "A"]
    prior = {c: float((train["outcome"] == c).mean()) for c in classes}
    if len(train) < min_cal * 2 or len(set(train["outcome"])) < 3:
        return 0.20, prior
    split = max(20, int(len(train) * 0.80))
    fit_part = train.iloc[:split]
    cal_part = train.iloc[split:]
    if len(cal_part) < min_cal or len(set(fit_part["outcome"])) < 3:
        return 0.20, prior
    model = fit_multiclass_model(fit_part, feature_cols)
    raw_list = [prob_dict_from_model(model, cal_part.iloc[[i]][feature_cols], classes) for i in range(len(cal_part))]
    alphas = [i / 20 for i in range(0, 11)]  # 0.00..0.50
    best_a, best_ll = 0.0, 1e99
    for a in alphas:
        cal = ShrinkCalibrator(classes, a, prior)
        ll = 0.0
        for probs, actual in zip(raw_list, cal_part["outcome"].tolist()):
            ll += logloss(cal.apply(probs), actual)
        ll /= len(cal_part)
        if ll < best_ll:
            best_ll, best_a = ll, a
    return best_a, prior


def choose_alpha_binary(train: pd.DataFrame, feature_cols: List[str], target: str, min_cal: int = 25) -> Tuple[float, float]:
    base = float(train[target].mean())
    if len(train) < min_cal * 2 or len(set(train[target])) < 2:
        return 0.20, base
    split = max(20, int(len(train) * 0.80))
    fit_part = train.iloc[:split]
    cal_part = train.iloc[split:]
    if len(cal_part) < min_cal or len(set(fit_part[target])) < 2:
        return 0.20, base
    model = fit_binary_model(fit_part, feature_cols, target)
    p_raw = model.predict_proba(cal_part[feature_cols])[:, list(model.named_steps["model"].classes_).index(1)]
    alphas = [i / 20 for i in range(0, 11)]
    best_a, best_ll = 0.0, 1e99
    for a in alphas:
        ps = (1.0 - a) * p_raw + a * base
        ll = sum(binary_logloss(float(p), int(y)) for p, y in zip(ps, cal_part[target])) / len(cal_part)
        if ll < best_ll:
            best_ll, best_a = ll, a
    return best_a, base


def metrics(rows: List[dict], prefix: str) -> dict:
    if not rows:
        return {}
    n = len(rows)
    return {
        f"{prefix}_matches": n,
        f"{prefix}_1x2_accuracy": sum(r[f"{prefix}_pick"] == r["actual"] for r in rows) / n,
        f"{prefix}_over25_accuracy": sum((r[f"{prefix}_over25_prob"] >= 0.5) == bool(r["actual_over25"]) for r in rows) / n,
        f"{prefix}_log_loss": sum(r[f"{prefix}_logloss"] for r in rows) / n,
        f"{prefix}_brier": sum(r[f"{prefix}_brier"] for r in rows) / n,
        f"{prefix}_over25_log_loss": sum(binary_logloss(r[f"{prefix}_over25_prob"], r["actual_over25"]) for r in rows) / n,
    }


def walk_forward(feat: pd.DataFrame, min_train: int = 90, refit_every: int = 25, calibrate: bool = True) -> dict:
    rows = []
    out_model = None
    over_model = None
    btts_model = None
    out_cal = None
    over_alpha, over_base = 0.2, 0.5
    btts_alpha, btts_base = 0.2, 0.5
    next_refit = min_train

    for i in range(min_train, len(feat)):
        if out_model is None or i >= next_refit:
            train = feat.iloc[:i].copy()
            out_model = fit_multiclass_model(train, FEATURE_COLS)
            over_model = fit_binary_model(train, FEATURE_COLS, "over25")
            btts_model = fit_binary_model(train, FEATURE_COLS, "btts")

            if calibrate:
                a, prior = choose_alpha_multiclass(train, FEATURE_COLS)
                out_cal = ShrinkCalibrator(["H", "D", "A"], a, prior)
                over_alpha, over_base = choose_alpha_binary(train, FEATURE_COLS, "over25")
                btts_alpha, btts_base = choose_alpha_binary(train, FEATURE_COLS, "btts")
            else:
                prior = {c: float((train["outcome"] == c).mean()) for c in ["H", "D", "A"]}
                out_cal = ShrinkCalibrator(["H", "D", "A"], 0.0, prior)
                over_alpha, over_base = 0.0, float(train["over25"].mean())
                btts_alpha, btts_base = 0.0, float(train["btts"].mean())

            next_refit = i + refit_every

        test = feat.iloc[[i]]
        r = feat.iloc[i]
        raw_probs = prob_dict_from_model(out_model, test[FEATURE_COLS], ["H", "D", "A"])
        hyb_probs = out_cal.apply(raw_probs)

        over_classes = list(over_model.named_steps["model"].classes_)
        over_raw = float(over_model.predict_proba(test[FEATURE_COLS])[0][over_classes.index(1)])
        over_p = float((1.0 - over_alpha) * over_raw + over_alpha * over_base)

        btts_classes = list(btts_model.named_steps["model"].classes_)
        btts_raw = float(btts_model.predict_proba(test[FEATURE_COLS])[0][btts_classes.index(1)])
        btts_p = float((1.0 - btts_alpha) * btts_raw + btts_alpha * btts_base)

        pois_probs = {"H": float(r["pois_home_prob"]), "D": float(r["pois_draw_prob"]), "A": float(r["pois_away_prob"])}
        actual = r["outcome"]

        rows.append({
            "date": str(r["date"].date()),
            "home": r["home_team"],
            "away": r["away_team"],
            "actual": actual,
            "actual_over25": int(r["over25"]),
            "actual_btts": int(r["btts"]),

            "baseline_pick": max(pois_probs, key=pois_probs.get),
            "baseline_probs": pois_probs,
            "baseline_over25_prob": float(r["pois_over25_prob"]),
            "baseline_btts_prob": float(r["pois_btts_prob"]),
            "baseline_logloss": logloss(pois_probs, actual),
            "baseline_brier": brier(pois_probs, actual),

            "hybrid_pick": max(hyb_probs, key=hyb_probs.get),
            "hybrid_probs": hyb_probs,
            "hybrid_over25_prob": max(0.001, min(0.999, over_p)),
            "hybrid_btts_prob": max(0.001, min(0.999, btts_p)),
            "hybrid_logloss": logloss(hyb_probs, actual),
            "hybrid_brier": brier(hyb_probs, actual),
        })

    summary = {}
    summary.update(metrics(rows, "baseline"))
    summary.update(metrics(rows, "hybrid"))
    summary["calibration_enabled"] = bool(calibrate)
    summary["min_train"] = min_train
    summary["refit_every"] = refit_every

    # Improvement deltas. Positive accuracy delta is good; negative loss delta is good.
    summary["delta_1x2_accuracy"] = summary["hybrid_1x2_accuracy"] - summary["baseline_1x2_accuracy"]
    summary["delta_over25_accuracy"] = summary["hybrid_over25_accuracy"] - summary["baseline_over25_accuracy"]
    summary["delta_log_loss"] = summary["hybrid_log_loss"] - summary["baseline_log_loss"]
    summary["delta_brier"] = summary["hybrid_brier"] - summary["baseline_brier"]

    return {"summary": summary, "predictions": rows}


def predict_one(feat: pd.DataFrame, home: str, away: str, calibrate: bool = True) -> dict:
    train = feat.copy()
    out_model = fit_multiclass_model(train, FEATURE_COLS)
    over_model = fit_binary_model(train, FEATURE_COLS, "over25")
    btts_model = fit_binary_model(train, FEATURE_COLS, "btts")
    a, prior = choose_alpha_multiclass(train, FEATURE_COLS) if calibrate else (0.0, {c: float((train["outcome"] == c).mean()) for c in ["H","D","A"]})
    out_cal = ShrinkCalibrator(["H","D","A"], a, prior)
    over_alpha, over_base = choose_alpha_binary(train, FEATURE_COLS, "over25") if calibrate else (0.0, float(train["over25"].mean()))
    btts_alpha, btts_base = choose_alpha_binary(train, FEATURE_COLS, "btts") if calibrate else (0.0, float(train["btts"].mean()))

    # Build synthetic feature row using the latest historical snapshots by appending a fake fixture.
    # Easiest robust method: create a fake final row and rebuild features.
    base_rows = []
    # Not available here, so approximate using average rows of the requested teams from feature table.
    h = canonical(home); ateam = canonical(away)
    h_rows = feat[(feat["home_team"] == h) | (feat["away_team"] == h)].tail(10)
    a_rows = feat[(feat["home_team"] == ateam) | (feat["away_team"] == ateam)].tail(10)

    global_row = feat[FEATURE_COLS].median(numeric_only=True).to_dict()
    x = {}
    for c in FEATURE_COLS:
        x[c] = global_row.get(c, 0.0)

    # Use rank and Poisson fallback from recent feature rows if possible.
    rank_h = RANKS.get(h, 70); rank_a = RANKS.get(ateam, 70)
    x["rank_home"] = rank_h; x["rank_away"] = rank_a; x["rank_diff"] = rank_a - rank_h
    if not h_rows.empty:
        x["games_home"] = min(10, len(h_rows))
    if not a_rows.empty:
        x["games_away"] = min(10, len(a_rows))

    xdf = pd.DataFrame([x], columns=FEATURE_COLS)
    raw_probs = prob_dict_from_model(out_model, xdf, ["H","D","A"])
    probs = out_cal.apply(raw_probs)

    over_classes = list(over_model.named_steps["model"].classes_)
    over_raw = float(over_model.predict_proba(xdf)[0][over_classes.index(1)])
    over_p = float((1.0-over_alpha)*over_raw + over_alpha*over_base)

    btts_classes = list(btts_model.named_steps["model"].classes_)
    btts_raw = float(btts_model.predict_proba(xdf)[0][btts_classes.index(1)])
    btts_p = float((1.0-btts_alpha)*btts_raw + btts_alpha*btts_base)

    return {
        "home": home,
        "away": away,
        "outcome": probs,
        "pick": max(probs, key=probs.get),
        "over25_prob": max(0.001, min(0.999, over_p)),
        "btts_prob": max(0.001, min(0.999, btts_p)),
        "calibration_alpha_1x2": a,
        "note": "Single-match predict mode uses latest aggregate feature fallback; v3B will improve this via feature store fixture snapshots.",
    }


def write_markdown_report(result: dict, path: Path):
    s = result["summary"]
    lines = [
        "# OmniBet Lab v3A hybrid model comparison",
        "",
        "Walk-forward comparison between the v2 rolling Poisson baseline and the new v3A hybrid logistic layer.",
        "",
        "## Summary",
        "",
        f"- Matches tested: **{s['hybrid_matches']}**",
        f"- Baseline 1X2 accuracy: **{s['baseline_1x2_accuracy']:.3f}**",
        f"- Hybrid 1X2 accuracy: **{s['hybrid_1x2_accuracy']:.3f}**",
        f"- Delta 1X2 accuracy: **{s['delta_1x2_accuracy']:+.3f}**",
        f"- Baseline Over 2.5 accuracy: **{s['baseline_over25_accuracy']:.3f}**",
        f"- Hybrid Over 2.5 accuracy: **{s['hybrid_over25_accuracy']:.3f}**",
        f"- Delta Over 2.5 accuracy: **{s['delta_over25_accuracy']:+.3f}**",
        f"- Baseline log loss: **{s['baseline_log_loss']:.3f}**",
        f"- Hybrid log loss: **{s['hybrid_log_loss']:.3f}**",
        f"- Delta log loss: **{s['delta_log_loss']:+.3f}**",
        "",
        "## Interpretation",
        "",
        "The hybrid model adds rolling-form stats, rank priors, and calibrated logistic probabilities on top of Poisson-style score features. "
        "The goal is not merely higher accuracy; lower log loss and better-calibrated confidence are more important for value betting.",
        "",
        "If the hybrid improves log loss but not raw accuracy, it may still be valuable for odds comparison. If it improves neither, the next step is more data and stronger features, not a more complex GUI.",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Run OmniBet v3A hybrid model lab.")
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    ap.add_argument("--mode", choices=["walk-forward", "predict"], default="walk-forward")
    ap.add_argument("--min-train", type=int, default=90)
    ap.add_argument("--refit-every", type=int, default=25)
    ap.add_argument("--rolling", type=int, default=10)
    ap.add_argument("--no-calibration", action="store_true")
    ap.add_argument("--home", default=None)
    ap.add_argument("--away", default=None)
    ap.add_argument("--out", default="../reports/v3_hybrid_metrics.json")
    ap.add_argument("--md", default="../reports/v3_model_comparison.md")
    args = ap.parse_args()

    df = load_data(Path(args.data))
    feat = build_features(df, rolling_n=args.rolling)

    if args.mode == "predict":
        if not args.home or not args.away:
            raise SystemExit("--home and --away are required for predict mode")
        result = {"prediction": predict_one(feat, args.home, args.away, calibrate=not args.no_calibration)}
        print(json.dumps(result, indent=2))
        return

    result = walk_forward(feat, min_train=args.min_train, refit_every=args.refit_every, calibrate=not args.no_calibration)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    write_markdown_report(result, Path(args.md))
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
