# v351-v360 Green Evaluator Sample

This batched phase adds a tiny internally consistent local mini-pack that can pass evaluator, baseline, calibration, no-vig, and paper CLV sample gates without pretending to be production-ready.

It remains `sample_only`. It does not unlock terminal predictions, bilet builder, staking, profitability claims, or real recommendations.

## Included versions

```text
v351 local fixture/odds/settlement mini-pack contract
v352 source manifest hash checks for the mini-pack
v353 eligible walk-forward window sample
v354 baseline report sample with non-null metrics
v355 calibration sample with non-null bins
v356 paper CLV sample with closing odds
v357 desktop reload from green sample
v358 trust gate stays sample_only, not validated_paper
v359 no recommendation output enforcement
v360 green evaluator/baseline/calibration smoke
```

## Files

```text
configs/green_evaluator_sample.v351_v360.json
data/modeling/v351_v360/green_evaluator_sample.sample.json
rust-core/src/green_sample_v351.rs
tauri-app/src/green-evaluator-sample.sample.json
tauri-app/src/green_sample.js
python_lab/green_evaluator_sample_smoke.py
.github/workflows/v351_v360_green_evaluator_sample.yml
```

## Mini-pack contents

The bundled sample contains:

```text
2 fixture rows
4 prediction rows
3 market families
3 source manifests
closing odds for paper CLV
non-null baseline metrics
non-null calibration bins
non-null no-vig deltas
non-null paper CLV summaries
```

## No-leak constraints

Every prediction row must satisfy:

```text
feature_observed_at <= prediction_time
settled_at > prediction_time
label_created_at >= settled_at
```

The sample also forbids:

```text
random split
live provider calls
credential values
real recommendation output
validated_paper claims
```

## Trust gate

The trust gate intentionally stays:

```text
sample_only
```

and explicitly keeps disabled:

```text
terminal_prediction_allowed = false
bilet_builder_allowed = false
validated_paper = false
```

## Rust implementation

The Rust module validates both the contract and sample:

```text
parse_green_evaluator_sample_contract
parse_green_evaluator_sample
validate_green_evaluator_sample_contract
validate_green_evaluator_sample
```

## Acceptance

v351-v360 is accepted when:

```text
local mini-pack contract is defined
source manifest hash checks are defined
eligible walk-forward window sample is defined
baseline report has non-null sample metrics
calibration sample has non-null bins
paper CLV sample has closing odds
desktop reload from green sample is added
trust gate remains sample_only, not validated_paper
no recommendation output is enforced
Rust validation module is added
Python smoke and CI are added
no live calls, credentials, or recommendations are introduced
```
