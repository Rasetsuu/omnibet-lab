# v341-v350 Calibration, CLV, and No-Vig Comparison Reports

This batched phase adds calibration, no-vig delta, and paper CLV report contracts after the walk-forward evaluator and baseline report gate.

It does not unlock betting, stake sizing, profitability claims, or real recommendations. If walk-forward or baseline reports are blocked, this phase emits blocked reports with metric fields left empty.

## Included versions

```text
v341 calibration report contract
v342 reliability table preview
v343 Brier/log-loss report shape
v344 no-vig baseline delta report
v345 paper CLV report shape
v346 closing-line value summary
v347 model trust gate update
v348 desktop calibration/CLV panel
v349 blocked report when baseline gates fail
v350 calibration/CLV smoke
```

## Rust implementation

The Rust module lives in:

```text
rust-core/src/calibration_clv_v341.rs
```

It provides:

```text
parse_calibration_clv_contract
validate_calibration_clv_contract
calibration_gap
brier_score
no_vig_delta
clv_decimal
build_blocked_calibration_clv_report
write_calibration_clv_report
```

## Gate behavior

Calibration, no-vig delta, and CLV metrics require:

```text
walk_forward_status == ready_for_evaluation
baseline_status == ready_for_baseline_reports
```

Otherwise, report status is:

```text
blocked
```

and metric fields remain null.

## Report families

```text
calibration bins / reliability table
Brier score / log-loss / ECE summary
no-vig model probability delta
paper CLV summary
trust gate update
```

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

Terminal prediction and bilet-builder actions stay locked until later gates pass.

## Files

```text
configs/calibration_clv_reports.v341_v350.json
data/modeling/v341_v350/calibration_clv_reports.sample.json
docs/calibration_clv_reports_v341_v350.md
rust-core/src/calibration_clv_v341.rs
tauri-app/src/calibration-clv.sample.json
tauri-app/src/calibration_clv.js
python_lab/calibration_clv_reports_smoke.py
.github/workflows/v341_v350_calibration_clv_reports.yml
```

## Acceptance

v341-v350 is accepted when:

```text
calibration report contract is defined
reliability table preview is defined
Brier/log-loss report shape is defined
no-vig baseline delta report is defined
paper CLV report shape is defined
closing-line value summary is defined
model trust gate update is defined
desktop calibration/CLV panel is added
blocked report is emitted when baseline gates fail
Rust validation module is added
Python smoke and CI are added
no live calls, credentials, or recommendation output are introduced
```
