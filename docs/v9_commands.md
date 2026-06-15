# v9 Commands

```bash
cd rust-core

cargo test

cargo run --bin omnibet-pack -- verify ../data_packs/football_core_v1
cargo run --bin omnibet-infer -- inspect ../data_packs/football_core_v1 3
cargo run --bin omnibet-infer -- predict ../data_packs/football_core_v1 Spain "Cape Verde"
cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80
```

Include rows:

```bash
cargo run --bin omnibet-infer -- backtest ../data_packs/football_core_v1 80 --rows
```
