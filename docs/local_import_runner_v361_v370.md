# v361-v370 Local Import Runner and Storage-Backed Green Sample

This batched phase turns the green sample from a bundled JSON-only proof into a generated local mini-pack path.

It still remains `sample_only`. It does not unlock terminal predictions, bilet builder, staking, profitability claims, or real recommendations.

## Included versions

```text
v361 local mini-pack loader
v362 source manifest hash verifier
v363 fixture/odds/settlement row parser
v364 generated walk-forward green report
v365 generated baseline metrics report
v366 generated calibration/CLV report
v367 storage-writer integration for mini-pack outputs
v368 desktop reload from generated green report
v369 sample_only trust gate preservation
v370 local import runner smoke
```

## Local mini-pack files

```text
data/local_sources/v361_v370/fixtures.jsonl
data/local_sources/v361_v370/odds.jsonl
data/local_sources/v361_v370/settlements.jsonl
data/local_sources/v361_v370/source_manifest.json
```

The source manifest includes row counts and SHA-256 content hashes for all three JSONL files.

## Generated report surface

The generated report sample is exposed through:

```text
tauri-app/src/generated-green-sample.sample.json
tauri-app/src/generated_green.js
```

The desktop page displays:

```text
source/storage manifest status
walk-forward report status
baseline sample metrics
calibration sample bins
paper CLV summary
sample_only trust gate
```

## Rust implementation

The Rust module lives in:

```text
rust-core/src/local_import_runner_v361.rs
```

It provides:

```text
parse_local_import_runner_contract
parse_source_manifest
parse_jsonl_rows
sha256_hex
validate_local_import_runner_contract
validate_source_manifest
verify_manifest_hashes
build_generated_green_report
load_minipack
write_generated_green_report
```

## Safety constraints

The runner enforces:

```text
paper_only = true
local_first = true
live provider calls = false
credential values = false
real money recommendations = false
validated_paper = false
trust_status = sample_only
terminal_prediction_allowed = false
bilet_builder_allowed = false
```

## Acceptance

v361-v370 is accepted when:

```text
local mini-pack loader is defined
source manifest hash verifier is defined
fixture/odds/settlement parser is defined
generated walk-forward green report is defined
generated baseline metrics report is defined
generated calibration/CLV report is defined
storage-writer integration is defined
desktop reload from generated report is added
trust gate remains sample_only
no recommendation output is enforced
Rust validation module is added
Python smoke and CI are added
no live calls, credentials, or recommendations are introduced
```
