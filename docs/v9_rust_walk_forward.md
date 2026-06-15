# v9 Rust Walk-Forward Backtest

v8 proved Rust can read compressed packs and produce a simple prediction.
v9 fixes the next important issue: avoiding self-training.

## Problem in v8

The v8 prediction command used all available matches to build team aggregates.
That is okay as a runtime proof, but it is not a proper evaluation method.

## v9 solution

`omnibet-infer backtest` runs a chronological walk-forward baseline:

1. Sort football matches by date.
2. Train aggregates only on matches before the current test match.
3. Predict the current match.
4. Update history after the match.
5. Compute accuracy, log loss, Brier, Over 2.5 and BTTS metrics.

## Commands

```bash
cd rust-core

cargo test

cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80
cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80 --rows
```

## Honest status

This is still a simple aggregate Poisson baseline, not the final smart model. But now the Rust runtime has the correct evaluation pattern.
