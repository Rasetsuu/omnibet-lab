# v242 Market Review Patch

v242 adds a controlled sample-only market review patch path.

It demonstrates how an unresolved market review row can be cleared only when a full canonical market definition and provider alias are added.

## Scope

```text
offline sample only
not production mapping
not training promotion
not automatic application
```

## Target review row

```text
provider: the_odds_api
market key: special_combo_unknown
```

## Required market fields

The patch must provide:

```text
canonical_market_id
family
settlement_rule
selection_scope
correlation_group
line_required
player_required
lineup_required
```

## Sample canonical market

```text
sample_same_game_combo_france_win_player_shot_team_corners
```

This is a same-game combo sample market:

```text
France win + player shot + team corners
```

It is marked:

```text
family: same_game_combo
selection_scope: compound_selection
player_required: true
lineup_required: true
correlation_group: same_game_combo_high_correlation
```

## Expected proof

v242 tests both states:

```text
unpatched: special_combo_unknown remains blocked
patched: market review count becomes 0
patched: total review rows become 0
patched: silver_ready becomes true
```

Even when patched, the result is still preview-only. Training promotion remains forbidden.

## Next step

v243 should turn the silver-ready preview into a small silver fact preview bundle, still offline-only and still not a training dataset.
