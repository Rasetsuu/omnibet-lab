# v381-v390 Generated Report Command Bridge

This phase connects the generated green report writer to the desktop command bridge.

The desktop can now request a generated green report through a fixed allowlisted Tauri command, then reload the generated JSON into the Generated Green page.

It remains `sample_only`. It does not unlock terminal predictions, bilet builder, staking, profitability claims, or real recommendations.

## Included versions

```text
v381 generated report command contract
v382 allowlisted local-import-runner command
v383 desktop Run Generated Green button
v384 command result report panel
v385 generated file reload after command
v386 failure-safe integrity report display
v387 sample_only trust gate preservation
v388 no live calls / no credentials guard
v389 CI command-bridge smoke
v390 generated command bridge docs
```

## Tauri command

The new command is:

```text
run_generated_green_report
```

It calls only:

```text
omnibet-local-import-runner
```

with fixed arguments:

```text
--root .
--report-out reports/generated_v371_v380_green_sample.json
--desktop-out tauri-app/src/generated-green-sample.generated.json
--storage-manifest-out reports/generated_v371_v380_storage_manifest.json
```

No user-provided shell command is accepted.

## Desktop UI

The Generated Green page now has:

```text
Run generated green report
Reload generated green report
Command result panel
Generated report panels
```

The run flow is:

```text
click run
→ invoke run_generated_green_report
→ render command result
→ reload tauri-app/src/generated-green-sample.generated.json
→ fall back to bundled sample if generated file is missing
```

## Safety invariants

```text
allowlisted command only
shell execution disabled
live provider calls disabled
credential values disabled
recommendation output disabled
trust_status = sample_only
validated_paper = false
terminal_prediction_allowed = false
bilet_builder_allowed = false
```

## CI

CI verifies the bridge by checking:

```text
Tauri backend command wiring
allowlist includes omnibet-local-import-runner
fixed CLI args are present
browser fallback is safe
run button and command panel are present
HTML IDs are unique
smoke report passes
```

## Acceptance

v381-v390 is accepted when:

```text
generated report command contract is defined
allowlisted local-import-runner command is added
desktop run generated green button is added
command result report panel is added
generated file reload after command is added
failure-safe integrity report display is added
sample_only trust gate is preserved
no live calls / no credentials guard is present
CI command bridge smoke is added
generated command bridge docs are added
no recommendation output is enforced
```
