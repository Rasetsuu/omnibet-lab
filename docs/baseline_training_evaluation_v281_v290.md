# v281-v290 Baseline Training and Evaluation

This batched phase defines the first baseline model and evaluation contracts after the historical dataset foundation.

It does not claim prediction accuracy, does not train on real large datasets yet, and does not enable real-money betting recommendations. It defines the contracts and gates needed before any future model can appear in the market terminal.

## Included versions

```text
v281 1X2 baseline contract
v282 totals/BTTS baseline contract
v283 no-vig market baseline comparison
v284 calibration report contract
v285 walk-forward evaluation report
v286 paper CLV report contract
v287 model trust gate
v288-v290 market terminal prediction table preparation
```

## v281 - 1X2 baseline contract

Initial 1X2 baselines:

```text
market-implied no-vig baseline
Poisson/Elo-style research candidate
```

The no-vig market baseline is the first mandatory comparator. Research candidates must beat or explain themselves against it before receiving trust.

## v282 - Totals/BTTS baseline contract

Initial totals and BTTS baselines:

```text
totals market-implied no-vig baseline
BTTS market-implied no-vig baseline
```

These remain paper-only and require settled labels before evaluation.

## v283 - No-vig market baseline comparison

Every model report must compare against the market-implied no-vig baseline.

Required comparison fields include:

```text
no_vig_baseline_delta
no_vig_probability
edge_vs_no_vig
```

No model can be trusted just because it outputs probabilities.

## v284 - Calibration report contract

Required calibration metrics:

```text
ECE
MCE
calibration bins
reliability table
```

Classification metrics:

```text
log_loss
brier_score
accuracy_for_reference_only
```

Accuracy alone is not enough for betting research.

## v285 - Walk-forward evaluation report

Random splits remain forbidden.

Required safety checks:

```text
feature_observed_at_lte_prediction_time
label_created_after_settlement
no_random_shuffle_split
market_family_specific_validation
settlement_coverage_threshold_met
```

Minimum before trust:

```text
minimum_windows_before_trust: 3
minimum_predictions_per_market_family: 300
```

## v286 - Paper CLV report contract

Paper CLV rows require closing odds and never allow real stake.

Required fields:

```text
paper_ticket_id
canonical_fixture_id
market_key
selection_key
paper_price_decimal
closing_price_decimal
no_vig_price_decimal
paper_clv
captured_at
closing_captured_at
```

## v287 - Model trust gate

Allowed trust statuses:

```text
unsupported
sample_only
low_data
experimental
paper_watch
validated_paper
```

Default status:

```text
sample_only
```

Minimum status for market terminal probability display:

```text
paper_watch
```

Minimum status for bilet builder:

```text
validated_paper
```

## v288-v290 - Market terminal prediction table preparation

Prepared columns:

```text
canonical_fixture_id
market_key
selection_key
model_probability
fair_odds_decimal
bookmaker_odds_decimal
no_vig_probability
edge_vs_no_vig
trust_status
blockers
allowed_action
```

Allowed actions:

```text
inspect
paper_watch_only
```

Forbidden actions:

```text
recommend_real_bet
place_bet
auto_stake
claim_profitability
```

## Rust module

Rust-facing validation lives in:

```text
rust-core/src/baseline_eval_v281.rs
```

It parses and validates:

```text
configs/baseline_training_evaluation.v281_v290.json
```

## Files

```text
configs/baseline_training_evaluation.v281_v290.json
data/training/v281_v290/baseline_training_evaluation.sample.json
docs/baseline_training_evaluation_v281_v290.md
rust-core/src/baseline_eval_v281.rs
python_lab/baseline_training_evaluation_smoke.py
.github/workflows/v281_v290_baseline_training_evaluation.yml
```

## Acceptance

v281-v290 is accepted when:

```text
1X2, totals, and BTTS baselines are defined
no-vig market baseline comparison is required
calibration and walk-forward reports are required
paper CLV requires closing odds
model trust gate blocks unvalidated models
market terminal prediction table is paper-only
random splits and unsettled training are forbidden
Rust module parses/validates the contract
Python smoke validates contract/sample/docs/module/workflow
```
