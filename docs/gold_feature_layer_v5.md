# OmniBet Lab v5 Gold Feature Layer

v5 converts normalized warehouse tables into model-ready features.

## Input tables

- `matches_norm`
- `match_events`
- `lineups`
- `odds_snapshots`

## Output tables

- `gold_team_snapshots`
- `gold_match_features`
- `gold_goal_timing_features`
- `gold_player_snapshots`
- `gold_market_features`

## Leakage rule

For each match, gold features must only use earlier matches/events. The builder creates team snapshots before updating team histories with the current match.

## Works now with score-only data

If only match scores exist, v5 still builds:

- rolling goals for/against
- rolling points/form
- target outcome
- Over 2.5 target
- BTTS target

## Activates automatically with event data

If StatsBomb/TheStatsAPI event data exists, v5 adds:

- xG for/against
- shots for/against
- cards
- corners where event source exposes them
- first-half / second-half goal tendencies
- goal timing buckets

## Command

```bash
cd python_lab
python gold_feature_builder.py build --db ../build/omnibet.sqlite --rolling 10
python gold_feature_builder.py inspect --db ../build/omnibet.sqlite
```
