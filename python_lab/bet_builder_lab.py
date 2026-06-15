#!/usr/bin/env python3
"""
OmniBet Lab v3B bet-builder prototype.

This is not a bookmaker-grade same-game-pricing engine yet. It is a practical
first layer that:
- reads model probabilities from hybrid_model_lab,
- derives a small set of currently-supported/prototype football markets,
- optionally matches user/bookmaker odds from CSV,
- computes fair odds, EV, Kelly and quarter-Kelly,
- generates Safe / Balanced / Aggressive tickets,
- applies correlation/risk penalties and NO BET logic.

Future versions should replace derived placeholders with event/player-specific
models and learned joint distributions.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import json
import math
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Local imports
from hybrid_model_lab import load_data, build_features, predict_one


@dataclass
class Leg:
    market_id: str
    selection: str
    label: str
    probability: float
    fair_odds: float
    category: str
    tags: List[str]
    bookmaker_odds: Optional[float] = None
    edge: Optional[float] = None
    kelly: Optional[float] = None
    quarter_kelly: Optional[float] = None
    risk_note: str = ""


@dataclass
class Ticket:
    name: str
    legs: List[Leg]
    raw_probability: float
    adjusted_probability: float
    fair_odds: float
    bookmaker_odds: Optional[float]
    edge: Optional[float]
    quarter_kelly: Optional[float]
    correlation_risk: float
    decision: str
    notes: List[str]


def fair_odds(p: float) -> float:
    p = min(max(float(p), 1e-6), 0.999999)
    return 1.0 / p


def kelly_fraction(prob: float, odds: float) -> float:
    if odds is None or odds <= 1.0:
        return 0.0
    b = odds - 1.0
    q = 1.0 - prob
    k = (b * prob - q) / b
    return max(0.0, min(1.0, k))


def read_odds(path: Optional[Path]) -> Dict[Tuple[str, str], float]:
    """Read odds CSV with columns market_id,selection,odds[,bookmaker]."""
    out = {}
    if not path:
        return out
    with path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            try:
                out[(row["market_id"], row["selection"])] = float(row["odds"])
            except Exception:
                continue
    return out


def add_odds(leg: Leg, odds_map: Dict[Tuple[str, str], float]) -> Leg:
    odds = odds_map.get((leg.market_id, leg.selection))
    if odds is not None:
        leg.bookmaker_odds = odds
        leg.edge = leg.probability * odds - 1.0
        k = kelly_fraction(leg.probability, odds)
        leg.kelly = k
        leg.quarter_kelly = k * 0.25
    return leg


def derive_legs(pred: dict, odds_map: Dict[Tuple[str, str], float]) -> List[Leg]:
    p = pred["outcome"]
    home = pred["home"]
    away = pred["away"]
    over25 = float(pred["over25_prob"])
    btts = float(pred["btts_prob"])

    # Conservative derived probabilities. These are placeholders until we have
    # full score matrix / event/player models in v4+.
    over15 = min(0.96, over25 + 0.18)
    over35 = max(0.04, over25 - 0.22)
    under25 = 1.0 - over25
    under35 = 1.0 - over35

    home_or_draw = p["H"] + p["D"]
    home_or_away = p["H"] + p["A"]
    draw_or_away = p["D"] + p["A"]

    home_over05 = min(0.95, p["H"] * 0.55 + over15 * 0.55)
    away_over05 = min(0.95, p["A"] * 0.55 + over15 * 0.45)
    home_over15 = max(0.05, p["H"] * 0.45 + over25 * 0.35)
    away_over15 = max(0.04, p["A"] * 0.45 + over25 * 0.25)

    proto_corners_over85 = 0.50 + min(0.16, max(-0.16, (over25 - 0.50) * 0.40))
    proto_cards_over35 = 0.50  # neutral until we have referee/discipline model

    candidates = [
        Leg("football.1x2", "home", f"{home} win", p["H"], fair_odds(p["H"]), "core", ["result", "home_strength"]),
        Leg("football.1x2", "draw", "Draw", p["D"], fair_odds(p["D"]), "core", ["result", "draw"]),
        Leg("football.1x2", "away", f"{away} win", p["A"], fair_odds(p["A"]), "core", ["result", "away_strength"]),

        Leg("football.double_chance", "1X", f"{home} or Draw", home_or_draw, fair_odds(home_or_draw), "core", ["result", "safer"]),
        Leg("football.double_chance", "12", "No Draw", home_or_away, fair_odds(home_or_away), "core", ["result"]),
        Leg("football.double_chance", "X2", f"Draw or {away}", draw_or_away, fair_odds(draw_or_away), "core", ["result", "safer"]),

        Leg("football.total_goals", "over_1.5", "Over 1.5 Goals", over15, fair_odds(over15), "goals", ["goals", "tempo"]),
        Leg("football.total_goals", "over_2.5", "Over 2.5 Goals", over25, fair_odds(over25), "goals", ["goals", "tempo"]),
        Leg("football.total_goals", "under_2.5", "Under 2.5 Goals", under25, fair_odds(under25), "goals", ["goals", "defensive"]),
        Leg("football.total_goals", "over_3.5", "Over 3.5 Goals", over35, fair_odds(over35), "goals", ["goals", "chaos"]),
        Leg("football.total_goals", "under_3.5", "Under 3.5 Goals", under35, fair_odds(under35), "goals", ["goals", "safer"]),

        Leg("football.btts", "yes", "BTTS Yes", btts, fair_odds(btts), "goals", ["goals", "both_teams_score"]),
        Leg("football.btts", "no", "BTTS No", 1.0 - btts, fair_odds(1.0 - btts), "goals", ["goals", "defensive"]),

        Leg("football.team_goals", "home_over_0.5", f"{home} Over 0.5 Goals", home_over05, fair_odds(home_over05), "team_goals", ["team_attacking", "goals"]),
        Leg("football.team_goals", "away_over_0.5", f"{away} Over 0.5 Goals", away_over05, fair_odds(away_over05), "team_goals", ["team_attacking", "goals"]),
        Leg("football.team_goals", "home_over_1.5", f"{home} Over 1.5 Goals", home_over15, fair_odds(home_over15), "team_goals", ["team_attacking", "goals"]),
        Leg("football.team_goals", "away_over_1.5", f"{away} Over 1.5 Goals", away_over15, fair_odds(away_over15), "team_goals", ["team_attacking", "goals"]),

        Leg("football.total_corners", "over_8.5", "Over 8.5 Corners", proto_corners_over85, fair_odds(proto_corners_over85), "corners", ["corners", "tempo"], risk_note="prototype: no dedicated corners model yet"),
        Leg("football.total_cards", "over_3.5", "Over 3.5 Cards", proto_cards_over35, fair_odds(proto_cards_over35), "cards", ["cards", "physicality"], risk_note="prototype: no referee/card model yet"),
    ]

    return [add_odds(x, odds_map) for x in candidates]


# Pairwise risk: 0 none, 1 light, 2 medium, 3 high, 4 contradiction/unstable.
def pair_risk(a: Leg, b: Leg) -> Tuple[int, str]:
    # same exact family conflict
    if a.market_id == b.market_id and a.selection != b.selection:
        return 4, f"conflicting selections in {a.market_id}"

    tags_a = set(a.tags)
    tags_b = set(b.tags)

    if "goals" in tags_a and "goals" in tags_b:
        return 2, "goal-market correlation"
    if "result" in tags_a and "team_attacking" in tags_b:
        return 2, "result/team-goal correlation"
    if "team_attacking" in tags_a and "result" in tags_b:
        return 2, "result/team-goal correlation"
    if "corners" in tags_a and "goals" in tags_b:
        return 1, "tempo correlation"
    if "goals" in tags_a and "corners" in tags_b:
        return 1, "tempo correlation"
    if "cards" in tags_a and "chaos" in tags_b:
        return 3, "chaos/card instability"
    if "defensive" in tags_a and "chaos" in tags_b:
        return 3, "defensive/chaos tension"
    return 0, ""


def ticket_probability(legs: List[Leg]) -> Tuple[float, float, float, List[str]]:
    raw = 1.0
    for leg in legs:
        raw *= leg.probability

    risk = 0
    notes = []
    for a, b in itertools.combinations(legs, 2):
        r, note = pair_risk(a, b)
        risk += r
        if note:
            notes.append(note)

    # Correlation penalty: conservative for same-game builders.
    adjusted = raw * (0.93 ** risk)
    return raw, adjusted, float(risk), sorted(set(notes))


def combined_book_odds(legs: List[Leg]) -> Optional[float]:
    if any(l.bookmaker_odds is None for l in legs):
        return None
    out = 1.0
    for l in legs:
        out *= float(l.bookmaker_odds)
    return out


def decision_for(ticket: Ticket, min_edge: float = 0.03) -> str:
    if ticket.correlation_risk >= 7:
        return "NO BET - correlation risk too high"
    if ticket.bookmaker_odds is None:
        return "PRICE NEEDED - add bookmaker odds"
    if ticket.edge is None or ticket.edge < min_edge:
        return "NO BET - edge too small"
    if ticket.adjusted_probability < 0.10:
        return "NO BET - probability too low"
    if ticket.quarter_kelly is not None and ticket.quarter_kelly > 0:
        if ticket.quarter_kelly < 0.005:
            return "BET SMALL - tiny edge"
        return "OK - quarter Kelly only"
    return "NO BET"


def make_ticket(name: str, legs: List[Leg]) -> Ticket:
    raw, adj, risk, notes = ticket_probability(legs)
    fair = fair_odds(adj)
    book = combined_book_odds(legs)
    edge = (adj * book - 1.0) if book is not None else None
    qk = kelly_fraction(adj, book) * 0.25 if book is not None else None
    t = Ticket(name, legs, raw, adj, fair, book, edge, qk, risk, "", notes)
    t.decision = decision_for(t)
    return t


def select_tickets(legs: List[Leg]) -> List[Ticket]:
    # Candidate filters
    safe_pool = [l for l in legs if l.probability >= 0.62 and l.category in {"core", "goals", "team_goals"}]
    balanced_pool = [l for l in legs if l.probability >= 0.52 and l.category in {"core", "goals", "team_goals", "corners"}]
    aggressive_pool = [l for l in legs if l.probability >= 0.45 and l.category in {"core", "goals", "team_goals", "corners", "cards"}]

    tickets = []

    def best_combo(pool: List[Leg], n: int, name: str) -> Optional[Ticket]:
        best = None
        for combo in itertools.combinations(pool, n):
            # avoid too many legs from the same market
            if len({(x.market_id, x.selection.split("_")[0]) for x in combo}) < n:
                continue
            t = make_ticket(name, list(combo))
            # Prefer edge if odds exist, otherwise adjusted probability/fair odds balance.
            score = (t.edge if t.edge is not None else 0.0) + (t.adjusted_probability * 0.15) - (t.correlation_risk * 0.02)
            if best is None or score > best[0]:
                best = (score, t)
        return best[1] if best else None

    for n, name, pool in [
        (2, "Safe Builder", safe_pool),
        (3, "Balanced Builder", balanced_pool),
        (4, "Aggressive Builder", aggressive_pool),
    ]:
        t = best_combo(pool, n, name)
        if t:
            tickets.append(t)

    return tickets


def as_jsonable_leg(leg: Leg) -> dict:
    d = asdict(leg)
    return d


def as_jsonable_ticket(t: Ticket) -> dict:
    d = asdict(t)
    d["legs"] = [as_jsonable_leg(l) for l in t.legs]
    return d


def main():
    ap = argparse.ArgumentParser(description="Generate prototype same-game bet-builder tickets.")
    ap.add_argument("--data", default="../data/unified_intl_matches.csv")
    ap.add_argument("--home", required=True)
    ap.add_argument("--away", required=True)
    ap.add_argument("--odds", default=None, help="Optional odds CSV: market_id,selection,odds,bookmaker")
    ap.add_argument("--out", default="../reports/v3b_bet_builder.json")
    args = ap.parse_args()

    df = load_data(Path(args.data))
    feat = build_features(df, rolling_n=10)
    pred = predict_one(feat, args.home, args.away, calibrate=True)
    odds_map = read_odds(Path(args.odds)) if args.odds else {}

    legs = derive_legs(pred, odds_map)
    tickets = select_tickets(legs)

    out = {
        "fixture": {"home": args.home, "away": args.away},
        "model_prediction": pred,
        "available_legs": [as_jsonable_leg(l) for l in legs],
        "tickets": [as_jsonable_ticket(t) for t in tickets],
        "notes": [
            "v3B is a prototype. It supports core/result/goals markets now and reserves player/event markets for future event-data models.",
            "Same-game probabilities are correlation-adjusted heuristically, not bookmaker-grade joint pricing.",
            "NO BET logic is intentional; the tool should reject weak or badly priced tickets.",
        ],
    }

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(json.dumps({
        "fixture": out["fixture"],
        "tickets": [
            {
                "name": t.name,
                "legs": [l.label for l in t.legs],
                "adjusted_probability": round(t.adjusted_probability, 4),
                "fair_odds": round(t.fair_odds, 3),
                "bookmaker_odds": None if t.bookmaker_odds is None else round(t.bookmaker_odds, 3),
                "edge": None if t.edge is None else round(t.edge, 4),
                "correlation_risk": t.correlation_risk,
                "decision": t.decision,
            }
            for t in tickets
        ],
        "out": args.out,
    }, indent=2))


if __name__ == "__main__":
    main()
