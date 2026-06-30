# v681-v710 Rust Sample Runner

This phase adds a tiny Rust CLI runner around the local sample parsers.

## Binary

```text
omnibet-sample-pack-runner
```

## Default inputs

```text
data/source_samples/v591_v620/football_data_sample.csv
data/source_samples/v591_v620/openfootball_sample.json
data/source_samples/v591_v620/statsbomb_events_sample.json
```

## Default output

```text
reports/rust_sample_pack_v681_v710.json
```

## Expected counts

```text
fixtures: 6
results: 6
events: 4
```

## Scope

Local files only. No network calls.

This is a runner bridge toward larger local packs and later GUI data-status integration.
