# v11 Aligned Rust Comparison

v10 compiled and ran on the user's machine, but exposed two cleanup issues:

1. `src/gold_model.rs` had an unused `json` import warning.
2. `compare` was not apples-to-apples:
   - baseline tested 221 matches after `min_train=80`
   - gold-feature heuristic tested all 301 matches with `min_train=0`

v11 fixes both.

## Fixes

- Removed the unused Rust import warning.
- `backtest-gold` now accepts `min_train`.
- `compare` now passes the same `min_train` to both models.
- `ModelComparison` now reports `aligned_test_window`.

## Commands

```bash
cd rust-core

cargo test
cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80
cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1 80
cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80
```

## Expected

`compare` should show both models testing the same number of matches. With the current pack, that should be 221.
