# Rust Pack Reader v7

v7 adds the first real Rust-side compressed data-pack reader.

## New Rust modules

```text
rust-core/src/schema.rs
rust-core/src/odds.rs
rust-core/src/pack.rs
rust-core/src/bin/omnibet-pack.rs
```

## What the Rust pack reader can do

- load `manifest.json`
- parse table metadata
- verify SHA256 for `.jsonl.gz` table files
- count decompressed JSONL rows
- compare row counts to manifest
- print pack summary
- print first N rows from a table

## Commands

If Rust is installed:

```bash
cd rust-core
cargo test

cargo run --bin omnibet-pack -- verify ../data_packs/football_core_v1
cargo run --bin omnibet-pack -- summary ../data_packs/football_core_v1
cargo run --bin omnibet-pack -- head ../data_packs/football_core_v1 matches_norm 3
```

## Why this matters

This is the start of moving stable runtime logic out of Python and into Rust.

Python still creates the pack in v7, but Rust can now validate and read it.
