# v73-v78 Forecast Scale-Up

This milestone improves Phase 2 before moving to product packaging.

## v73 larger historical dataset

Creates a deterministic offline dataset with 240 historical rows across 10 seasons.

## v74 rolling-origin evaluation

Runs rolling-origin folds:

```text
train on past seasons
test on one future season
```

This is stronger than a single split because it checks stability across multiple seasons.

## v75 model comparison

Compares transparent model variants:

```text
baseline_rate
rating_only
rating_form
full_scorecard
```

Metrics:

```text
Brier score
log loss
accuracy at 0.5
```

## v76 feature ablation

Compares the full scorecard against smaller variants and reports deltas.

Positive deltas mean the full model performed better on this offline sample.

## v77 calibration and stability

Reports:

```text
calibration bins
expected calibration error
fold metric ranges
```

## v78 model-lab UI payload

Adds:

```text
tauri-app/src/model-lab.sample.json
```

and expands the Models page renderer to show:

```text
model comparison
feature ablation
calibration/stability
example forecast explanations
```

## Smoke

```bash
python python_lab/forecast_scaleup_smoke.py \
  --out-dir build/forecast_scaleup_v73_v78 \
  --ui-sample tauri-app/src/model-lab.sample.json \
  --out reports/ci_v73_v78_forecast_scaleup.json
```

## Safety

```text
Paper/offline research only.
No recommendation output.
No staking or financial guidance.
No live calls in CI.
No API key values.
No shell execution.
```
