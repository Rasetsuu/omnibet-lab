# Storage and Compression v6

The long-term OmniBet database can become huge when we track:

- every match
- every event
- every shot
- every card
- every pass/corner/offside
- every lineup/substitution
- every player snapshot
- every odds movement
- every live update

## Rule

Do not store everything forever as one giant SQLite database.

## Layered storage

```text
SQLite
  source registry
  update runs
  app settings
  recent cache
  small indexes

Compressed data packs
  historical matches
  events
  lineups
  player snapshots
  odds snapshots

Gold features
  regenerated cache, optionally packed
```

## Current v6 format

Dependency-free fallback:

```text
JSONL.GZ + manifest.json
```

This is not the final best compression, but it is portable and verifiable.

## Future preferred format

```text
Parquet + ZSTD
```

Why:

- columnar compression is much better for sports datasets
- queries only read needed columns
- ZSTD is fast and strong
- DuckDB/Polars/Rust readers can handle it well

## Pack strategy

Do not ship all sports and seasons by default.

Use packs like:

```text
football_core_results_europe_2010_2026
football_events_statsbomb_open
football_odds_major_leagues_2010_2026
football_players_transfermarkt_import
nba_core_2007_2026
nba_player_props_2015_2026
```

Users install what they need.
