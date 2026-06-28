# v421-v430 Historical Materialization Command Bridge

This phase connects the v411-v420 historical materializer to a fixed local Rust command.

It generates Bronze, Silver, and Gold preview artifacts from the validated v401-v410 local historical sample pack. It still does not train a model.

## Included versions

```text
v421 historical materialization CLI contract
v422 allowlisted materialization command
v423 generated Bronze artifacts
v424 generated Silver artifacts
v425 generated Gold artifacts
v426 generated materialization manifest
v427 desktop reload contract placeholder
v428 failure-safe materialization report
v429 CI command bridge smoke
v430 command bridge docs
```

## Command

The fixed command is:

```text
omnibet-historical-materialization-runner
```

Accepted arguments:

```text
--root
--report-out
--manifest-out
--artifact-dir
--run-id
```

No free-form shell command is accepted.

## Generated outputs

Default report:

```text
reports/generated_historical_materialization_v421_v430_report.json
```

Default artifact directory:

```text
reports/materialized/v421_v430/
```

Generated artifacts:

```text
bronze_fixtures.generated.json
bronze_odds.generated.json
bronze_settlements.generated.json
silver_fixtures.generated.json
silver_odds.generated.json
gold_evaluation_candidates.generated.json
materialization_manifest.json
command_result.json
```

## Safety behavior

The success report keeps:

```text
paper_only = true
ready_for_walk_forward = true
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

Failure reports keep:

```text
status = materialization_command_failed_sample_only
ready_for_walk_forward = false
ready_for_training = false
trust_status = sample_only
credential_values_present = false
recommendation_output_present = false
```

## Why this matters

v411-v420 created the materializer logic. v421-v430 makes it executable by a local Rust command and produces real generated preview files in `reports/`.

This is the bridge from static materialization logic to generated artifacts that the desktop/report layers can later reload.

## Next

The next natural phase is:

```text
v431-v440 historical materialization desktop reload panel
```

That should expose the generated materialization report and artifact summaries in the desktop UI while keeping training locked.
