# v28 Real-Source Acquisition Catalog

v28 turns the data-source discussion into a repo-owned, CI-checked source catalog.

The goal is to grow OmniBet beyond tiny bundled samples without committing large datasets or requiring paid API keys in CI.

## New script

```text
python_lab/source_acquisition_catalog.py
```

CI-safe command:

```bash
cd python_lab
python source_acquisition_catalog.py \
  --out ../reports/ci_v28_source_catalog.json \
  --write-example-config ../configs/source_acquisition.v28.example.json \
  --write-shell-plan ../build/v28_sync_sources_plan.sh
```

This writes a deterministic report and local sync skeleton. It does **not** download data in CI.

## Sources in v28 catalog

### StatsBomb Open Data

Use for:

```text
events
lineups
players through event/lineup references
selected StatsBomb 360 freeze-frame data
competition/season metadata
```

Local sync shape:

```bash
git clone https://github.com/statsbomb/open-data.git data/external/statsbomb-open-data
```

v26 backfill argument:

```bash
--statsbomb-dir data/external/statsbomb-open-data/data
```

### Football-Data.co.uk

Use for:

```text
historical results
match stats
bookmaker odds columns
closing/opening odds where columns exist
league/season CSV files
```

Local policy: download selected CSVs manually or with a future careful downloader into:

```text
data/external/football-data/
```

v26 backfill argument:

```bash
--football-data-dir data/external/football-data
```

### OpenFootball World Cup / football.db

Use for:

```text
public-domain fixture/result spine
World Cup historical fixtures/results
World Cup 2026 fixture/group structure
qualifier/result text data where available
```

Local sync shape:

```bash
git clone https://github.com/openfootball/worldcup.git data/external/openfootball/worldcup
```

v26 backfill argument:

```bash
--openfootball-dir data/external/openfootball
```

### The Odds API

Use later for:

```text
live odds
historical odds snapshots
historical event IDs
player props / alternate / period markets where supported
```

This is disabled by default because historical odds are paid/API-key based. Do not require this in CI.

Future env shape:

```bash
export THE_ODDS_API_KEY=...
```

v26 reserved argument:

```bash
--odds-dir data/external/the-odds-api
```

## Local workflow after v28

1. Generate catalog and sync skeleton:

```bash
cd python_lab
python source_acquisition_catalog.py \
  --out ../reports/v28_source_catalog_local.json \
  --local-root ../data/external \
  --write-shell-plan ../build/v28_sync_sources_plan.sh
```

2. Review the shell plan, source terms, and disk use.

3. Sync free/open sources:

```bash
bash build/v28_sync_sources_plan.sh
```

4. Add Football-Data CSV files manually under:

```text
data/external/football-data/
```

5. Run v26 local backfill:

```bash
cd python_lab
python local_backfill_runner.py \
  --out ../build/local_backfills/v28_real_sources \
  --pack-name football_v28_real_sources \
  --football-data-dir ../data/external/football-data \
  --statsbomb-dir ../data/external/statsbomb-open-data/data \
  --openfootball-dir ../data/external/openfootball
```

6. Export Parquet+ZSTD after backfill:

```bash
python export_parquet_zstd_pack.py \
  --db ../build/local_backfills/v28_real_sources/omnibet_v26_backfill.sqlite \
  --out-dir ../build/local_backfills/v28_real_sources/parquet_zstd_pack \
  --pack-name football_v28_real_sources_parquet_zstd \
  --zstd-level 6
```

## Git policy

Commit:

```text
scripts
docs
small deterministic samples
manifests/reports from CI
```

Do not commit:

```text
full raw source mirrors
large Parquet packs
paid API responses
API keys
local data_lake outputs
```

## Relationship to open issues

v28 supports the phase-aware modeling issue by identifying sources that can provide period labels, lineups, events, and settlement-context inputs. It does not solve phase-aware modeling by itself.

## Honesty

v28 is acquisition infrastructure only.

No model-quality, betting-profit, or live-betting claims are made.
