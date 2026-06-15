# v14 Public Event Sample

v14 adds a real public-data validation path for the existing StatsBomb adapter.

## Goal

Prove that real event-data shaped like StatsBomb Open Data can feed the same pipeline that v13 proved with synthetic demo rows.

## Pipeline

```text
public event JSON sample
  -> statsbomb_open_adapter
  -> SQLite warehouse
  -> gold_feature_builder
  -> goal_timing_lab
  -> player_score_lab
  -> compressed data pack
```

## Outputs

```text
build/omnibet_v14_statsbomb_sample.sqlite
data_packs/football_statsbomb_sample_v1/
reports/v14_statsbomb_public_sample.json
```

## Command

```bash
cd python_lab

python statsbomb_public_sample.py \
  --sample-root ../data/statsbomb_public_sample/data \
  --db ../build/omnibet_v14_statsbomb_sample.sqlite \
  --pack-dir ../data_packs/football_statsbomb_sample_v1 \
  --reports-dir ../reports \
  --limit-matches 3

python verify_data_pack.py --pack-dir ../data_packs/football_statsbomb_sample_v1
```

## CI contract

The v14 CI summary requires the public sample to produce non-zero:

- `matches_norm`
- `match_events`
- `lineups`
- `players`
- `gold_goal_timing_features`
- `gold_player_snapshots`

This is not a full data mirror and not a model breakthrough by itself. It proves the real public event-data adapter can activate the detailed-data pipeline.
