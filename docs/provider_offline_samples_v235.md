# v235 Offline Provider Sample Parsers

v235 adds the first typed Rust parser layer for provider samples, still with zero live network calls.

This is the next safe step after v234 provider metadata/status contracts.

## Samples parsed

```text
The Odds API-style event markets
  data/samples/the_odds_api_event_markets_sample.json

API-Football-style live state
  data/samples/api_football_live_state_sample.json
```

## Rust parser outputs

The Rust provider module now parses samples into typed normalized snapshots:

```text
ProviderFixtureSnapshot
ProviderOddsSnapshot
ProviderMarketDiscoverySnapshot
ProviderEventSnapshot
ProviderLineupPlayerSnapshot
ProviderTeamStatisticSnapshot
```

## The Odds API sample

The parser extracts:

```text
fixture identity
competition/sport
home/away teams
bookmakers
markets
outcomes
odds decimal
line/point
player-prop participant description
market discovery rows
unknown market review flags
source snapshot manifest
payload SHA-256
```

Expected sample counts:

```text
fixture_count: 1
market_rows: 8
odds_rows: 17
needs_mapping_review_rows: 1
```

The sample includes `special_combo_unknown`, which must require market-mapping review. Unknown markets cannot be auto-promoted.

## API-Football sample

The parser extracts:

```text
fixture identity
league/season/status
home/away teams
score
venue
match events
lineup starters/substitutes
team statistics
source snapshot manifest
payload SHA-256
```

Expected sample counts:

```text
fixture_count: 1
event_rows: 4
lineup_player_rows: 8
statistic_rows: 12
started_player_rows: 6
bench_player_rows: 2
```

## Safety

v235 remains offline-only:

```text
no HTTP client
no provider credentials
no external calls in CI
no credential values stored
no credential values displayed
```

It turns saved sample payloads into typed rows so later phases can promote them into bronze/silver/gold storage.

## Next steps

```text
v236: write parsed snapshots to local JSONL.GZ / bronze snapshot cache
v237: canonical identity and market mapping registry v1
v238: odds snapshot warehouse rows + no-vig preparation
v239: API-Football lineup/event promotion into silver facts
```
