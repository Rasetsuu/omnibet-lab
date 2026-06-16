# v22 Trained Model Export

v22 adds the first Python training/export step that produces a compact model artifact consumed by Rust.

## New script

```text
python_lab/train_linear_model.py
```

## What it trains

A small multinomial logistic model for:

```text
market: football.1x2
settlement_scope: regulation_time
phase_scope: regulation halves + regulation stoppage
```

The training script uses only Python stdlib and the existing SQLite gold features.

## Output artifact

```text
build/models/football_regulation_linear_trained_v1.json
```

The artifact contains:

- model name/version
- sport
- target market
- settlement scope
- phase scope
- model trust
- classes
- intercept
- feature paths
- weights
- calibration shrink
- training metadata

## Rust verification

CI runs:

```bash
cd rust-core
cargo run --bin omnibet-model -- backtest \
  ../data_packs/football_phase_training_v1 \
  ../build/models/football_regulation_linear_trained_v1.json \
  1
```

This proves that Rust can load and evaluate the Python-exported artifact.

## Honesty

This is a training/export contract milestone, not a betting-edge proof. The CI dataset is intentionally small. The exported model remains `PAPER_ONLY` by low `model_trust`.
