# v10 Next

v10 proves Rust can evaluate `gold_match_features`.

Next likely steps:

## v11

Add Rust odds/value/bet-builder runtime:

- read model probabilities
- generate supported market legs
- compute fair odds
- match bookmaker odds from `odds_snapshots`
- EV/Kelly/no-bet
- correlation-risk logic

## v12

Add real data import validation:

- StatsBomb event import
- TheStatsAPI endpoint schema capture
- first event rows in `match_events`
- first goal timing rows in `gold_goal_timing_features`

## v13

Only then start wiring Tauri to Rust.
