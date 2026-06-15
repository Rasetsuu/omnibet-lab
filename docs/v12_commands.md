# v12 Commands

```bash
cd rust-core

cargo test

cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80

cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv
```
