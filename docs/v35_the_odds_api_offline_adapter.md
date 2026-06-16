# v35 The Odds API Offline Event-Market Adapter

v35 adds the first provider-style adapter skeleton.

It is offline-only in CI:

```text
local sample JSON only
no API key
no network call
no paid quota
no website automation
```

## Goal

Take The Odds API-style event odds/markets JSON and push it through the market pipeline:

```text
sample event-market JSON
→ raw_market_snapshots
→ exact alias apply
→ mapped_market_id when safe
→ unknown_market_queue for unmapped markets
→ provider coverage report
```

## Files

```text
python_lab/adapters/the_odds_api_adapter.py
python_lab/the_odds_api_offline_smoke.py
data/samples/the_odds_api_event_markets_sample.json
configs/the_odds_api_adapter.v35.json
```

## Sample shape

The local sample includes:

```text
event id
sport key
home/away teams
bookmakers
markets
outcomes
decimal prices
optional point/line
```

Markets covered by the sample:

```text
h2h / 1X2
totals
spreads / handicap
corners
shots on target
player shots on target
unknown special combo
```

## Adapter behavior

The adapter:

```text
loads local sample JSON
normalizes market keys into raw market names
writes one raw_market_snapshots row per outcome
seeds minimal canonical market aliases for smoke coverage
applies exact high-confidence market aliases only
writes resolver_mapping_candidates and resolver_mapping_decisions for mapped rows
leaves unknown rows in unknown_market_queue
```

## CI smoke

```bash
cd python_lab
python the_odds_api_offline_smoke.py \
  --db ../build/omnibet_v35_the_odds_api_offline.sqlite \
  --input ../data/samples/the_odds_api_event_markets_sample.json \
  --out ../reports/ci_v35_the_odds_api_offline.json
```

Acceptance checks:

```text
events_seen == 1
bookmakers_seen == 2
raw snapshots inserted
h2h maps to football_1x2_regulation
totals maps to football_total_goals_regulation
corners maps to football_corners_total_regulation
shots on target maps separately from shots
player shots on target maps separately
unknown combo remains unknown
resolver decisions are written
```

## What v35 does not do

```text
No live API integration.
No API key handling beyond config docs.
No network call in CI.
No fuzzy market auto-mapping.
No betting/staking output.
No profit claim.
```

v35 is a provider-ingestion skeleton, not a live betting system.
