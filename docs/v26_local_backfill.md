# v26 Local-Scale Historical Data Backfill Runner

v26 adds a local-only backfill orchestration layer for larger football data imports while keeping CI small and deterministic.

The goal is not model improvement by itself. The goal is to make the warehouse ready for larger walk-forward, odds/CLV, event, player, lineup, and identity-resolution validation.

## New scripts

```text
python_lab/local_backfill_runner.py
python_lab/backfill_reports.py
```

## CI tiny smoke

CI must remain small and deterministic:

```bash
cd python_lab
python local_backfill_runner.py \
  --preset tiny-smoke \
  --out ../build/v26_smoke \
  --pack-name football_v26_tiny_smoke

python verify_data_pack.py \
  --pack-dir ../build/v26_smoke/packs/football_v26_tiny_smoke
```

The tiny smoke uses only checked-in sample files:

- `data/samples/football_data_odds_sample.csv`
- `data/samples/openfootball_sample.json`
- `data/samples/wyscout_public_sample_matches.json`
- `data/samples/wyscout_public_sample_events.json`

It proves orchestration, coverage reporting, identity candidates, odds snapshots, compressed pack export, and pack verification without downloading large external data.

## Local-scale command shape

Use local paths outside CI:

```bash
cd python_lab
python local_backfill_runner.py \
  --out ../build/local_backfills/v26_run \
  --pack-name football_v26_local_backfill \
  --football-data-dir ../data/external/football-data \
  --statsbomb-dir ../data/external/statsbomb-open-data/data \
  --openfootball-dir ../data/external/openfootball \
  --wyscout-dir ../data/external/wyscout-style \
  --max-files-per-source 0 \
  --max-statsbomb-matches 0
```

You can also pass repeatable explicit files:

```bash
python local_backfill_runner.py \
  --out ../build/local_backfills/v26_manual \
  --football-data-csv ../data/external/football-data/mmz4281/2324/E0.csv \
  --openfootball-json ../data/external/openfootball/worldcup/2026.json \
  --wyscout-matches ../data/external/wyscout/matches.json \
  --wyscout-events ../data/external/wyscout/events.json
```

## Outputs

The runner writes:

```text
build/local_backfills/<run_id>/
  omnibet_v26_backfill.sqlite
  packs/
    <pack_name>/
      manifest.json
      tables/*.jsonl.gz
  reports/
    v26_backfill_manifest.json
    v26_source_coverage_report.json
    v26_identity_coverage_report.json
    v26_event_coverage_report.json
    v26_player_coverage_report.json
    v26_odds_coverage_report.json
    v26_walk_forward_ready_report.json
```

## Coverage reports

The reports answer questions that matter before model work:

- How many normalized matches were imported?
- Which sources contributed matches/events/players/odds?
- What competitions/seasons are present?
- How many identity candidates exist across sources?
- How many matches have event data?
- How many matches have lineup/player data?
- How many matches have odds and closing-odds-like rows?
- Is the warehouse ready for walk-forward odds/CLV validation?

## Storage policy

v26 keeps JSONL.GZ because it is:

- stdlib-only on Python;
- deterministic and CI-friendly;
- already readable/verifiable by the Rust pack runtime;
- good enough for smoke and medium local packs.

For heavy event/player/odds history, the planned v27 storage backend should add Parquet + ZSTD or DuckDB-compatible partitioned tables.

Recommended long-term split:

```text
Bronze: raw source archives / JSON / CSV / JSON.zst
Silver: normalized matches/events/lineups/players/odds, Parquet+ZSTD
Gold: model-ready rolling team/player/market snapshots, Parquet+ZSTD
Runtime: compact Rust-loadable model artifacts + identity/metadata cache
```

## Honesty contract

v26 is `PAPER_ONLY` infrastructure.

It does not claim:

- profitable betting;
- improved accuracy;
- real edge;
- production model readiness.

It only prepares larger, auditable data for later walk-forward and CLV tests.
