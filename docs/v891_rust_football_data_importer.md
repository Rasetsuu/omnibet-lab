# v891-v920 Rust Football-Data importer foundation

This milestone starts the Rust-first historical data spine from issue #192.

## Purpose

The importer reads offline Football-Data style CSV files and writes deterministic local canonical outputs:

- `matches.jsonl`
- `odds.jsonl`
- `import_report.json`

It is intentionally historical/offline only. It does not call live providers, does not persist credentials, and does not unlock real training by itself.

## Current product rule

The importer may make a batch ready for feature building, but the app must still rely on the later feature-count and evaluation gates before it claims model readiness.

`ready_for_training` stays `false` in the v891 report.

## Supported first-pass fields

Required match columns:

- `Date`
- `HomeTeam`
- `AwayTeam`
- `FTHG`
- `FTAG`

Optional match columns:

- `Time`
- `FTR`
- `HTHG`
- `HTAG`
- `HTR`

Supported odds families in this first pass:

- `1x2` regulation 90 scope
- `total_goals_2_5` regulation 90 scope

The importer recognizes common Football-Data bookmaker columns such as Bet365, Pinnacle, William Hill, Victor Chandler, market average/max, and their closing variants when present.

## CLI

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-football-data-importer -- \
  --input data/local_historical/football_data/raw/england/2024_2025/E0.csv \
  --competition england_premier_league \
  --season 2024_2025 \
  --out data/local_historical/football_data/normalized/england_premier_league/2024_2025
```

Outputs are local files only.

## Acceptance

- Rust module and CLI exist.
- Tiny fixture-style tests cover match rows, odds rows, duplicate rows, incomplete rows, and missing required columns.
- No Python is required for the importer.
- No model/training claims are introduced.
