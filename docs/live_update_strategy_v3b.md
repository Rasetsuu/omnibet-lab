# Live / Scheduled Database Update Strategy

Long-term OmniBet must keep itself updated. The app needs a source registry, update logs, and quota-aware adapters.

## Source types

### Football batch data

Football-Data.co.uk is suitable for batch CSV updates/backfills. It provides long-running results, odds, and major league match statistics. It should be used for historical match/odds imports.

### Football event data

StatsBomb Open Data is suitable for event/player modelling research: competitions, matches, events, lineups, and 360 data where available.

### Live/upcoming odds

The Odds API is suitable for live/upcoming events, odds, scores, event markets, and participants. It requires an API key and quota tracking.

### NBA

`nba_api` is suitable for NBA.com stats and live scoreboard access. It should be a separate NBA adapter and model family.

## Local architecture

```text
source_registry
update_runs
raw_source_blobs
        ↓
bronze/raw storage
        ↓
silver normalized tables
        ↓
gold feature snapshots
        ↓
models / predictions / bet builder
```

## Update rules

- Do not mutate model-ready features directly from API responses.
- Always keep raw source blobs or raw files for audit/rebuild.
- Every update must log source, time, rows seen, rows inserted, rows updated, and errors.
- API adapters must be quota-aware and backoff on rate limits.
- Live odds and live scores should update more often than historical results.
- Training should not happen on every live update; use scheduled retraining.

## Commands

```bash
cd python_lab
python live_update_manager.py init --db ../build/omnibet.sqlite
python live_update_manager.py status --db ../build/omnibet.sqlite
python live_update_manager.py write-source-config --out ../config/source_registry.template.json
python live_update_manager.py import-local-football-csv --db ../build/omnibet.sqlite --csv ../data/unified_intl_matches.csv
```
