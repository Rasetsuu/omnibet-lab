# v8 Commands

## Re-export pack with fixed empty-table ratios

```bash
cd python_lab
python export_data_pack.py --db ../build/omnibet.sqlite --out-dir ../data_packs/football_core_v1
python verify_data_pack.py --pack-dir ../data_packs/football_core_v1
```

## Rust pack + inference

```bash
cd rust-core

cargo test

cargo run --bin omnibet-pack -- verify ../data_packs/football_core_v1
cargo run --bin omnibet-pack -- summary ../data_packs/football_core_v1
cargo run --bin omnibet-pack -- head ../data_packs/football_core_v1 matches_norm 3

cargo run --bin omnibet-infer -- inspect ../data_packs/football_core_v1 3
cargo run --bin omnibet-infer -- predict ../data_packs/football_core_v1 Spain "Cape Verde"
```
