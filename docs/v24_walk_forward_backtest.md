# v24 Walk-Forward Backtest

v24 adds the first no-future-leak walk-forward training/evaluation loop.

## New/updated file

```text
python_lab/walk_forward_backtest.py
```

## What it does

For each test step, the script:

1. sorts matches by `match_date, match_id`;
2. trains only on rows before the test match;
3. tests on the next future match;
4. repeats with an expanding past-only window;
5. compares against an expanding prior baseline.

## CI command

```bash
cd python_lab
python walk_forward_backtest.py \
  --db ../build/omnibet_v20_statsbomb_scale.sqlite \
  --out ../reports/ci_v24_walk_forward.json \
  --min-train 6 \
  --min-test-rows 4 \
  --model-trust 0.35
```

## Contract

The report includes:

- target market: `football.1x2`
- settlement scope: `regulation_time`
- phase scope: regulation halves and regulation stoppage
- rows tested
- walk-forward accuracy/log-loss/brier
- expanding-prior baseline accuracy/log-loss/brier
- deltas against baseline
- leakage guard metadata

## Honesty

This is a small CI smoke, not model proof. Its value is that it enforces the evaluation shape we need for larger data:

```text
past-only training -> next-match future test
```

That is the first serious step before scaled historical training and odds/CLV evaluation.
