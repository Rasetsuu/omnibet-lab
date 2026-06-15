# v12 Next

After v12, the Rust runtime can:

- verify packs
- read typed rows
- infer probabilities
- walk-forward backtest
- compare model paths
- compute value / no-bet / bet-builder tickets

Next meaningful step:

## v13

Start importing real event data:

- StatsBomb Open Data local import smoke
- populate `match_events`
- populate `lineups`
- build `gold_goal_timing_features`
- run first goal-timing report with non-zero rows

This would finally expand the data detail level beyond match summaries.
