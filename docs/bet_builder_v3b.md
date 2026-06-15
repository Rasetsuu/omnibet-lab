# Bet Builder v3B

v3B adds a prototype same-game bet-builder engine.

## What it does now

- Creates candidate legs from the hybrid model:
  - 1X2
  - double chance
  - over/under goals
  - BTTS
  - team goals
  - prototype corners/cards placeholders
- Reads optional odds CSV:
  - `market_id`
  - `selection`
  - `odds`
  - `bookmaker`
- Computes:
  - fair odds
  - bookmaker combined odds
  - edge
  - Kelly and quarter-Kelly
  - correlation risk
  - no-bet / price-needed / ok decisions

## Why correlation risk matters

Same-game builder legs are not independent. Example:

- Team win + team over 1.5 goals: positive correlation.
- Over 2.5 + BTTS: positive correlation.
- Player to score + player shots on target: strong positive correlation.
- Red card yes + result markets: unstable/chaos.

v3B uses heuristic penalties. Later, this should become a learned joint-probability model.

## Example

```bash
cd python_lab
python bet_builder_lab.py \
  --home Spain \
  --away "Cape Verde" \
  --odds ../data/sample_odds_spain_cape_verde.csv \
  --out ../reports/v3b_bet_builder_spain_cape_verde.json
```

## Important

The model should not force bets. `NO BET` is a feature, not a bug.
