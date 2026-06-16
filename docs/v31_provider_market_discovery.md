# v31 Provider Matrix and Dynamic Market Discovery

v31 defines how OmniBet should track provider capabilities and discover bookmaker markets over time.

The goal is to predict many market options eventually, without hardcoding one sportsbook website forever and without unsafe scraping.

## Provider groups

### Manual/reference sportsbook candidates

These are useful for market taxonomy, Romanian market naming, and human comparison:

```text
Superbet
Betano
Unibet
Bet365
Fortuna
Casa Pariurilor
Mozzart
Betfair
Pinnacle
```

Policy:

```text
manual/reference or permissioned/API only
no website scraping in CI
no account automation
no hidden data collection
```

### Official/API candidates

These are the preferred automation route:

```text
The Odds API
API-Football
Sportmonks
Betfair Exchange API / historical data
Pinnacle API if access is granted
football-data.org
OpenLigaDB
```

## Recommended use

```text
Odds and market discovery:
  The Odds API
  Betfair Exchange API
  Pinnacle only if access is approved

Football live state:
  API-Football
  Sportmonks
  football-data.org
  OpenLigaDB where coverage fits

Manual market taxonomy reference:
  Superbet, Betano, Unibet, Bet365, Fortuna, Casa Pariurilor, Mozzart
```

## Dynamic market discovery

Markets vary by match, time, region, bookmaker, and live state.

So OmniBet should not assume one fixed market list.

Instead, every observed market gets a raw snapshot:

```text
raw_market_snapshot_id
observed_at
provider_id
bookmaker
provider_sport_key
provider_event_id
match_id
raw_market_key
raw_market_name
raw_selection_key
raw_selection_name
decimal_odds
line_raw
line_value
team_name_raw
team_id
player_name_raw
player_id
period_raw
settlement_scope_guess
mapped_market_id
mapping_confidence
needs_mapping
suspended
last_update
payload_sha256
```

If the market is unknown:

```text
mapped_market_id = null
needs_mapping = true
```

Nothing is thrown away. Unknown markets go to a review queue.

## Mapping lifecycle

```text
1. Ingest raw provider market snapshot.
2. Parse line/team/player/period/selection guesses.
3. Map to known_market_id when confidence is high.
4. Otherwise keep needs_mapping=true.
5. Review unknown_market_queue.
6. Add parser/mapping rule.
7. Rerun mapping without mutating original raw snapshot.
```

## Known market families

Initial families:

```text
1x2
double_chance
draw_no_bet
totals
team_totals
handicap
asian_handicap
btts
correct_score
half_time_full_time
corners
team_corners
cards
team_cards
offsides
shots
shots_on_target
player_shots
player_shots_on_target
player_goalscorer
player_assists
player_cards
goalkeeper_saves
fouls
bet_builder_same_game_combo
boosted_odds_reference
```

## Why The Odds API is important

The Odds API has endpoints for sports, odds, scores, events, event odds, event markets, participants, historical odds, historical events, and historical event odds. The event-markets endpoint is especially important because it tells us which markets are available per bookmaker/event.

This gives OmniBet a clean way to discover markets dynamically.

## Why sportsbook websites still matter

Superbet and similar sportsbooks show real bookmaker taxonomy, localized names, live market UX, and Bet Builder structures.

But they should be used as:

```text
manual/reference sources
user-provided snapshots
permissioned/API sources if available
```

not as blind scraping targets.

## What v31 does not do

```text
No API keys.
No provider requests.
No website scraping.
No betting automation.
No staking recommendation.
No model-quality claim.
```

v31 only defines the safe data model for provider/market discovery.
