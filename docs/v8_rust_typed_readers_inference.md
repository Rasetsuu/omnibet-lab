# v8 Rust Typed Readers and First Inference

v8 fixes one v7 issue and adds the next Rust runtime step.

## Fix

Empty tables no longer report nonsense compression ratios like `44.0`.
For empty exported tables, `compression_ratio` is now `null`.

## New Rust modules

```text
rust-core/src/typed_rows.rs
rust-core/src/inference.rs
rust-core/src/bin/omnibet-infer.rs
```

## Typed readers

Rust can now deserialize:

- `matches_norm`
- `gold_match_features`

from the compressed `JSONL.GZ` pack.

## First Rust inference

The new CLI runs a simple aggregate Poisson model directly over `matches_norm` rows read from the compressed pack.

This is **not the final model**. It is a runtime proof:

```text
compressed pack -> Rust reader -> typed rows -> simple inference -> JSON output
```

## Commands

```bash
cd rust-core

cargo test

cargo run --bin omnibet-pack -- verify ../data_packs/football_core_v1
cargo run --bin omnibet-pack -- summary ../data_packs/football_core_v1

cargo run --bin omnibet-infer -- inspect ../data_packs/football_core_v1 2
cargo run --bin omnibet-infer -- predict ../data_packs/football_core_v1 Spain "Cape Verde"
```

## Honest status

- The data-pack reader was proven by the user locally in v7.
- v8 source adds typed readers/inference.
- If this environment has no Cargo, local user-side Cargo validation is still required.
