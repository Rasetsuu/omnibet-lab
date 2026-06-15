#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, Tuple

LEDGER_SCHEMA = """
CREATE TABLE IF NOT EXISTS paper_bets (
    bet_id TEXT PRIMARY KEY,
    fixture_id TEXT NOT NULL,
    market_id TEXT NOT NULL,
    selection TEXT NOT NULL,
    model_probability REAL,
    fair_odds REAL,
    placed_odds REAL,
    closing_odds REAL,
    edge REAL,
    quarter_kelly REAL,
    paper_units REAL,
    decision TEXT,
    model_trust REAL,
    placed_at TEXT,
    raw_json TEXT
);

CREATE TABLE IF NOT EXISTS clv_snapshots (
    clv_id TEXT PRIMARY KEY,
    bet_id TEXT NOT NULL,
    placed_odds REAL,
    closing_odds REAL,
    clv_ratio REAL,
    clv_percent REAL,
    captured_at TEXT,
    raw_json TEXT
);
"""


def read_closing(path: Path) -> Dict[Tuple[str, str], Dict[str, Any]]:
    out: Dict[Tuple[str, str], Dict[str, Any]] = {}
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[(row["market_id"], row["selection"])] = row
    return out


def load_report(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if "report" in data:
        return data["report"]
    return data


def run(db_path: Path, value_report_path: Path, closing_odds_path: Path, out_path: Path, fixture_id: str) -> dict:
    report = load_report(value_report_path)
    closing = read_closing(closing_odds_path)

    con = sqlite3.connect(str(db_path))
    con.executescript(LEDGER_SCHEMA)
    con.execute("DELETE FROM paper_bets")
    con.execute("DELETE FROM clv_snapshots")

    selections = report.get("selections", [])
    written = 0
    clv_written = 0
    clv_values = []
    paper_only_count = 0

    for idx, sel in enumerate(selections):
        market = sel.get("market_id")
        selection = sel.get("selection")
        decision = str(sel.get("decision", ""))
        if not market or not selection:
            continue
        if sel.get("edge", 0.0) <= 0:
            continue
        close = closing.get((market, selection))
        if not close:
            continue

        paper_only = decision.startswith("PAPER ONLY")
        if paper_only:
            paper_only_count += 1
        placed = float(sel.get("bookmaker_odds"))
        closing_odds = float(close["closing_odds"])
        clv_ratio = placed / closing_odds if closing_odds > 0 else None
        clv_percent = (clv_ratio - 1.0) * 100.0 if clv_ratio is not None else None
        bet_id = f"{fixture_id}:{market}:{selection}:{idx}"
        paper_units = 1.0

        con.execute(
            """INSERT OR REPLACE INTO paper_bets
               (bet_id, fixture_id, market_id, selection, model_probability, fair_odds,
                placed_odds, closing_odds, edge, quarter_kelly, paper_units,
                decision, model_trust, placed_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                bet_id,
                fixture_id,
                market,
                selection,
                sel.get("model_probability"),
                sel.get("fair_odds"),
                placed,
                closing_odds,
                sel.get("edge"),
                sel.get("quarter_kelly"),
                paper_units,
                decision,
                sel.get("model_trust"),
                close.get("captured_at"),
                json.dumps(sel, ensure_ascii=False),
            ),
        )
        written += 1

        clv_id = f"{bet_id}:closing"
        con.execute(
            """INSERT OR REPLACE INTO clv_snapshots
               (clv_id, bet_id, placed_odds, closing_odds, clv_ratio, clv_percent, captured_at, raw_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                clv_id,
                bet_id,
                placed,
                closing_odds,
                clv_ratio,
                clv_percent,
                close.get("captured_at"),
                json.dumps(close, ensure_ascii=False),
            ),
        )
        clv_written += 1
        if clv_percent is not None:
            clv_values.append(clv_percent)

    con.commit()
    paper_count = con.execute("SELECT COUNT(*) FROM paper_bets").fetchone()[0]
    clv_count = con.execute("SELECT COUNT(*) FROM clv_snapshots").fetchone()[0]
    con.close()

    result = {
        "ok": paper_count > 0 and clv_count > 0 and paper_only_count == paper_count,
        "warning": "Paper ledger only. No real-money staking. Uses low-trust model outputs.",
        "db": str(db_path),
        "fixture_id": fixture_id,
        "paper_bets_written": paper_count,
        "clv_rows_written": clv_count,
        "paper_only_bets": paper_only_count,
        "all_paper_only": paper_only_count == paper_count,
        "avg_clv_percent": (sum(clv_values) / len(clv_values)) if clv_values else None,
        "positive_clv_rows": sum(1 for v in clv_values if v > 0),
        "negative_clv_rows": sum(1 for v in clv_values if v < 0),
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if not result["ok"]:
        raise SystemExit(1)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Create paper-betting ledger and CLV report from value output.")
    ap.add_argument("--db", default="../build/omnibet.sqlite")
    ap.add_argument("--value-report", default="../reports/ci_rust_value_report.json")
    ap.add_argument("--closing-odds", default="../data/sample_closing_odds_spain_cape_verde.csv")
    ap.add_argument("--out", default="../reports/ci_paper_ledger.json")
    ap.add_argument("--fixture-id", default="Spain-vs-Cape-Verde")
    args = ap.parse_args()
    run(Path(args.db), Path(args.value_report), Path(args.closing_odds), Path(args.out), args.fixture_id)


if __name__ == "__main__":
    main()
