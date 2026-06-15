#!/usr/bin/env python3
"""Honest walk-forward backtest for OmniBet football baseline.

This is intentionally simple and transparent. It retrains the baseline from
only historical rows before each match, then scores the next match. That makes
it much more honest than the in-sample v0 test.
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


def canonical(name: str) -> str:
    name = (name or "").strip()
    aliases = {
        "usa": "USA",
        "united states": "USA",
        "united states of america": "USA",
        "czech republic": "Czechia",
        "turkey": "Turkiye",
        "türkiye": "Turkiye",
        "cabo verde": "Cape Verde",
        "cape verde islands": "Cape Verde",
        "curacao": "Curacao",
        "curaçao": "Curacao",
        "dr congo": "DR Congo",
        "congo dr": "DR Congo",
        "korea republic": "South Korea",
    }
    return aliases.get(name.lower(), name)


@dataclass
class Row:
    date: str
    home: str
    away: str
    hg: float
    ag: float


@dataclass
class Agg:
    m: float = 0.0
    gf: float = 0.0
    ga: float = 0.0


@dataclass
class Model:
    teams: dict[str, Agg]
    avg_g: float


def load_rows(path: Path) -> list[Row]:
    out: list[Row] = []
    with path.open(newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for x in r:
            try:
                hg = float(x["home_goals"])
                ag = float(x["away_goals"])
            except Exception:
                continue
            out.append(Row(x.get("date", ""), canonical(x["home_team"]), canonical(x["away_team"]), hg, ag))
    return sorted(out, key=lambda x: x.date)


def fit(rows: list[Row]) -> Model:
    teams: dict[str, Agg] = defaultdict(Agg)
    total_goals = 0.0
    for x in rows:
        total_goals += x.hg + x.ag
        h = teams[x.home]
        a = teams[x.away]
        h.m += 1; h.gf += x.hg; h.ga += x.ag
        a.m += 1; a.gf += x.ag; a.ga += x.hg
    avg = total_goals / max(1.0, 2.0 * len(rows))
    return Model(dict(teams), max(0.1, avg))


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def poisson(k: int, lam: float) -> float:
    p = math.exp(-lam)
    for i in range(k):
        p *= lam / (i + 1)
    return p


def predict(model: Model, home: str, away: str):
    z = Agg()
    h = model.teams.get(home, z)
    a = model.teams.get(away, z)
    hm = max(1.0, h.m)
    am = max(1.0, a.m)
    avg = model.avg_g
    h_att = clamp((h.gf / hm) / avg, 0.35, 3.2)
    h_def = clamp((h.ga / hm) / avg, 0.35, 3.2)
    a_att = clamp((a.gf / am) / avg, 0.35, 3.2)
    a_def = clamp((a.ga / am) / avg, 0.35, 3.2)
    lh = clamp(avg * h_att * math.sqrt(a_def), 0.05, 4.5)
    la = clamp(avg * a_att * math.sqrt(h_def), 0.05, 4.5)
    hp = dp = ap = o25 = 0.0
    for i in range(8):
        for j in range(8):
            p = poisson(i, lh) * poisson(j, la)
            if i > j:
                hp += p
            elif i == j:
                dp += p
            else:
                ap += p
            if i + j >= 3:
                o25 += p
    s = hp + dp + ap
    if s:
        hp, dp, ap = hp / s, dp / s, ap / s
    return {"H": hp, "D": dp, "A": ap, "O25": o25, "lambda_home": lh, "lambda_away": la}


def evaluate(rows: list[Row], min_train: int) -> dict[str, float]:
    n = correct = correct_o25 = 0
    logloss = brier = 0.0
    for i in range(min_train, len(rows)):
        model = fit(rows[:i])
        x = rows[i]
        pred = predict(model, x.home, x.away)
        actual = "H" if x.hg > x.ag else "A" if x.ag > x.hg else "D"
        pick = max(("H", "D", "A"), key=lambda k: pred[k])
        p_actual = max(1e-12, pred[actual])
        correct += int(pick == actual)
        correct_o25 += int((pred["O25"] >= 0.5) == (x.hg + x.ag >= 3))
        logloss += -math.log(p_actual)
        brier += sum((pred[k] - (1.0 if k == actual else 0.0)) ** 2 for k in ("H", "D", "A"))
        n += 1
    return {
        "matches": n,
        "1x2_accuracy": correct / n if n else 0,
        "over25_accuracy": correct_o25 / n if n else 0,
        "log_loss": logloss / n if n else 0,
        "brier_1x2": brier / n if n else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    ap.add_argument("--min-train", type=int, default=80)
    args = ap.parse_args()
    rows = load_rows(Path(args.data))
    result = evaluate(rows, args.min_train)
    for k, v in result.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")


if __name__ == "__main__":
    main()
