# v331-v340 Baseline Training Reports

This batched phase adds the first baseline report runner shape after the Rust walk-forward evaluator.

It does not claim prediction quality. It only produces baseline reports when evaluator gates pass. If the v321-v330 evaluator reports blocked status, this phase must emit blocked reports instead of fake metrics.

## Included versions

```text
v331 1X2 no-vig baseline report runner
v332 totals no-vig baseline report runner
v333 BTTS no-vig baseline report runner
v334 simple Poisson/Elo/team-strength candidate report
v335 blocked report when evaluator gates fail
v336 model artifact manifest
v337 baseline metrics report writer
v338 desktop model report status panel
v339 trust gate integration
v340 baseline training smoke
```

## Rust implementation

The Rust module lives in:

```text
rust-core/src/baseline_reports_v331.rs
```

It provides:

```text
parse_baseline_reports_contract
validate_baseline_reports_contract
no_vig_from_decimal_prices
build_baseline_training_report
write_baseline_training_report
```

## Gate behavior

Training/report metrics require:

```text
walk_forward_status == ready_for_evaluation
walk_forward_ready == true
```

Otherwise, output status is:

```text
blocked
```

and baseline rows keep metric fields null.

## Baselines

```text
no_vig_1x2_v331
no_vig_totals_v332
no_vig_btts_v333
poisson_elo_team_strength_candidate_v334
```

The no-vig helper computes market-implied probabilities from decimal prices and normalizes them to remove overround. In this phase it is preview-only unless the evaluator gates pass.

## Trust gate

Default trust status:

```text
blocked_sample
```

Allowed statuses:

```text
blocked_sample
sample_only
experimental_paper
validated_paper
```

Terminal prediction and bilet-builder actions remain blocked until later gates pass.

## Files

```text
configs/baseline_training_reports.v331_v340.json
data/modeling/v331_v340/baseline_training_reports.sample.json
docs/baseline_training_reports_v331_v340.md
rust-core/src/baseline_reports_v331.rs
tauri-app/src/baseline-reports.sample.json
tauri-app/src/baseline_reports.js
python_lab/baseline_training_reports_smoke.py
.github/workflows/v331_v340_baseline_training_reports.yml
```

## Acceptance

v331-v340 is accepted when:

```text
1X2 no-vig runner is defined
totals no-vig runner is defined
BTTS no-vig runner is defined
simple Poisson/Elo candidate report is defined
blocked reports are emitted when evaluator gates fail
model artifact manifest is defined
baseline metrics report writer is defined
desktop model report status panel is added
trust gate integration is defined
Rust module is added
Python smoke and CI are added
no live calls, credentials, or recommendation output are introduced
```
