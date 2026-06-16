# v25 Odds / CLV Walk-Forward Paper Backtest

v25 connects the walk-forward evaluation shape to betting-market reality.

## New script

```text
python_lab/odds_walk_forward_backtest.py
```

## What it does

The CI smoke uses the v23 multi-source warehouse and reads:

- finished matches from `matches_norm`
- 1X2 odds from `odds_snapshots`
- placed odds from Bet365-style columns
- closing odds from Pinnacle/PS-style columns

For each future match after `min_train`, it:

1. builds simple expanding-prior probabilities from past matches only;
2. computes no-vig implied probabilities from placed odds;
3. selects positive-edge paper candidates;
4. settles paper profit/loss from the final score;
5. compares placed odds to closing odds for CLV;
6. writes rows to `paper_backtest_bets`;
7. emits `ci_v25_odds_clv_backtest.json`.

## CI command

```bash
cd python_lab
python odds_walk_forward_backtest.py \
  --db ../build/omnibet_v23_multisource.sqlite \
  --out ../reports/ci_v25_odds_clv_backtest.json \
  --min-train 1 \
  --min-bets 1 \
  --min-edge 0.0
```

## Contract

The report includes:

- market: `football.1x2`
- settlement scope: `regulation_time`
- matches with odds
- paper bets
- wins/losses
- paper profit units
- ROI
- average edge
- average CLV percentage
- paper-only flag
- leakage guard

## Honesty

This is a tiny CI smoke, not betting proof. Its value is structural:

```text
past-only probability estimate + available odds + future settlement + CLV tracking
```

A real v26/v27 pass should run this over larger historical odds data and compare against closing lines at scale.
