# v13 Commands

## Python synthetic event demo

```bash
cd python_lab

python synthetic_event_demo.py \
  --base-db ../build/omnibet.sqlite \
  --demo-db ../build/omnibet_v13_event_demo.sqlite \
  --pack-dir ../data_packs/football_event_demo_v1 \
  --reports-dir ../reports

python verify_data_pack.py --pack-dir ../data_packs/football_event_demo_v1
```

## Rust value report with trust gate

```bash
cd rust-core

cargo test

cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv \
  0.25
```

## Rust pack verify for event demo

```bash
cargo run --bin omnibet-pack -- verify ../data_packs/football_event_demo_v1
```
