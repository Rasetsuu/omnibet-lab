# TheStatsAPI Adapter v4

TheStatsAPI is now a first-class planned source in OmniBet.

## Environment

```bash
export THESTATSAPI_KEY="your_key_here"
```

## Commands

```bash
cd python_lab

# Check source registration and key presence
python -m adapters.thestatsapi_adapter status --db ../build/omnibet.sqlite

# Fetch one endpoint into bronze storage
python -m adapters.thestatsapi_adapter get \
  --endpoint /competitions \
  --entity-type competitions \
  --db ../build/omnibet.sqlite

# Paginated competition sync
python -m adapters.thestatsapi_adapter sync-competitions \
  --db ../build/omnibet.sqlite \
  --limit-pages 2

# Paginated match sync
python -m adapters.thestatsapi_adapter sync-matches \
  --db ../build/omnibet.sqlite \
  --competition-id YOUR_COMPETITION_ID \
  --season-id YOUR_SEASON_ID \
  --limit-pages 2
```

## Safety

- No API call runs without explicit command + key.
- Raw JSON is stored in `bronze_blobs`.
- Endpoint schemas should be observed with real payloads before aggressive normalization.
- Scheduler must respect rate limits and monthly request budgets.
