# Final GUI Market Terminal Vision

This document records the long-term OmniBet desktop target so the GUI does not drift into a simple dashboard.

The final application should be a cross-platform Windows/Linux Tauri desktop app where a user can open real upcoming and live football matches, select a match, inspect every supported bettable market family, and build paper-only same-game tickets with model trust, fair odds, bookmaker odds, edge, CLV, and correlation risk.

It is not enough to show only:

```text
Team A win / draw / Team B win
```

The final GUI must support bilet-builder quality market exploration.

## Core views

```text
Upcoming Matches
Live Matches
Match Prediction Terminal
Bilet Builder
Player Props
Market Mapping Review
Paper Ledger
Data Sources
Model Lab
Settings
```

## Match prediction terminal

For one selected fixture, the user should be able to browse market families such as:

```text
1X2 / double chance / draw no bet
qualification / after extra time / penalties
correct score / winning margin / goal timing
total goals / team goals / BTTS
first half / second half markets
corners / team corners / corner handicaps
cards / player cards / red cards / booking points
offsides / team offsides / player offsides
shots / shots on target / player shots
anytime scorer / first scorer / assists / goal-or-assist
penalties / own goals / goalkeeper saves
```

Each row should show:

```text
model probability
fair odds
bookmaker odds when available
edge / EV
model trust
required data coverage
settlement scope
market status: active / disabled / needs lineup / unsupported / unknown mapping
```

## Live matches

Live mode should show:

```text
score
clock / phase
red/yellow cards
lineups and substitutions
events
team/player stats
odds movement
market availability changes
```

Live predictions must be lower-trust unless live state, lineup, event, and odds timestamps are clean.

## Lineup-dependent markets

Player props are not reliable before lineups are known. Pre-lineup mode can use probable lineups, expected minutes, recent starts, injuries, and roles, but must show lower trust.

Markets requiring lineup/player context include:

```text
anytime scorer
first goalscorer
player shots
player shots on target
player assists
player cards
player fouls
player offsides
goalkeeper saves
```

Once confirmed lineups arrive, the GUI should reprice player markets and clearly show that the prediction is lineup-adjusted.

## Bilet Builder

The builder should support:

```text
Safe
Balanced
Aggressive
Custom
```

A ticket should display:

```text
legs
combined model probability
fair odds
book odds
edge
correlation risk
contradiction warnings
confidence / model trust
paper-only ledger action
```

The builder must be correlation-aware. Same-game selections are not independent.

Examples of positive correlation:

```text
team win + team over 1.5 goals
over 2.5 goals + BTTS
player to score + player shots on target over
red card yes + over cards
```

Examples that should be rejected or heavily warned:

```text
under 1.5 goals + both strikers to score
no goal before 30' + first goal before 15'
low-tempo script + high shots + high corners + high goals
```

## Data source UX

The GUI should show provider health, not secrets:

```text
provider enabled/disabled
credential present/missing
last snapshot time
quota/status if available
last error
market count
lineup availability
live-state freshness
```

Credential values must never be displayed.

## Model trust UX

Every market must have its own trust status. A model may be strong for 1X2 but weak for corners, cards, scorer, or offsides.

Possible statuses:

```text
unsupported
sample only
low data
experimental
paper watch
validated paper
```

No market should show confident value language until it has enough historical validation, calibration, no-vig baseline comparison, and CLV evidence.

## Build order

The GUI shell can exist before the model is final, but full prediction actions should unlock only as the engine becomes credible.

Recommended order:

```text
1. upcoming/live match browser
2. provider status and data freshness
3. market discovery/mapping review
4. simple market prediction table
5. bilet builder preview with disabled low-trust props
6. player props after lineup/event/player data exists
7. full live match terminal
8. final polished release UI
```

The final GUI is the product surface, but the engine/data/model trust must come first.
