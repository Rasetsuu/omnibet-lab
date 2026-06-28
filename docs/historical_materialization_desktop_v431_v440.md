# v431-v440 Historical Materialization Desktop Reload

This phase adds a desktop/report reload panel for the generated historical materialization command output from v421-v430.

It does not generate data itself. It loads:

```text
reports/generated_historical_materialization_v421_v430_report.json
```

and falls back to:

```text
tauri-app/src/historical-materialization.sample.json
```

## Included versions

```text
v431 desktop materialization report contract
v432 generated materialization report loader
v433 Bronze artifact summary panel
v434 Silver artifact summary panel
v435 Gold candidate summary panel
v436 materialization manifest panel
v437 trust and training lock panel
v438 fallback sample for desktop reload
v439 CI desktop reload smoke
v440 desktop reload docs
```

## Desktop page

The page id is:

```text
historical-materialization
```

Navigation label:

```text
Historical Materialization
```

Buttons:

```text
load-historical-materialization-status
load-historical-materialization-status-page
```

## Panels

```text
historical-materialization-summary
historical-materialization-artifacts
historical-materialization-bronze
historical-materialization-silver
historical-materialization-gold
historical-materialization-manifest
historical-materialization-trust
```

## Renderer

```text
tauri-app/src/historical_materialization.js
```

The renderer loads the generated v421-v430 report first and falls back to the bundled sample when generated files are not present.

## Safety locks

The desktop must display the generated state without unlocking training:

```text
ready_for_walk_forward = true
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

## What this enables

This gives the GUI a readable view of materialized historical data layers:

```text
Bronze fixtures / odds / settlements
Silver fixtures / odds
Gold evaluation candidates
materialization manifest
training lock / trust state
```

## Next

The next phase should move toward either:

```text
v441-v450 real local historical file adapter/import UX
```

or:

```text
v441-v450 materialized storage hashes and compression-backed generated artifacts
```

The safer order is storage hashes/compression first, then larger real historical file adapter UX.
