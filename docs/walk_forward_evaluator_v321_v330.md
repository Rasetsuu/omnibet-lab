# v321-v330 Rust Dataset Loader and Walk-Forward Evaluator

This batched phase adds the first Rust no-leak walk-forward evaluator spine.

It does not train models. It blocks training unless the dataset windows, timestamps, labels, market-family splits, and coverage gates are safe.

## Included versions

```text
v321 dataset window loader
v322 prediction_time boundary checks
v323 feature_observed_at <= prediction_time checks
v324 label_created_after_settlement checks
v325 market-family split checks
v326 no-random-split enforcement
v327 evaluation-window report writer
v328 coverage/readiness gate integration
v329 desktop evaluator status panel
v330 walk-forward evaluator smoke
```

## Rust implementation

The Rust module lives in:

```text
rust-core/src/walk_forward_v321.rs
```

It provides:

```text
parse_walk_forward_contract
parse_walk_forward_sample
validate_walk_forward_contract
evaluate_walk_forward_sample
write_walk_forward_report
```

## Required safety checks

```text
prediction_time_within_evaluation_window
feature_observed_at_lte_prediction_time
label_created_at_gte_settled_at
label_created_at_gt_prediction_time
settled_at_gt_prediction_time
market_family_matches_window
no_random_split
coverage_gate_checked
```

## Coverage gates

```text
minimum_eval_rows: 100
minimum_settlement_coverage_ratio: 0.95
minimum_closing_odds_coverage_ratio: 0.60
minimum_market_family_rows: 30
```

The bundled sample intentionally fails coverage and contains one feature timestamp failure. That proves the evaluator blocks unsafe training instead of emitting fake readiness.

## Report output

Local report target:

```text
.omnibet-local/reports/local_v321_v330_walk_forward_evaluator.json
```

The report includes:

```text
status
windows
total_rows
eligible_rows
blocked_rows
random_split_used
recommendation_output_present
safety_checks
coverage_readiness
blockers
next_action
```

## Desktop panel

The desktop status panel shows:

```text
summary
window rows
safety checks
coverage readiness
next phase
```

Files:

```text
tauri-app/src/walk-forward-evaluator.sample.json
tauri-app/src/walk_forward_evaluator.js
```

## Forbidden outputs

The evaluator contract forbids:

```text
real_money_recommendation
stake_size
profitability_claim
live_provider_fetch
random_train_test_split
```

## Files

```text
configs/walk_forward_evaluator.v321_v330.json
data/evaluation/v321_v330/walk_forward_evaluator.sample.json
docs/walk_forward_evaluator_v321_v330.md
rust-core/src/walk_forward_v321.rs
tauri-app/src/walk-forward-evaluator.sample.json
tauri-app/src/walk_forward_evaluator.js
python_lab/walk_forward_evaluator_smoke.py
.github/workflows/v321_v330_walk_forward_evaluator.yml
```

## Acceptance

v321-v330 is accepted when:

```text
dataset window loader is defined
prediction-time boundaries are checked
feature timestamps must be <= prediction_time
labels must be created after settlement and after prediction_time
market-family split checks exist
random split is forbidden
evaluation report writer exists
coverage readiness gates are integrated
desktop evaluator status panel is added
Rust validation module is added
Python smoke and CI are added
no live calls, credentials, or recommendation output are introduced
```
