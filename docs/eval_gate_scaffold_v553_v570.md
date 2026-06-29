# v553-v570 Eval Gate Scaffold

This phase adds a gate between completed result rows and future engine work.

## Inputs

```text
configs/world_cup_result_ingest.v543_v552.json
tauri-app/src/world-cup-fixtures.local.json
data/world_cup/v543_v552/world_cup_results.local.json
```

## Outputs

```text
reports/ci_v553_v570_eval_gate_scaffold.json
reports/model_status_v553_v570.json
reports/feature_family_manifest_v553_v570.json
```

## Gates

```text
minimum settled rows: 200
minimum distinct teams: 20
minimum competitions: 3
minimum chronological splits: 3
label timestamps must be after kickoff
```

## Expected current status

```text
settled_rows = 1
ready_for_real_model = false
status = blocked_insufficient_settled_rows
```

This is correct. One settled row is enough for a smoke preview, not enough for a useful engine.

## Feature families

```text
fixture result and goals: candidate preview available
corners/cards/set pieces: locked until event data exists
player markets: locked until lineups and player events exist
market value: locked until opening and closing price data exists
```

## Next

```text
v571-v590 historical data source expansion
v591-v620 train/eval runner after enough rows exist
v621-v650 Rust runtime migration for stable pieces
```
