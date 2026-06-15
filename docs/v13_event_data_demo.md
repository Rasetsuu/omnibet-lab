# v13 Event Data Demo

v13 finally activates event/player/goal-timing tables.

The normal football core pack remains match-summary data.

v13 adds a separate synthetic/public-safe demo:

```text
build/omnibet_v13_event_demo.sqlite
data_packs/football_event_demo_v1/
reports/v13_synthetic_event_pipeline.json
```

## Why synthetic?

The project should not fake real event intelligence before real data is imported.

Synthetic data is used only to prove the pipeline shape:

```text
matches_norm
  -> match_events
  -> lineups
  -> gold_goal_timing_features
  -> gold_player_snapshots
  -> compressed event demo pack
```

## v13 demo results

```text
matches_norm: 305
match_events: 35
lineups: 18
teams: 4
players: 9
gold_goal_timing_features: 4
gold_player_snapshots: 9
```

Goal timing demo:

```text
matches: 4
avg first goal minute: 19.5
first-half goals: 5
second-half goals: 7
second-half goal share: 58.33%
```

## Command

```bash
cd python_lab

python synthetic_event_demo.py \
  --base-db ../build/omnibet.sqlite \
  --demo-db ../build/omnibet_v13_event_demo.sqlite \
  --pack-dir ../data_packs/football_event_demo_v1 \
  --reports-dir ../reports

python verify_data_pack.py --pack-dir ../data_packs/football_event_demo_v1
```

## Warning

This data is synthetic and public-safe. It is not predictive real-world data.
