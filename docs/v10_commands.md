# v10 Commands

```bash
cd rust-core

cargo test

# Baseline raw-match aggregate walk-forward
cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80

# Gold-feature heuristic backtest
cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1

# Compare baseline vs gold-feature heuristic
cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80
```
