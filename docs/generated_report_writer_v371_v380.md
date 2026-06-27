# v371-v380 Generated Report Writer and Desktop Reload

This batched phase turns the v361 local import runner into an actual generated report writer path.

It still remains `sample_only`. It does not unlock terminal predictions, bilet builder, staking, profitability claims, or real recommendations.

## Included versions

```text
v371 generated report writer CLI shape
v372 generated desktop sample writer
v373 generated storage manifest writer
v374 mini-pack integrity failure report
v375 generated report reload button path
v376 sample_only trust gate preservation
v377 generated artifacts upload in CI
v378 local import runner docs update
v379 no recommendation output enforcement
v380 generated report writer smoke
```

## CLI

The new binary is:

```text
omnibet-local-import-runner
```

Registered in:

```text
rust-core/Cargo.toml
rust-core/src/bin/omnibet-local-import-runner.rs
```

Default output paths:

```text
reports/generated_v371_v380_green_sample.json
tauri-app/src/generated-green-sample.generated.json
reports/generated_v371_v380_storage_manifest.json
```

Supported arguments:

```text
--root
--report-out
--desktop-out
--storage-manifest-out
```

## Generated outputs

The CLI writes:

```text
generated green report
generated desktop reload JSON
generated storage manifest
```

The desktop renderer now prefers:

```text
tauri-app/src/generated-green-sample.generated.json
```

and falls back to:

```text
tauri-app/src/generated-green-sample.sample.json
```

## Integrity failure behavior

If the mini-pack cannot be parsed or verified, the CLI writes a safe failure report:

```text
integrity_failed_sample_only
```

The failure path preserves:

```text
paper_only = true
trust_status = sample_only
validated_paper = false
terminal_prediction_allowed = false
bilet_builder_allowed = false
recommendation_output_present = false
```

## Safety constraints

The writer enforces:

```text
local-only input
no live provider calls
no credential values
no recommendation output
no validated_paper claim
sample_only trust gate
```

## CI artifacts

The workflow uploads:

```text
reports/generated_v371_v380_green_sample.json
reports/generated_v371_v380_storage_manifest.json
reports/ci_v371_v380_generated_report_writer.json
tauri-app/src/generated-green-sample.generated.json
```

## Acceptance

v371-v380 is accepted when:

```text
generated report writer CLI is defined
generated desktop sample writer is defined
generated storage manifest writer is defined
mini-pack integrity failure report is defined
desktop generated reload path is added
trust gate remains sample_only
generated artifacts are uploaded in CI
local import runner docs are updated
no recommendation output is enforced
Python smoke and CI are added
no live calls, credentials, or recommendations are introduced
```
