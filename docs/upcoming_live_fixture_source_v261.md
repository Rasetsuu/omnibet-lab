# v261 Upcoming/Live Fixture Source Contract

v261 defines the source contract that tells OmniBet which football matches exist now and soon.

This is not the final match browser and not a prediction engine. It is the normalized provider/source layer that later phases need before odds snapshots, live storage, prediction-ready context bundles, and the final market terminal can be trusted.

## Goal

Answer, safely and locally first:

```text
what matches are live now?
what matches are scheduled today/tomorrow/next days?
which provider saw them?
which match state fields are available?
which rows are blocked and why?
```

## Provider roles

Initial provider direction:

```text
api_football -> fixture date ranges, live state, lineups/events/stats availability
sportmonks_candidate -> richer fixture/livescore candidate, not a locked adapter yet
```

No credential values are stored or displayed. CI uses offline samples only.

## Request contracts

v261 describes two provider request shapes:

```text
fixture_date_range
live_fixture_state
```

Both are contract-only in CI:

```text
ci_network_allowed: false
```

## Normalized fixture/live row

Every normalized row must include:

```text
provider
provider_fixture_id
canonical_fixture_id
competition_id
competition_name
season
home_team
away_team
kickoff_time
status
phase
minute
home_score
away_score
lineup_available
event_data_available
stats_available
observed_at
captured_at
freshness_status
prediction_readiness
blocker_reason
next_action
```

## Status and freshness

Allowed statuses:

```text
scheduled
live
halftime
finished
postponed
cancelled
unknown
```

Allowed freshness states:

```text
fresh_sample
stale_sample
missing_timestamp
unknown
```

Allowed prediction-readiness states:

```text
fixture_visible
prediction_context_partial
blocked
```

A row can be visible without being prediction-ready. For example, a scheduled fixture may not have lineups yet, and a live fixture is still incomplete until odds snapshots arrive in v262.

## No-leak boundary

For every source row:

```text
observed_at <= captured_at
```

Later training must use only fields that existed at the prediction time. Final labels and settlement records are added only after the match is complete and settled.

## Files

```text
configs/upcoming_live_fixture_source.v261.json
data/provider_fixtures/v261/upcoming_live_fixture_source.sample.json
python_lab/upcoming_live_fixture_source_smoke.py
```

## Acceptance

v261 is accepted when:

```text
offline sample contains scheduled and live rows
required normalized fields are present
lineup/event/stats availability is explicit
timestamps preserve prediction-time boundaries
readiness and blocker reasons are explicit
no CI live provider calls exist
no credential values are present
README and phase docs point to v261
```
