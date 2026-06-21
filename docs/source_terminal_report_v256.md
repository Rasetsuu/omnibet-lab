# v256 Source Terminal Report

v256 combines the provider-side beta pieces into one desktop-facing source terminal report.

## Inputs

```text
omnibet.provider_adapter_validation_report.v254
omnibet.provider_normalization_preview_bundle.v255
```

## Output

```text
omnibet.source_terminal_report.v256
```

## Report contents

```text
adapter count
adapter OK count
normalized total rows
normalized row counts by type
readiness badges
blocker summary
locked desktop actions
```

## Expected sample source-terminal status

Using the offline v254 fixtures and v255 normalizer:

```text
adapter_count: 2
adapter_ok_count: 2
normalized_total_rows: 5
odds_snapshot_candidate: 3
fixture_result_candidate: 1
event_context_candidate: 1
source_terminal_visible: true
```

## Desktop panels

```text
adapter health
normalization counts
row type filters
blocker summary
readiness badges
quarantine banner
```

## Actions

Allowed:

```text
inspect adapters
inspect rows
export report
```

Disabled:

```text
live fetch
promote to bronze
run evaluation
train model
place bets
```

## Safety

The report is still paper-only and quarantine-only. It makes the source terminal useful for inspection, but it does not enable ingestion, evaluation, model training, or betting.

## Next beta-oriented batch

v257 should add a desktop command contract for opening this report from the Tauri UI and rendering source terminal cards/tables:

```text
source terminal command schema
source terminal mock payload
frontend panel contract
read-only export action
```
