# v29 Feature Priority and Live Data Contract

v29 freezes the feature policy before OmniBet grows into larger datasets and live providers.

The goal is not to collect everything. The goal is to collect what is likely to help and can be validated without leakage.

## Core feature scope

The serious engine should focus on:

```text
must-have + high-value + refined medium-value
```

### Must-have

```text
match identity
source identity
competition / season / date
two teams
home / away / neutral
regulation score
full-time score
extra-time score when present
penalty result when present
market id
settlement scope
opening odds
closing odds
no-vig implied probability
```

### High-value

```text
lineups
starters / substitutes
player minutes
player roles / positions
reliable injuries / suspensions
xG / xA
shots / shots on target
corners
cards / red cards
fouls
substitutions
goalkeeper actions
recent form
rest days / fixture congestion
rolling team/player strength
```

### Refined medium-value

```text
referee
tournament stage
match importance / qualification context
squad rotation
club strength of national-team players
national-team chemistry / continuity
```

These are allowed in the core engine because they are plausible, interpretable, and especially useful for cards, props, tournament matches, and international football.

## Experimental medium-value

These can be added later behind ablation reports:

```text
travel distance / time zone
crowd attendance
pitch condition
```

## Postponed by default

These should not consume early engineering/storage effort:

```text
weather
social media sentiment
vague news sentiment
rumors
```

Weather is not forbidden forever. It is just low priority because historical availability and reliability are inconsistent, and it is likely only useful in extreme cases.

## Live data architecture

Live games should use append-only point-in-time snapshots.

Do **not** mutate one current-row table and pretend it is historical truth. Every state change should have:

```text
observed_at
provider timestamp when available
provider id
provider fixture/event id
normalized match id when resolved
payload sha256
```

## Proposed live snapshot tables

```text
live_fixture_snapshots
live_event_snapshots
live_lineup_snapshots
live_stat_snapshots
live_odds_snapshots
```

The key rule:

```text
any prediction or evaluation may use only snapshots with observed_at <= evaluation_time
```

That prevents future leakage.

## Provider roles

Candidate live data providers:

```text
API-Football:
  fixtures, events, lineups, stats, players, odds candidate

Sportmonks:
  live scores, fixtures, events, World Cup app/live docs candidate

The Odds API:
  odds, scores, events, event odds, historical odds candidate
```

All provider work is API-key/network dependent and must stay out of CI.

## Runtime loop

Future local/runtime loop:

```text
poll fixture/status provider
append live fixture snapshot
append event/stat/lineup snapshots when available
append odds snapshots from odds provider
join latest point-in-time features
run Rust model artifact inference
write paper-only report/decision rows
after match, evaluate against final result and closing odds without rewriting old snapshots
```

## Relationship to previous milestones

```text
v26:
  local historical backfill

v27:
  Parquet+ZSTD heavy storage path

v28:
  real-source acquisition catalog

v29:
  feature priority + live point-in-time contract
```

## Honesty

v29 does not add a live betting system.

It only defines the contract that future live ingestion must obey.

No model-quality, betting-profit, or live-readiness claim is made.
