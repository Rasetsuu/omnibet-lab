# Football Market Registry v3B

v3B introduces a proper market registry. The goal is to stop thinking of football prediction as only `1X2 + over 2.5`.

## Registry contract

Each market has:

- `market_id`
- `sport`
- `family`
- `display_name`
- `selections`
- `requires_team`
- `requires_player`
- `requires_line`
- `requires_minute`
- `availability`
- `model_hint`
- `data_requirements`
- `correlation_tags`

## Availability levels

- `supported`: model has current probability support.
- `prototype`: derived or placeholder probability exists, but not a dedicated trained model.
- `future`: schema exists, but it needs event/player/live data.

## Long-term football market families

- Core result markets
- Goal totals
- Team goals
- BTTS
- Correct score
- Goal timing
- First scorer / anytime scorer
- Player shots / shots on target
- Assists / passes / key passes
- Corners
- Cards / red cards / player cards
- Offsides
- Penalties
- Half-time and interval markets

Use:

```bash
cd python_lab
python market_registry.py --sport football
python market_registry.py --sport football --json ../reports/v3b_football_market_registry.json
```
