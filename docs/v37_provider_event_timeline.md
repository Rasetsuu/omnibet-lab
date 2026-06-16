# v37 Offline Provider Event Timeline Join

v37 joins the two Phase A offline provider paths:

```text
v35 The Odds API-style odds/event-market sample
v36 API-Football-style fixture/live-state sample
```

into one canonical provider event timeline.

## Goal

Create one canonical event view:

```text
canonical_event_id
  ├─ odds provider event id
  └─ match-state provider fixture id
```

Then materialize a combined timeline:

```text
match_state rows
match_event rows
odds_market rows
```

## Safety

CI remains offline only:

```text
local samples only
no API keys
no network calls
no paid quota
no website automation
no betting/staking output
```

## Files

```text
data/samples/provider_event_link_sample.v37.json
python_lab/provider_event_timeline_smoke.py
configs/provider_event_timeline.v37.json
```

The smoke reuses:

```text
data/samples/the_odds_api_event_markets_sample.json
data/samples/api_football_live_state_sample.json
```

## SQLite objects created by the smoke

```text
provider_event_links
provider_event_timeline
```

These are created by the v37 smoke itself so the milestone stays isolated and safe.
Later they can be promoted into the shared warehouse schema.

## Timeline row types

```text
match_state:
  fixture status, score, match date

match_event:
  goals, cards, provider event minute, player/team ids

odds_market:
  bookmaker, mapped market id, raw market name, raw selection, line, decimal odds, needs_mapping
```

## CI smoke

```bash
cd python_lab
python provider_event_timeline_smoke.py \
  --db ../build/omnibet_v37_provider_event_timeline.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v37_provider_event_timeline.json
```

Acceptance checks:

```text
v35 odds adapter report is ok
v36 state adapter report is ok
2 provider event links are written
timeline includes match_state rows
timeline includes match_event rows
timeline includes odds_market rows
mapped market ids are present
unknown markets remain visible
```

## What v37 does not do

```text
No live provider linking.
No fuzzy event matching.
No live API calls.
No API keys.
No settlement engine.
No betting output.
```

v37 only proves that offline provider odds and match-state data can be joined into one canonical event timeline.
