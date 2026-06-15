# v7 Rust Engine Scope

v7 is not a full rewrite. It is the first Rust runtime boundary.

## Already in Rust

- schema structs
- odds math
- overround removal
- EV/Kelly
- data-pack manifest structs
- data-pack verification
- compressed table row reader

## Still in Python

- ingestion experiments
- feature engineering research
- training
- model comparison
- data-source discovery

## Next Rust targets

1. Typed row deserialization for `matches_norm`
2. typed row deserialization for `gold_match_features`
3. Rust Poisson/Dixon-Coles inference over gold features
4. Rust bet-builder scoring over model outputs
5. Tauri commands wrapping the Rust core
