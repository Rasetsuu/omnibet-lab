# v10 Rust Gold Feature Model

v9 added chronological Rust walk-forward over raw match aggregates.

v10 adds a second Rust evaluation path over `gold_match_features`.

## Why

The final engine should not only read raw match rows. It should also use the gold feature layer:

- rolling goals for/against
- rolling points/form
- rest days
- xG/shots/cards/corners when event data exists
- leakage-safe feature snapshots

## New Rust module

```text
rust-core/src/gold_model.rs
```

## New commands

```bash
cargo run --bin omnibet-infer -- backtest-gold ../data_packs/football_core_v1
cargo run --bin omnibet-infer -- compare ../data_packs/football_core_v1 80
```

## What it is

A Rust heuristic model over gold features.

## What it is not

It is not trained ML yet. It is the bridge step:

```text
compressed pack
  -> typed Rust gold feature rows
  -> feature JSON parsing
  -> heuristic probabilities
  -> backtest metrics
```

The next step is replacing this heuristic with a learned/calibrated Rust model or loading exported model weights.
