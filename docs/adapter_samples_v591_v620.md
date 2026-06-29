# v591-v620 Adapter Samples

This phase moves from source planning into small local sample adapters.

## Goal

Prove that different source shapes can be normalized into one common historical preview pack.

No CI downloads are allowed. Everything is local sample data.

## Added samples

```text
data/source_samples/v591_v620/football_data_sample.csv
data/source_samples/v591_v620/openfootball_sample.json
data/source_samples/v591_v620/statsbomb_events_sample.json
```

A team-strength/rating sample remains a future slot because it is not required for the first normalizer smoke.

## Normalized output

The smoke writes:

```text
reports/normalized_historical_pack_v591_v620.json
```

Expected counts:

```text
fixtures: 6
results: 6
events: 4
ratings: 0
```

## Important status

```text
ready_for_real_model = false
```

This is adapter plumbing, not real scale yet.

## Next

```text
v621-v650 Rust normalizer/runtime migration
v651-v690 larger local historical row packs
```
