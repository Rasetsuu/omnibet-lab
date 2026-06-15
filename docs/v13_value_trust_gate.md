# v13 Value Trust Gate

v12 correctly produced a value report, but the labels were too aggressive.

Problem:

```text
A simple baseline model could output STRONG VALUE.
```

That is dangerous product behavior.

v13 adds `model_trust` gating to the Rust value runtime.

## Default behavior

`omnibet-value` defaults to:

```text
model_trust = 0.25
```

At low trust, selections and tickets are labeled:

```text
PAPER ONLY - model trust too low
```

## Command

```bash
cd rust-core

cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv \
  0.25
```

To simulate a trusted model later:

```bash
cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv \
  0.80
```

The 0.80 mode is only for testing labels. It does not make the model good.
