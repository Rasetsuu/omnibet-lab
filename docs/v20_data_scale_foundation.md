# v20 Data Scale Foundation

v20 starts the real data-scale chapter.

The project already had compressed JSONL.GZ packs and Rust verification. v20 adds a configurable StatsBomb public-data pipeline so we can move beyond tiny fixed samples without changing the core storage contract.

## New script

```text
python_lab/statsbomb_scale_pipeline.py
```

## Profiles

### Smoke profile

Used by CI. Small, deterministic, compression-verified.

```bash
cd python_lab
python statsbomb_scale_pipeline.py \
  --profile smoke \
  --max-matches 16 \
  --pack-name football_statsbomb_scale_v1
```

### Medium profile

For local bigger testing.

```bash
cd python_lab
python statsbomb_scale_pipeline.py \
  --profile medium \
  --max-matches 100 \
  --max-competitions 3 \
  --pack-name football_statsbomb_medium_v1
```

### Full profile

For local full public import. This is intentionally not run in CI.

```bash
cd python_lab
python statsbomb_scale_pipeline.py \
  --profile full \
  --max-matches 0 \
  --max-competitions 0 \
  --pack-name football_statsbomb_full_v1 \
  --pack-dir ../data_packs/football_statsbomb_full_v1 \
  --db ../build/omnibet_statsbomb_full.sqlite \
  --report-name v20_statsbomb_full.json
```

## What it produces

- source slice manifest
- SQLite warehouse
- gold features
- goal timing features
- player snapshots
- compressed JSONL.GZ data pack
- quality report
- storage plan

## Compression strategy

Current stable pack format remains:

```text
JSONL.GZ + manifest.json
```

This is good for CI and Rust verification. For very large local data, the planned next storage layer is:

```text
Parquet + ZSTD or DuckDB external tables
```

SQLite should remain metadata/cache/recent-state, not the giant historical lake.

## CI contract

CI now verifies:

- v20 scale pack exports successfully;
- v20 scale pack verifies with Python;
- v20 scale pack verifies with Rust;
- rows/events/lineups/players/compressed bytes are non-zero;
- all previous v14-v19 gates remain green.
