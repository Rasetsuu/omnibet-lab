# v11 Commands

```bash
cd rust-core

cargo test

cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80
cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1 80
cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80
```

Optional row dump:

```bash
cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1 80 --rows
```
