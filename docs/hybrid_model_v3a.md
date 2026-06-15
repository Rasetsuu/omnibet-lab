# OmniBet Lab v3A Hybrid Model

v3A adds a first hybrid accuracy layer.

## Model idea

```text
Rolling Poisson score features
+ rolling team form/stats
+ rank priors
+ logistic classification layer
+ simple shrink calibration
= calibrated match-market probabilities
```

## Why not jump straight to deep learning?

The dataset currently has only a few hundred international matches. A larger neural network can easily overfit. v3A uses simple, stable models first and measures them honestly with walk-forward validation.

## Markets

v3A trains/evaluates:

- 1X2 outcome
- Over 2.5 goals
- BTTS

v3B should add:

- corners
- cards
- team goals
- handicap/Asian handicap
- same-game bet-builder combinations

## Calibration

v3A uses a simple shrink calibration:

```text
p_calibrated = (1 - alpha) * p_model + alpha * p_base_rate
```

This is intentionally easy to port to Rust/C++ later and safer on small datasets than overfit calibration models.
