# v16 Rust Linear Model Runtime

v16 adds the first model representation that Rust can load from JSON and evaluate directly over compressed `gold_match_features` packs.

## New files

```text
models/football_event_linear_v1.json
rust-core/src/linear_model.rs
rust-core/src/bin/omnibet-model.rs
```

## Command

```bash
cd rust-core

cargo run --bin omnibet-model -- backtest \
  ../data_packs/football_statsbomb_sample_v1 \
  ../models/football_event_linear_v1.json \
  1
```

## What it does

The model JSON contains:

- class names: `H`, `D`, `A`
- feature paths into `features_json`
- fallback paths into home/away snapshots
- intercepts
- weights
- calibration shrink toward base probabilities
- model trust

Rust loads this JSON and runs:

```text
compressed StatsBomb sample pack
  -> gold_match_features rows
  -> model JSON feature extraction
  -> logits
  -> softmax
  -> calibration shrink
  -> backtest metrics
```

## Honesty

The included model is hand-authored, not trained. Its `model_trust` is intentionally low, and CI requires `trust_decision = PAPER_ONLY`.

This is a runtime milestone, not a proof of betting edge.
