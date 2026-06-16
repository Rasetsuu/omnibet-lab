# v27 Parquet + ZSTD Storage Scale Path

v27 adds the first optional Parquet+ZSTD local warehouse pack path.

The important split:

```text
CI / smoke / Rust-pack baseline:
  JSONL.GZ remains the default deterministic pack.

Local heavy historical warehouse:
  Parquet + ZSTD becomes the preferred analytical storage format.
```

This avoids breaking the existing Rust pack reader while giving local-scale imports a storage format that can handle event, player, lineup, odds, and market-history data.

## Why Parquet + ZSTD

Parquet is columnar. Football/event/odds data has many repeated categorical columns:

```text
sport
competition_id
season_id
team_id
player_id
event_type
period
market_id
bookmaker
selection
source_id
```

Columnar encoding plus dictionary/RLE and ZSTD compression should beat row-oriented JSONL for larger normalized data, while staying queryable from DuckDB, Polars, PyArrow, and future Rust readers.

## Optional dependency policy

The normal CI harness must not depend on heavy analytics packages.

Install optional storage dependencies locally only when you want to export/query heavy packs:

```bash
python -m pip install -r requirements-storage.txt
```

## CI-safe plan check

Dependency-free plan mode inspects the SQLite warehouse and reports what would be exported:

```bash
cd python_lab
python export_parquet_zstd_pack.py \
  --plan-only \
  --db ../build/v26_smoke/omnibet_v26_backfill.sqlite \
  --out ../reports/ci_v27_parquet_zstd_plan.json
```

This mode is safe for CI because it does not require PyArrow.

## Local Parquet+ZSTD export

After running a v26 local backfill, export a Parquet+ZSTD pack:

```bash
cd python_lab
python export_parquet_zstd_pack.py \
  --db ../build/local_backfills/v26_run/omnibet_v26_backfill.sqlite \
  --out-dir ../build/local_backfills/v26_run/parquet_zstd_pack \
  --pack-name football_v27_local_parquet_zstd \
  --zstd-level 6 \
  --row-group-size 100000
```

Check it:

```bash
python check_parquet_pack.py \
  --pack-dir ../build/local_backfills/v26_run/parquet_zstd_pack
```

## ZSTD level policy

Recommended defaults:

```text
level 1-3:
  fast iteration, bigger files

level 6:
  default balance for OmniBet local packs

level 9-15:
  archival/high compression, slower writes
```

Start with level 6. Use higher only after measuring on real data.

## Planned storage layout

v27 still writes a simple one-file-per-table pack:

```text
parquet_zstd_pack/
  manifest.json
  tables/
    matches_norm.parquet
    match_events.parquet
    lineups.parquet
    players.parquet
    odds_snapshots.parquet
```

Future v28/v29 storage work should move heavy tables into partitioned layout:

```text
data_lake/
  football/
    bronze/
      source=statsbomb_open/...
    silver/
      matches/source=.../season=.../*.parquet
      events/source=.../competition=.../season=.../*.parquet
      lineups/source=.../season=.../*.parquet
      odds/source=.../market=.../season=.../*.parquet
    gold/
      match_features/market=1x2_regulation/schema=v1/*.parquet
      player_snapshots/schema=v1/*.parquet
      lineup_snapshots/schema=v1/*.parquet
```

## Runtime policy

The desktop app should not ship the full raw warehouse.

Runtime artifacts should be small:

```text
model.omnimodel.zst
identity_maps.json.zst
feature_normalization.json.zst
market_registry.json
recent/live cache SQLite
```

The large Parquet+ZSTD warehouse is for local training, auditing, and backtesting.

## Honesty

v27 is a storage-scale milestone only.

It does not claim:

- model accuracy improvement;
- betting profit;
- player-prop readiness;
- live-betting readiness.

It gives us the storage format needed before those things can be tested honestly.
