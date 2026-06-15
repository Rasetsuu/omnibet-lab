# Warehouse Schema v4

v4 creates the first serious normalized data warehouse.

## Metadata

- `source_registry`
- `update_runs`
- `adapter_watermarks`
- `raw_source_blobs`
- `bronze_blobs`

## Normalized football/NBA-ready tables

- `competitions`
- `seasons`
- `teams`
- `players`
- `matches_norm`
- `match_events`
- `lineups`
- `odds_snapshots`

## Why bronze/silver/gold

### Bronze

Store raw API/CSV payloads unchanged. This allows audit/rebuilds.

### Silver

Normalize source-specific data into shared tables.

### Gold

Build model-ready snapshots with no leakage.

## Performance

SQLite is enough for the current prototype and millions of summary rows. For event/player scale, v5/v6 should add DuckDB + Parquet for analytics and keep SQLite for app metadata/cache.
