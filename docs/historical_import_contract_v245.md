# v245 Historical Import Contract

v245 starts the transition from tiny offline samples to larger historical import planning.

It does not fetch production data yet. It defines the rules that historical imports must satisfy before they can become bronze candidates for evaluation.

## Target layer

```text
historical_raw_to_bronze_candidate
```

## Required source classes

```text
fixture/results source
odds snapshot source
lineup/event context source
```

Every required source must have:

```text
point-in-time timestamp
provider identity mapping requirement
no persisted credentials
```

Odds sources must also require:

```text
market mapping
```

## Leakage guards

All historical imports must enforce:

```text
fixture start time required
odds snapshot time required
source snapshot time required
feature cutoff precedes fixture start
labels do not exist before settlement
closing odds kept separate from opening features
future team form forbidden
future lineup info forbidden
mutable provider rows versioned
```

## Settlement policy

```text
settlement lag: at least 24 hours
result source required
postponed/abandoned matches voided
market-specific settlement rules required
labels generated only after settlement
```

## Current sample windows

```text
sample_world_cup_2026_pre_tournament_window
sample_world_cup_2026_matchday_window
```

These are contract windows only. They do not imply that the app has imported real World Cup production data yet.

## Why this matters

The next phase is about model credibility. That requires historical data, but historical data is dangerous if it leaks future information.

v245 makes the import requirements explicit before we build the importer.

## Next step

v246 should add an offline historical manifest preview: enumerate candidate historical files/sources, validate their windows, and produce a no-network import plan artifact.
