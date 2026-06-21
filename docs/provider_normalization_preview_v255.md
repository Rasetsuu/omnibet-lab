# v255 Provider Normalization Preview

v255 normalizes the offline priority-provider fixtures from v254 into quarantined preview rows.

## Inputs

```text
data/provider_fixtures/v254/odds_provider_snapshot.sample.json
data/provider_fixtures/v254/football_fixture_event.sample.json
```

## Output

```text
omnibet.provider_normalization_preview_bundle.v255
```

## Preview row types

```text
odds_snapshot_candidate
fixture_result_candidate
event_context_candidate
```

Expected sample output from the current fixtures:

```text
odds_snapshot_candidate: 3
fixture_result_candidate: 1
event_context_candidate: 1
total_rows: 5
```

## Safety

```text
paper_only: true
network_calls_allowed_in_ci: false
credentials_stored_in_repo: false
live_fetch_enabled: false
quarantine_only: true
promotion_allowed: false
evaluation_allowed: false
training_dataset_promotion_allowed: false
```

## Desktop surface

The desktop can show normalized preview counts, provider row samples, row-type filters, and a quarantine banner.

It can export preview reports, but cannot promote to bronze, run evaluation, or train a model.

## Next beta-oriented batch

v256 should connect normalized preview rows into the existing v252 validation/readiness surface and produce a single source-terminal report for the desktop:

```text
adapter health
normalization preview counts
value validation status
review reason counts
candidate readiness
```
