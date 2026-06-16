# v36 API-Football Offline Live-State Adapter

v36 adds an offline API-Football-style adapter for match state.

It complements v35:

```text
v35 = provider odds / markets
v36 = provider fixture state / lineups / events / stats
```

## Safety

CI is offline only:

```text
local sample JSON only
no API key
no network call
no paid quota
no website automation
no betting output
```

## Files

```text
data/samples/api_football_live_state_sample.json
python_lab/adapters/api_football_adapter.py
python_lab/api_football_offline_smoke.py
configs/api_football_adapter.v36.json
```

## What imports

The adapter reads local API-Football-style fixture JSON and writes:

```text
teams
players
matches_norm
lineups
match_events
bronze_blobs
```

The raw payload is preserved in `bronze_blobs` before normalization.

## Sample coverage

The local sample includes:

```text
fixture id/date/status/venue/referee
league/season/round
home/away teams
goals and score
events: goals and card
lineups: startXI and substitutes
statistics: shots, corners, possession, cards
```

## CI smoke

```bash
cd python_lab
python api_football_offline_smoke.py \
  --db ../build/omnibet_v36_api_football_offline.sqlite \
  --input ../data/samples/api_football_live_state_sample.json \
  --out ../reports/ci_v36_api_football_offline.json
```

Acceptance checks:

```text
fixture imports into matches_norm
both teams import into teams
players import into players
lineups import into lineups
goal/card events import into match_events
raw payload is preserved in bronze_blobs
statistics summary is emitted
```

## What v36 does not do

```text
No live API integration.
No API key handling beyond config docs.
No network call in CI.
No settlement engine.
No betting/staking output.
No profit claim.
```

v36 is a provider live-state ingestion skeleton, not a live betting system.
