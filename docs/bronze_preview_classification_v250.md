# v250 Bronze Preview Classification

v250 classifies quarantined v249 preview rows before any import or promotion path can use them.

## Input

```text
omnibet.bronze_candidate_preview_bundle.v249
```

## Output

```text
omnibet.bronze_preview_classification_bundle.v250
```

## Known source classes

```text
fixtures_results -> fixture_result
odds -> odds_snapshot
lineups_events -> lineup_event_context
```

Unknown source kinds are marked:

```text
classification_status: review_required
row_class: unknown
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

v250 is still a review/classification layer. It does not write real bronze tables and does not approve rows for model evaluation or training.

## Next step

v251 should add field-level schema checks for each classified row type. For example, odds rows should require market/provider/price/snapshot-time fields, fixture rows should require fixture/team/time/result fields, and event-context rows should require provider/entity/timestamp fields.
