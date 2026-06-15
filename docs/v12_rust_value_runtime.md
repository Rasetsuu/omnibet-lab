# v12 Rust Value / Bet-Builder Runtime

v11 was mostly correctness cleanup. v12 is a real feature step.

## Fixes

- Fixes the failing `sigmoid_bounds` test from v11.
- Rust package version bumped to `0.12.0`.

## New Rust module

```text
rust-core/src/value.rs
```

## New Rust CLI

```text
rust-core/src/bin/omnibet-value.rs
```

## What it does

Given:

- compressed data pack
- fixture teams
- bookmaker odds CSV

Rust now:

1. Runs model prediction from the compressed pack.
2. Converts market probabilities into fair odds.
3. Reads market prices from CSV.
4. Computes EV/edge.
5. Computes quarter-Kelly.
6. Emits NO BET / VALUE decisions.
7. Builds three prototype bet-builder tickets:
   - Safe Builder
   - Balanced Builder
   - Aggressive Builder

## Command

```bash
cd rust-core

cargo test

cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv
```

## Honesty

This is not betting advice and not bookmaker-grade same-game pricing.

The model is still simple, and correlation risk is heuristic.
The important step is that the runtime now has the complete value-analysis shape.
