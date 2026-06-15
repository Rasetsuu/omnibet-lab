# Rust Migration Plan v6

The project is still proof-of-concept, so Python is correct for research. But the final engine should move stable parts to Rust.

## Keep Python for now

- model research
- training experiments
- source discovery
- notebooks
- calibration experiments
- fast iteration

## Move to Rust when stable

- odds conversion
- overround removal
- EV/Kelly
- data-pack manifest verification
- data-pack reading
- entity resolution once rules stabilize
- feature extraction once schema stabilizes
- Poisson/Dixon-Coles inference
- bet-builder scoring
- Tauri backend commands

## Rust benefits

Rust does not magically increase prediction accuracy. It improves:

- memory safety
- deterministic execution
- speed
- lower memory usage
- safer concurrency
- better error handling
- stronger schema discipline

That indirectly improves reliability because fewer data bugs/leakage bugs reach the model.

## Current Rust skeleton

`rust-core/src/lib.rs` now defines:

- Match
- Team
- Player
- MatchEvent
- OddsSnapshot
- Prediction
- MarketDefinition
- DataPackManifest
- odds/EV/Kelly helpers
- overround removal helper
