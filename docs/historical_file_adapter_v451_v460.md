# v451-v460 Historical File Adapter

This phase starts the move from bundled sample rows toward user-provided historical files.

It adds local CSV adapter samples for fixtures, odds, settlements, and identity mapping. The adapter flow is still preview-only and does not train a model.

## Included versions

```text
v451 historical file adapter contract
v452 local fixture CSV adapter
v453 local odds CSV adapter
v454 local settlement CSV adapter
v455 local identity CSV adapter
v456 adapter catalog sample
v457 local adapter preview report
v458 desktop upload UX contract placeholder
v459 CI file adapter smoke
v460 file adapter docs
```

## Inputs

Sample local CSV files:

```text
data/historical/v451_v460/fixtures.adapter.sample.csv
data/historical/v451_v460/odds.adapter.sample.csv
data/historical/v451_v460/settlements.adapter.sample.csv
data/historical/v451_v460/identity_map.adapter.sample.csv
```

Adapter catalog:

```text
data/historical/v451_v460/adapter_catalog.sample.json
```

## Outputs

The smoke generates:

```text
reports/historical_file_adapter_v451_v460_report.json
reports/historical_file_adapter_v451_v460_normalized_preview.json
reports/ci_v451_v460_historical_file_adapter.json
```

## Validation rules

The adapter preview checks:

```text
fixture ids are unique
odds rows reference known fixtures
settlement rows reference known fixtures and odds keys
decimal odds are greater than 1.0
closing odds are captured at or before kickoff
labels are available after prediction time
low-confidence identities require review
```

## Desktop UX placeholder

This phase adds the contract placeholder for a future upload/import panel:

```text
historical-file-adapter
preview-historical-file-adapter
historical-file-adapter-inputs
historical-file-adapter-preview
historical-file-adapter-errors
historical-file-adapter-trust
```

The actual desktop upload UI should come in a later phase once adapter report schemas are stable.

## Safety locks

```text
paper_only = true
local_first = true
no live provider calls
no credential values
no recommendation output
ready_for_materialization may become true
ready_for_training = false
trust_status = sample_only
```

Even valid imported local CSV previews remain blocked from training:

```text
ready_for_training = false
```

## Next

The next phase should turn the adapter preview into a generated local import command or desktop import panel, depending on whether the CLI path or UI path is more urgent.
