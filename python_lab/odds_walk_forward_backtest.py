#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Tuple

SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_backtest_bets (
    bet_id TEXT PRIMARY KEY,
    match_id TEXT NOT NULL,
    match_date TEXT,
    market_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_probability REAL NOT NULL,
    placed_odds REAL NOT NULL,
    closing_odds REAL,
    implied_probability REAL NOT NULL,
    edge REAL NOT NULL,
    stake_units REAL NOT NULL,
    result TEXT NOT NULL,
    profit_units REAL NOT NULL,
    clv_percent REAL,
    decision TEXT NOT NULL,
    settlement_scope TEXT NOT NULL,
    raw_json TEXT NOT NULL
);
"""

SELECTIONS = ["home", "draw", "away"]
LABEL_TO_SELECTION = {"H": "home", "D": "draw", "A": "away"}
SELECTION_TO_LABEL = {v: k for k, v in LABEL_TO_SELECTION.items()}


def outcome(home_score: int, away_score: int) -> str:
    if home_score > away_score:
        return "H"
    if home_score < away_score:
        return "A"
    return "D"


def prior_probs(train_rows: List[dict]) -> Dict[str, float]:
    c = Counter({"H": 1.0, "D": 1.0, "A": 1.0})
    for r in train_rows:
        c[r["actual"]] += 1.0
    s = sum(c.values())
    return {LABEL_TO_SELECTION[k]: c[k] / s for k in ["H", "D", "A"]}


def load_matches(con: sqlite3.Connection) -> List[dict]:
    rows = con.execute(
        """SELECT match_id, match_date, home_team_name, away_team_name, home_score, away_score
           FROM matches_norm
           WHERE home_score IS NOT NULL AND away_score IS NOT NULL
           ORDER BY match_date, match_id"""
    ).fetchall()
    return [
        {"match_id": mid, "match_date": date, "home": h, "away": a, "home_score": int(hg), "away_score": int(ag), "actual": outcome(int(hg), int(ag))}
        for mid, date, h, a, hg, ag in rows
    ]


def load_1x2_odds(con: sqlite3.Connection) -> Dict[str, Dict[Tuple[str, str], float]]:
    out: Dict[str, Dict[Tuple[str, str], float]] = defaultdict(dict)
    rows = con.execute(
        """SELECT match_id, bookmaker, selection, odds_decimal
           FROM odds_snapshots
           WHERE market_id='football.1x2' AND odds_decimal IS NOT NULL"""
    ).fetchall()
    for match_id, bookmaker, selection, odds in rows:
        out[match_id][(str(bookmaker), str(selection))] = float(odds)
    return out


def no_vig_implied(odds_by_selection: Dict[str, float]) -> Dict[str, float]:
    inv = {s: 1.0 / o for s, o in odds_by_selection.items() if o and o > 1.0}
    total = sum(inv.values())
    if total <= 0:
        return {}
    return {s: v / total for s, v in inv.items()}


def settle(selection: str, actual_label: str, odds: float, stake: float) -> Tuple[str, float]:
    win = SELECTION_TO_LABEL[selection] == actual_label
    return ("win" if win else "loss", (odds - 1.0) * stake if win else -stake)


def run(args: argparse.Namespace) -> dict:
    con = sqlite3.connect(str(args.db))
    con.executescript(SCHEMA)
    con.execute("DELETE FROM paper_backtest_bets")
    matches = load_matches(con)
    odds = load_1x2_odds(con)

    bets = []
    skipped = []
    for idx, m in enumerate(matches):
        if idx < args.min_train:
            continue
        train_rows = matches[:idx]
        probs = prior_probs(train_rows)
        match_odds = odds.get(m["match_id"], {})
        placed = {s: match_odds.get((args.placed_bookmaker, s)) for s in SELECTIONS}
        closing = {s: match_odds.get((args.closing_bookmaker, s)) for s in SELECTIONS}
        if not all(placed.values()):
            skipped.append({"match_id": m["match_id"], "reason": "missing_placed_1x2_odds"})
            continue
        implied = no_vig_implied({s: float(placed[s]) for s in SELECTIONS})
        if not implied:
            skipped.append({"match_id": m["match_id"], "reason": "bad_implied_probabilities"})
            continue
        candidates = []
        for s in SELECTIONS:
            edge = probs[s] - implied[s]
            if edge >= args.min_edge:
                candidates.append((edge, s))
        candidates.sort(reverse=True)
        for edge, s in candidates[: args.max_selections_per_match]:
            po = float(placed[s])
            co = float(closing[s]) if closing.get(s) else None
            res, profit = settle(s, m["actual"], po, args.stake_units)
            clv_percent = ((po / co) - 1.0) * 100.0 if co and co > 0 else None
            rec = {
                "match_id": m["match_id"],
                "match_date": m["match_date"],
                "fixture": f"{m['home']} vs {m['away']}",
                "market_id": "football.1x2",
                "selection": s,
                "actual": LABEL_TO_SELECTION[m["actual"]],
                "model_probability": probs[s],
                "placed_odds": po,
                "closing_odds": co,
                "implied_probability": implied[s],
                "edge": edge,
                "stake_units": args.stake_units,
                "result": res,
                "profit_units": profit,
                "clv_percent": clv_percent,
                "decision": "PAPER_ONLY",
                "settlement_scope": "regulation_time",
                "train_rows": idx,
            }
            bet_id = f"{m['match_id']}:{s}:{len(bets)}"
            con.execute(
                """INSERT OR REPLACE INTO paper_backtest_bets
                   (bet_id, match_id, match_date, market_id, selection, model_probability,
                    placed_odds, closing_odds, implied_probability, edge, stake_units,
                    result, profit_units, clv_percent, decision, settlement_scope, raw_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    bet_id, rec["match_id"], rec["match_date"], rec["market_id"], rec["selection"], rec["model_probability"],
                    rec["placed_odds"], rec["closing_odds"], rec["implied_probability"], rec["edge"], rec["stake_units"],
                    rec["result"], rec["profit_units"], rec["clv_percent"], rec["decision"], rec["settlement_scope"], json.dumps(rec, sort_keys=True),
                ),
            )
            bets.append(rec)
    con.commit()
    con.close()

    total_stake = sum(b["stake_units"] for b in bets)
    profit = sum(b["profit_units"] for b in bets)
    clv_values = [b["clv_percent"] for b in bets if b["clv_percent"] is not None]
    report = {
        "ok": len(bets) >= args.min_bets,
        "warning": "Tiny odds/CLV walk-forward smoke. Paper-only; not a betting edge proof.",
        "db": str(args.db),
        "target_market": "football.1x2",
        "settlement_scope": "regulation_time",
        "placed_bookmaker": args.placed_bookmaker,
        "closing_bookmaker": args.closing_bookmaker,
        "min_train": args.min_train,
        "min_edge": args.min_edge,
        "matches_seen": len(matches),
        "matches_with_odds": sum(1 for m in matches if m["match_id"] in odds),
        "paper_bets": len(bets),
        "wins": sum(1 for b in bets if b["result"] == "win"),
        "losses": sum(1 for b in bets if b["result"] == "loss"),
        "total_stake_units": total_stake,
        "profit_units": profit,
        "roi": (profit / total_stake) if total_stake > 0 else None,
        "avg_edge": (sum(b["edge"] for b in bets) / len(bets)) if bets else None,
        "avg_clv_percent": (sum(clv_values) / len(clv_values)) if clv_values else None,
        "positive_clv_rows": sum(1 for v in clv_values if v > 0),
        "negative_clv_rows": sum(1 for v in clv_values if v < 0),
        "all_paper_only": all(b["decision"] == "PAPER_ONLY" for b in bets),
        "leakage_guard": {
            "probabilities": "expanding_prior_from_past_matches_only",
            "placed_odds": args.placed_bookmaker,
            "closing_odds": args.closing_bookmaker,
            "test_scope": "future matches after min_train",
        },
        "skipped": skipped[:20],
        "samples": bets[:12],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not report["ok"]:
        raise SystemExit(1)
    return report


def main() -> None:
    ap = argparse.ArgumentParser(description="Odds/CLV walk-forward paper backtest.")
    ap.add_argument("--db", default="../build/omnibet_v23_multisource.sqlite")
    ap.add_argument("--out", default="../reports/ci_v25_odds_clv_backtest.json")
    ap.add_argument("--placed-bookmaker", default="Bet365")
    ap.add_argument("--closing-bookmaker", default="Pinnacle/PS")
    ap.add_argument("--min-train", type=int, default=1)
    ap.add_argument("--min-edge", type=float, default=0.0)
    ap.add_argument("--min-bets", type=int, default=1)
    ap.add_argument("--max-selections-per-match", type=int, default=2)
    ap.add_argument("--stake-units", type=float, default=1.0)
    args = ap.parse_args()
    run(args)


if __name__ == "__main__":
    main()
