# v38 Settlement and Outcome Truth Skeleton

v38 adds the first settlement/outcome truth skeleton.

It answers the next required question:

```text
Now that we have odds + match state in one timeline, can we grade market outcomes correctly?
```

The answer is: only where deterministic truth exists.

## Safety

CI remains offline only:

```text
local samples only
no API keys
no network calls
no website automation
no staking/profit output
no model-quality claim
```

Unsupported markets are not guessed.

## Input

v38 reuses the v37 offline provider timeline:

```text
v35 The Odds API-style odds/market sample
v36 API-Football-style fixture/live-state sample
v37 provider event link manifest
```

## SQLite objects created by the smoke

```text
settlement_rules
outcome_truth
settlement_evaluations
```

These are created by the v38 smoke itself. They can be promoted into the shared warehouse schema later.

## Initial supported settlement rules

```text
football_1x2_regulation
football_total_goals_regulation
football_corners_total_regulation
football_shots_on_target_total_regulation
football_asian_handicap_regulation
```

## Intentionally unsupported in v38

```text
football_player_shots_on_target_regulation
unknown/special combo markets
```

Player shots on target requires player-level shot truth. The v36 sample has team statistics, not player shot statistics, so v38 marks player props as unsupported.

## Derived truth

From the local sample:

```text
home team: France
away team: Senegal
score: France 2 - 1 Senegal
1X2 result: home
total goals: 3
total corners: 12
total shots on target: 10
home score margin: +1
```

## Settlement examples

```text
France 1X2 -> win
Draw 1X2 -> loss
Senegal 1X2 -> loss
Over 2.5 goals -> win
Under 2.5 goals -> loss
Over 9.5 corners -> win
Under 9.5 corners -> loss
Over 8.5 shots on target -> win
Under 8.5 shots on target -> loss
France -1.0 handicap -> push
Senegal +1.0 handicap -> push
player shots on target -> unsupported
unknown combo -> unmapped
```

## CI smoke

```bash
cd python_lab
python settlement_truth_smoke.py \
  --db ../build/omnibet_v38_settlement_truth.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v38_settlement_truth.json
```

Acceptance checks:

```text
v37 timeline builds successfully
settlement rules are written
outcome truth rows are written
1X2, totals, corners, shots-on-target, and handicap examples are evaluated
handicap push exists
player prop is unsupported
unknown market is unmapped
win/loss/push results are present
```

## What v38 does not do

```text
No real settlement provider.
No account/history import.
No player-prop settlement without player truth.
No live API calls.
No model training.
No betting output.
```

v38 is a correctness skeleton for market grading, not a predictive model.
