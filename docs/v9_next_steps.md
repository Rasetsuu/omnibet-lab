# v9 Next Steps

After v9, the Rust engine has:

- compressed pack verification
- typed table readers
- simple prediction
- chronological walk-forward backtest

Next useful steps:

## v10

Port more of the Python hybrid logic into Rust:

- rolling team snapshots from `gold_match_features`
- use feature JSON instead of raw match-only aggregates
- add calibration shrink
- compare Rust baseline vs Python hybrid

## v11

Connect Rust inference to bet-builder:

- generate legs
- fair odds
- EV/Kelly
- no-bet logic
- correlation risk

## v12

Only after stable engine:

- wire Tauri buttons to Rust commands
- pack summary UI
- match selector
- prediction card
- bet-builder panel
