# v30 Bookmaker Odds and Bet Builder Market Contract

v30 defines how OmniBet should represent bookmaker odds, Romanian `cota/cote`, and Bet Builder / same-game parlay markets before any sportsbook integration is added.

## Language

```text
cota = decimal odd / price
cote = odds / prices
Bet Builder = same-game parlay / same-match accumulator
```

## Why this matters

A normal 1X2 market is simple:

```text
France win @ 1.50
Draw @ 4.50
Senegal win @ 6.50
```

A Bet Builder is different because every leg is inside the same match:

```text
France win
France over 4.5 corners
Player over 1.5 shots
Over 2.5 total goals
```

Those legs are correlated. You cannot safely multiply single-leg fair probabilities and call it the true builder probability. A bookmaker's combined quote already includes correlation pricing and margin.

## Core market rows

OmniBet should normalize these market families first:

```text
football_1x2_regulation
football_total_goals_regulation
football_asian_handicap_regulation
football_corners_regulation
football_cards_regulation
football_player_shots_regulation
football_anytime_scorer_regulation
```

Every market row should carry:

```text
market_id
settlement_scope
selection
line
team_id
player_id
bookmaker
decimal_odds
observed_at
provider_event_id
payload_sha256
```

## Odds math

Decimal odds imply raw probability:

```text
p_raw = 1 / decimal_odds
```

For 1X2, normalize by overround:

```text
raw_home = 1 / home_odds
raw_draw = 1 / draw_odds
raw_away = 1 / away_odds
overround = raw_home + raw_draw + raw_away - 1
p_no_vig_home = raw_home / (raw_home + raw_draw + raw_away)
```

This gives the market baseline that the model must beat.

## Bet Builder contract

A builder has:

```text
builder_id
match_id
bookmaker
observed_at
provider_event_id
combined_decimal_odds
legs[]
payload_sha256
```

Each leg has:

```text
leg_id
market_id
selection
line
team_id
player_id
settlement_scope
decimal_odds
provider_leg_id
```

Output should include:

```text
bookmaker_quote
model_joint_probability
model_edge
correlation_warning
paper_only
```

## Source policy

### Flashscore

Useful as a human-facing score/status/stat reference, but its terms say the site is for personal use, not commercial purpose; it restricts automated requests, scraping, aggregation, and recreating content without consent.

Therefore:

```text
Do not add a Flashscore scraper unless permission/API/legal route is confirmed.
```

### Superbet

Useful as a Romanian sportsbook reference for odds, live offers, and Bet Builder examples. Treat it as:

```text
manual/user-provided snapshots first
permissioned/API source later if available
not a CI data source
```

No API keys, accounts, or automated sportsbook scraping should be added to CI.

## Live odds snapshots

Live odds should use append-only snapshots:

```text
live_odds_snapshots
```

Required fields:

```text
snapshot_id
observed_at
provider_id
bookmaker
provider_event_id
match_id
market_id
selection
line
player_id
team_id
decimal_odds
suspended
last_update
payload_sha256
```

The rule is the same as v29:

```text
Only use snapshots with observed_at <= evaluation_time.
```

## What v30 does not do

v30 does not add:

```text
Superbet scraper
Flashscore scraper
API-key integration
staking recommendations
profit claims
live betting automation
```

It only defines the market model so future ingestion is safe.
