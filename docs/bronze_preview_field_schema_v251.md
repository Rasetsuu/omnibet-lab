# v251 Bronze Preview Field Schema

v251 validates required field names for quarantined, classified preview rows.

It still does not import, promote, evaluate, or train on any rows.

## Input

```text
omnibet.bronze_preview_classification_bundle.v250
```

## Output

```text
omnibet.bronze_preview_field_schema_bundle.v251
```

## Required fields

```text
fixture_result:
  fixture_id, home_team, away_team, kickoff_utc, result_status

odds_snapshot:
  fixture_id, provider_id, bookmaker_id, market_key, selection_key, price_decimal, snapshot_utc

lineup_event_context:
  fixture_id, provider_id, entity_id, event_type, observed_at_utc
```

Unknown or incomplete rows are marked:

```text
schema_status: review_required
```

## Safety

Every bundle and row keeps:

```text
quarantine_only: true
import_allowed_now: false
promotion_allowed: false
evaluation_allowed: false
training_dataset_promotion_allowed: false
```

This is a schema gate only. It does not approve rows for real bronze storage, evaluation, or training.

## Next step

v252 should add type/value validation for schema-ok rows, such as decimal odds parsing, timestamp shape checks, non-empty fixture IDs, and market key allowlist checks.
