#!/usr/bin/env python3
"""
Dixon-Coles football model lab.

This is the first serious modelling pass for OmniBet Lab. It provides:
- a leakage-safe train/test split by date,
- Poisson baseline,
- Dixon-Coles low-score correction,
- optional exponential time weighting,
- holdout and walk-forward evaluation.

The implementation is intentionally transparent and pure Python/NumPy/SciPy.
Once the model design stabilizes, the same math can be ported to Rust or C++.
"""
from __future__ import annotations

import argparse
import json
import math
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import gammaln


def canonical(name: str) -> str:
    aliases = {
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
    return aliases.get((name or "").strip(), (name or "").strip())


def parse_date(s: str) -> datetime:
    return datetime.strptime(str(s)[:10], "%Y-%m-%d")


def load_matches(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "home_team", "away_team", "home_goals", "away_goals"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    df = df.dropna(subset=["date", "home_team", "away_team", "home_goals", "away_goals"]).copy()
    df["date"] = pd.to_datetime(df["date"].astype(str).str[:10])
    df["home_team"] = df["home_team"].map(canonical)
    df["away_team"] = df["away_team"].map(canonical)
    df["home_goals"] = df["home_goals"].astype(int)
    df["away_goals"] = df["away_goals"].astype(int)
    df = df.sort_values(["date", "home_team", "away_team"]).reset_index(drop=True)
    return df


def poisson_pmf(k: int, lam: float) -> float:
    if k < 0:
        return 0.0
    lam = max(float(lam), 1e-9)
    out = math.exp(-lam)
    for i in range(k):
        out *= lam / (i + 1)
    return out


def dc_tau(x: int, y: int, lam: float, mu: float, rho: float) -> float:
    """Dixon-Coles correction for low scores."""
    if x == 0 and y == 0:
        return 1.0 - lam * mu * rho
    if x == 0 and y == 1:
        return 1.0 + lam * rho
    if x == 1 and y == 0:
        return 1.0 + mu * rho
    if x == 1 and y == 1:
        return 1.0 - rho
    return 1.0


def score_matrix(lam: float, mu: float, rho: float = 0.0, max_goals: int = 8, dixon_coles: bool = True) -> np.ndarray:
    mat = np.zeros((max_goals + 1, max_goals + 1), dtype=float)
    for x in range(max_goals + 1):
        for y in range(max_goals + 1):
            p = poisson_pmf(x, lam) * poisson_pmf(y, mu)
            if dixon_coles:
                tau = dc_tau(x, y, lam, mu, rho)
                if tau <= 0:
                    p = 0.0
                else:
                    p *= tau
            mat[x, y] = p
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


def brier_1x2(probs: Dict[str, float], actual: str) -> float:
    return sum((probs[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ["H", "D", "A"])


def logloss_1x2(probs: Dict[str, float], actual: str) -> float:
    return -math.log(max(1e-12, probs[actual]))


@dataclass
class FitResult:
    teams: List[str]
    attack: np.ndarray
    defense: np.ndarray
    intercept: float
    home_adv: float
    rho: float
    success: bool
    fun: float
    n_train: int


class DixonColesModel:
    def __init__(self, xi: float = 0.001, l2: float = 0.10, max_goals: int = 8):
        self.xi = xi
        self.l2 = l2
        self.max_goals = max_goals
        self.fit_result: FitResult | None = None
        self.team_to_idx: Dict[str, int] = {}

    def fit(self, df: pd.DataFrame, maxiter: int = 300) -> FitResult:
        teams = sorted(set(df["home_team"]).union(df["away_team"]))
        self.team_to_idx = {t: i for i, t in enumerate(teams)}
        n = len(teams)

        home_idx = df["home_team"].map(self.team_to_idx).to_numpy(dtype=int)
        away_idx = df["away_team"].map(self.team_to_idx).to_numpy(dtype=int)
        hg = df["home_goals"].to_numpy(dtype=int)
        ag = df["away_goals"].to_numpy(dtype=int)

        # Time weights: recent games count more.
        max_date = df["date"].max()
        days_old = (max_date - df["date"]).dt.days.to_numpy(dtype=float)
        weights = np.exp(-self.xi * days_old)

        avg_goals = max(0.05, (hg.sum() + ag.sum()) / (2.0 * len(df)))
        init = np.zeros(2 * n + 3, dtype=float)
        init[2 * n] = math.log(avg_goals)  # intercept
        init[2 * n + 1] = 0.05             # home advantage
        init[2 * n + 2] = 0.0              # rho

        def unpack(params):
            attack = params[:n].copy()
            defense = params[n:2*n].copy()
            # center for identifiability
            attack -= attack.mean()
            defense -= defense.mean()
            intercept = params[2*n]
            home_adv = params[2*n + 1]
            rho = params[2*n + 2]
            return attack, defense, intercept, home_adv, rho

        def objective(params):
            attack, defense, intercept, home_adv, rho = unpack(params)
            # Vectorized expected goals and Dixon-Coles low-score correction.
            lam = np.exp(intercept + home_adv + attack[home_idx] + defense[away_idx])
            mu = np.exp(intercept + attack[away_idx] + defense[home_idx])

            logp = -lam + hg * np.log(np.maximum(lam, 1e-12)) - gammaln(hg + 1)
            logp += -mu + ag * np.log(np.maximum(mu, 1e-12)) - gammaln(ag + 1)

            tau = np.ones_like(lam)
            m00 = (hg == 0) & (ag == 0)
            m01 = (hg == 0) & (ag == 1)
            m10 = (hg == 1) & (ag == 0)
            m11 = (hg == 1) & (ag == 1)
            tau[m00] = 1.0 - lam[m00] * mu[m00] * rho
            tau[m01] = 1.0 + lam[m01] * rho
            tau[m10] = 1.0 + mu[m10] * rho
            tau[m11] = 1.0 - rho

            if np.any(tau <= 0) or not np.all(np.isfinite(tau)):
                return 1e9

            ll = float(np.sum(weights * (logp + np.log(tau))))
            penalty = self.l2 * (float(np.sum(attack * attack)) + float(np.sum(defense * defense)) + home_adv * home_adv + rho * rho)
            return -ll + penalty

        bounds = [(-2.5, 2.5)] * (2 * n) + [(-2.0, 2.0), (-1.0, 1.0), (-0.10, 0.10)]
        res = minimize(objective, init, method="L-BFGS-B", bounds=bounds, options={"maxiter": maxiter, "ftol": 1e-7})

        attack, defense, intercept, home_adv, rho = unpack(res.x)
        self.fit_result = FitResult(
            teams=teams,
            attack=attack,
            defense=defense,
            intercept=float(intercept),
            home_adv=float(home_adv),
            rho=float(rho),
            success=bool(res.success),
            fun=float(res.fun),
            n_train=int(len(df)),
        )
        return self.fit_result

    def predict(self, home: str, away: str, neutral: bool = True) -> dict:
        if self.fit_result is None:
            raise RuntimeError("model not fitted")
        fr = self.fit_result
        h = canonical(home)
        a = canonical(away)
        hi = self.team_to_idx.get(h)
        ai = self.team_to_idx.get(a)
        # Unknown-team fallback: neutral attack/defense.
        h_attack = fr.attack[hi] if hi is not None else 0.0
        a_attack = fr.attack[ai] if ai is not None else 0.0
        h_def = fr.defense[hi] if hi is not None else 0.0
        a_def = fr.defense[ai] if ai is not None else 0.0
        home_adv = 0.0 if neutral else fr.home_adv
        lam = math.exp(fr.intercept + home_adv + h_attack + a_def)
        mu = math.exp(fr.intercept + a_attack + h_def)
        mat = score_matrix(lam, mu, fr.rho, max_goals=self.max_goals, dixon_coles=True)
        probs = outcome_probs(mat)
        idx = np.unravel_index(int(np.argmax(mat)), mat.shape)
        return {
            "home": home,
            "away": away,
            "lambda_home": lam,
            "lambda_away": mu,
            "rho": fr.rho,
            "outcome": probs,
            "over_25": over25_prob(mat),
            "btts": float(1.0 - mat[0, :].sum() - mat[:, 0].sum() + mat[0, 0]),
            "most_likely": [int(idx[0]), int(idx[1])],
            "score_matrix": mat,
        }


def actual_outcome(row) -> str:
    if row.home_goals > row.away_goals:
        return "H"
    if row.home_goals < row.away_goals:
        return "A"
    return "D"


def evaluate_predictions(preds: List[dict]) -> dict:
    if not preds:
        return {}
    n = len(preds)
    acc = sum(p["pick"] == p["actual"] for p in preds) / n
    o25_acc = sum((p["over25_prob"] >= 0.5) == bool(p["actual_over25"]) for p in preds) / n
    return {
        "matches": n,
        "1x2_accuracy": acc,
        "over25_accuracy": o25_acc,
        "log_loss": sum(p["log_loss"] for p in preds) / n,
        "brier_1x2": sum(p["brier"] for p in preds) / n,
        "avg_home_prob": sum(p["probs"]["H"] for p in preds) / n,
        "avg_draw_prob": sum(p["probs"]["D"] for p in preds) / n,
        "avg_away_prob": sum(p["probs"]["A"] for p in preds) / n,
    }


def holdout(df: pd.DataFrame, test_frac: float, xi: float, l2: float, maxiter: int) -> dict:
    cut = int(len(df) * (1.0 - test_frac))
    train = df.iloc[:cut].copy()
    test = df.iloc[cut:].copy()
    model = DixonColesModel(xi=xi, l2=l2)
    fit = model.fit(train, maxiter=maxiter)

    preds = []
    for row in test.itertuples(index=False):
        pred = model.predict(row.home_team, row.away_team, neutral=True)
        probs = pred["outcome"]
        actual = actual_outcome(row)
        pick = max(probs, key=probs.get)
        preds.append({
            "date": str(row.date.date()),
            "home": row.home_team,
            "away": row.away_team,
            "actual": actual,
            "pick": pick,
            "probs": probs,
            "over25_prob": pred["over_25"],
            "actual_over25": int(row.home_goals + row.away_goals >= 3),
            "log_loss": logloss_1x2(probs, actual),
            "brier": brier_1x2(probs, actual),
            "lambda_home": pred["lambda_home"],
            "lambda_away": pred["lambda_away"],
            "rho": pred["rho"],
        })
    metrics = evaluate_predictions(preds)
    metrics.update({"mode": "holdout", "train_matches": len(train), "test_matches": len(test), "fit_success": fit.success, "rho": fit.rho})
    return {"metrics": metrics, "predictions": preds}


def walk_forward(df: pd.DataFrame, min_train: int, refit_every: int, xi: float, l2: float, maxiter: int) -> dict:
    preds = []
    model = None
    fit = None
    next_refit = min_train
    for i in range(min_train, len(df)):
        if model is None or i >= next_refit:
            train = df.iloc[:i].copy()
            model = DixonColesModel(xi=xi, l2=l2)
            fit = model.fit(train, maxiter=maxiter)
            next_refit = i + refit_every
        row = df.iloc[i]
        pred = model.predict(row.home_team, row.away_team, neutral=True)
        probs = pred["outcome"]
        actual = "H" if row.home_goals > row.away_goals else ("A" if row.home_goals < row.away_goals else "D")
        pick = max(probs, key=probs.get)
        preds.append({
            "date": str(row.date.date()),
            "home": row.home_team,
            "away": row.away_team,
            "actual": actual,
            "pick": pick,
            "probs": probs,
            "over25_prob": pred["over_25"],
            "actual_over25": int(row.home_goals + row.away_goals >= 3),
            "log_loss": logloss_1x2(probs, actual),
            "brier": brier_1x2(probs, actual),
            "lambda_home": pred["lambda_home"],
            "lambda_away": pred["lambda_away"],
            "rho": pred["rho"],
        })
    metrics = evaluate_predictions(preds)
    metrics.update({"mode": "walk_forward", "min_train": min_train, "refit_every": refit_every, "last_fit_success": bool(fit.success if fit else False), "last_rho": float(fit.rho if fit else 0.0)})
    return {"metrics": metrics, "predictions": preds}


def save_run_to_db(db_path: Path, result: dict, model_name: str = "dixon_coles_v2"):
    con = sqlite3.connect(str(db_path))
    run_id = f"{model_name}:{datetime.utcnow().isoformat(timespec='seconds')}"
    metrics = result["metrics"]
    con.execute(
        "INSERT OR REPLACE INTO model_runs(run_id, model_name, sport, params_json, metrics_json) VALUES (?, ?, 'football', ?, ?)",
        (run_id, model_name, json.dumps({"source": "python_lab/dixon_coles_lab.py"}), json.dumps(metrics)),
    )
    con.commit()
    con.close()
    return run_id


def main():
    ap = argparse.ArgumentParser(description="Fit and backtest a Dixon-Coles model.")
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    ap.add_argument("--db", default=None, help="Optional SQLite DB to save model_run metrics.")
    ap.add_argument("--mode", choices=["holdout", "walk-forward", "predict"], default="walk-forward")
    ap.add_argument("--test-frac", type=float, default=0.25)
    ap.add_argument("--min-train", type=int, default=80)
    ap.add_argument("--refit-every", type=int, default=25)
    ap.add_argument("--xi", type=float, default=0.0015, help="Dixon-Coles exponential decay strength.")
    ap.add_argument("--l2", type=float, default=0.10, help="L2 regularization.")
    ap.add_argument("--maxiter", type=int, default=250)
    ap.add_argument("--home", default=None)
    ap.add_argument("--away", default=None)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    df = load_matches(Path(args.data))

    if args.mode == "holdout":
        result = holdout(df, args.test_frac, args.xi, args.l2, args.maxiter)
    elif args.mode == "walk-forward":
        result = walk_forward(df, args.min_train, args.refit_every, args.xi, args.l2, args.maxiter)
    else:
        if not args.home or not args.away:
            raise SystemExit("--home and --away are required for predict mode")
        model = DixonColesModel(xi=args.xi, l2=args.l2)
        fit = model.fit(df, maxiter=args.maxiter)
        pred = model.predict(args.home, args.away, neutral=True)
        result = {
            "metrics": {"mode": "predict", "fit_success": fit.success, "train_matches": len(df), "rho": fit.rho},
            "prediction": {
                "home": pred["home"],
                "away": pred["away"],
                "lambda_home": pred["lambda_home"],
                "lambda_away": pred["lambda_away"],
                "rho": pred["rho"],
                "outcome": pred["outcome"],
                "over_25": pred["over_25"],
                "btts": pred["btts"],
                "most_likely": pred["most_likely"],
            },
        }

    if args.db:
        run_id = save_run_to_db(Path(args.db), result)
        result["model_run_id"] = run_id

    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(result, indent=2), encoding="utf-8")

    print(json.dumps(result["metrics"], indent=2))
    if args.mode == "predict":
        print(json.dumps(result["prediction"], indent=2))


if __name__ == "__main__":
    main()
