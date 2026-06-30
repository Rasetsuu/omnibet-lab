# v801-v830 Feature Builder v1

This phase converts local completed match rows into feature rows.

## Input

```text
data/source_samples/v591_v620/football_data_sample.csv
```

## Output

```text
reports/ci_v801_v830_feature_builder_v1.json
reports/feature_rows_v801_v830.json
```

## First fields

```text
history match counts
points-per-match before kickoff
goals for/against before kickoff
home field flag
result labels
```

## Ordering rule

Each feature row is built before the current match updates team history.

## Expected current status

```text
feature rows: 3
ready_for_v1_baseline: false
```

The sample is enough for a smoke check, not enough for v1 baseline work.
