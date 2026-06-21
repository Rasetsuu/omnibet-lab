# v252 Bronze Validation Batch

v252 is the first batched post-v251 milestone.

It groups several related layers that were previously being split into tiny PRs:

```text
value/type validation
review reason normalization
candidate readiness summary
desktop validation surface contract
```

## Inputs

```text
omnibet.bronze_preview_field_schema_bundle.v251
```

## Outputs

```text
omnibet.bronze_preview_value_validation_bundle.v252
omnibet.bronze_preview_review_reason_bundle.v252
omnibet.bronze_candidate_readiness_summary.v252
omnibet.bronze_validation_batch_report.v252
```

## Value checks

```text
non-empty fixture/provider/bookmaker/market/selection fields
parseable decimal odds between 1.0 and 1000.0
UTC timestamp shape for kickoff/snapshot/observed fields
review-required rows remain review-required
```

## Readiness summary

The readiness summary is intentionally conservative:

```text
ready_for_bronze_write: false
ready_for_silver_promotion: false
ready_for_evaluation: false
ready_for_training: false
paper_only: true
```

This is because v252 still validates preview rows only. It does not write production bronze tables.

## Desktop surface

The desktop contract allows read-only inspection:

```text
candidate readiness
review reason counts
value validation rows
blocked row filters
```

It explicitly disables:

```text
import rows
promote rows
run evaluation
train model
place bets
```

## Why this matters

This is the start of the faster batch mode. v252 moves multiple connected backend/product-surface pieces in one CI-gated PR instead of one tiny layer per PR.

## Next beta-oriented batch

v253 should group provider/historical data work:

```text
provider adapter status matrix
local provider credential capability contract
historical dataset manifest expansion plan
market terminal data-source panel contract
```

This moves us closer to the actual prediction/betting research beta rather than only schema scaffolding.
