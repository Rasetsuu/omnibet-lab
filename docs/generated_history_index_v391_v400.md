# v391-v400 Generated Report Persistence and Local History Index

This phase makes generated reports persistent instead of only overwriting the latest output files.

Every generated run receives a local run id and an immutable archive directory. The latest files can still be overwritten for desktop convenience, but the history index keeps prior successful and failed runs.

The system remains `sample_only`. It does not unlock terminal predictions, bilet builder, staking, profitability claims, or real recommendations.

## Included versions

```text
v391 generated run id contract
v392 immutable generated report archive
v393 generated storage history manifest
v394 local history index writer
v395 latest pointer + history index split
v396 desktop history panel
v397 failed run history preservation
v398 sample_only trust gate preservation
v399 CI history-index smoke
v400 generated persistence docs
```

## Runner additions

The local runner now accepts:

```text
--history-dir
--history-index-out
--run-id
```

Default history paths:

```text
reports/generated_history/runs
reports/generated_history/index.json
```

Each run archive contains:

```text
green_report.json
desktop_report.json
storage_manifest.json
command_result.json
```

## Latest versus history

Latest files remain:

```text
reports/generated_v371_v380_green_sample.json
tauri-app/src/generated-green-sample.generated.json
reports/generated_v371_v380_storage_manifest.json
```

History files live under:

```text
reports/generated_history/runs/<run_id>/
```

The index lives at:

```text
reports/generated_history/index.json
```

## Failure preservation

If integrity checks fail, the runner still writes a run archive with:

```text
integrity_failed_sample_only
```

and preserves:

```text
paper_only = true
trust_status = sample_only
validated_paper = false
terminal_prediction_allowed = false
bilet_builder_allowed = false
recommendation_output_present = false
```

## Desktop history panel

The Generated Green page now includes:

```text
generated-green-history
```

It loads the generated history index and falls back to:

```text
tauri-app/src/generated-history.sample.json
```

## Safety invariants

```text
immutable archive required
latest pointer allowed
failed runs preserved
trust_status = sample_only
validated_paper = false
terminal_prediction_allowed = false
bilet_builder_allowed = false
credential values forbidden
recommendation output forbidden
```

## CI

The v391-v400 workflow runs the local runner with:

```text
--run-id ci_v391_v400
--history-dir reports/generated_history/runs
--history-index-out reports/generated_history/index.json
```

and uploads:

```text
reports/generated_history/index.json
reports/generated_history/runs/ci_v391_v400/green_report.json
reports/generated_history/runs/ci_v391_v400/desktop_report.json
reports/generated_history/runs/ci_v391_v400/storage_manifest.json
reports/generated_history/runs/ci_v391_v400/command_result.json
reports/ci_v391_v400_generated_history_index.json
```

## Acceptance

v391-v400 is accepted when:

```text
generated run id contract is defined
immutable generated report archive is added
generated storage history manifest is added
local history index writer is added
latest pointer + history index split is added
desktop history panel is added
failed run history preservation is added
sample_only trust gate is preserved
CI history-index smoke is added
generated persistence docs are added
no live calls, credentials, or recommendations are introduced
```
