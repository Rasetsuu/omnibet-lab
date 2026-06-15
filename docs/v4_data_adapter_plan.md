# OmniBet Lab v4 Data Adapter Plan

v4 starts the real data-ingestion layer.

## Why this matters

Prediction accuracy will not improve from GUI work alone. The real jump comes from better data:

- larger historical match database
- closing/opening odds
- match stats
- xG
- lineups
- event timing
- player-level history
- live fixtures and live odds

## Source roles

### TheStatsAPI

First-class football API source for:

- fixtures/results
- match stats/events
- player stats
- xG
- lineups/squads
- pre-match odds
- historical odds
- live odds and live stats

The adapter is API-key gated through `THESTATSAPI_KEY`.

### Football-Data.co.uk

Best free-ish batch/backfill source for:

- historical league results
- odds
- common match stats
- closing-line style benchmarks

### StatsBomb Open Data

Best event/player modelling research source:

- events
- lineups
- shots/xG
- match-level event timestamps

### The Odds API

Multi-sport live/upcoming odds and scores.

### nba_api

NBA-specific data adapter, separate model family.

## Architecture

```text
source registry
    ↓
bronze raw JSON/CSV
    ↓
silver normalized tables
    ↓
gold feature snapshots
    ↓
models / bet-builder / Tauri GUI
```

## Rule

Never train directly from raw API payloads. Always preserve raw data, normalize, then build leakage-safe feature snapshots.
