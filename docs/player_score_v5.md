# Player Score v5

v5 adds a first prototype player-score builder.

## Inputs

- `lineups`
- `match_events`

## Current prototype signals

- expected minutes
- goals per 90
- shots per 90
- xG per 90
- cards per 90

## Output

`gold_player_snapshots`

## Important

This is not the final player rating. It is a scaffold that becomes useful once event/lineup data is imported.

Long-term player score should be position-specific and include:

- league strength
- age curve
- recent form
- injury/suspension risk
- starter probability
- position fit
- role: penalty taker, free-kick taker, corner taker
- team tactical context
