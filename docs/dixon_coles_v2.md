# Dixon-Coles v2 notes

This pass adds `python_lab/dixon_coles_lab.py`, a transparent Python/SciPy implementation of a Dixon-Coles goal model.

## Why Dixon-Coles?

A vanilla Poisson football model assumes independent team goal counts. That is a useful baseline, but it often mishandles low-score outcomes such as 0-0, 1-0, 0-1, and 1-1. Dixon-Coles adds a low-score correction parameter `rho` to improve those areas.

## What v2 implements

- Attack and defense parameters per team.
- Global goal intercept.
- Home advantage parameter.
- Dixon-Coles low-score correction `rho`.
- L2 regularization.
- Exponential time weighting.
- Holdout backtest.
- Walk-forward backtest.
- Single-match prediction mode.
- Optional saving of model run metrics into SQLite.

## Smoke-test results

Generated reports are stored in `reports/`:

- `v2_feature_store_init.json`
- `v2_dixon_holdout.json`
- `v2_dixon_walk_forward.json`
- `v2_sample_prediction_spain_cape_verde.json`

Observed walk-forward result on the bundled 301-match dataset:

```text
matches: 221
1x2_accuracy: ~44.8%
over25_accuracy: ~53.8%
log_loss: ~1.109
brier_1x2: ~0.648
```

This is not yet a strong betting edge. It is a more serious baseline and gives us the correct structure for honest testing.

## Next accuracy work

- Tune `xi`, `l2`, and `rho` constraints by walk-forward log loss, not raw accuracy.
- Add team-rank/Elo priors as shrinkage rather than as a post-hoc multiplier.
- Add rolling feature models for corners/cards/shots.
- Add calibration curves and probability bins.
- Compare Poisson vs Dixon-Coles vs bivariate Poisson under identical walk-forward splits.
