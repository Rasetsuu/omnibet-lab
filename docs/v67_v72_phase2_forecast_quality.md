# v67-v72 Phase 2 Forecast Quality

This milestone starts the actual forecast-quality phase.

## v67 historical importer

Creates deterministic offline historical fixture rows with:

```text
event id
kickoff time
home/away names
pre-event ratings
pre-event form
rest days
final score
```

## v68 settled training dataset

Builds settled training rows from the historical rows.

Each row contains only pre-event features plus the final label:

```text
rating_diff
form_diff
rest_diff
home_bias
label_home_win
```

The leakage guard remains explicit: features are available before kickoff only.

## v69 chronological backtest

Uses a chronological split:

```text
train before 2025-01-01
test from 2025-01-01 onward
```

Reports forecast metrics and baseline metrics.

## v70 calibration

Reports calibration bins and expected calibration error.

## v71 model registry

Writes a model card/registry entry with:

```text
model id
version
model family
target
training data sha
historical data sha
split
metrics
safety flags
```

## v72 prediction/explanation UI

Adds a Models page renderer for:

```text
model card
chronological backtest metrics
calibration bins
example explanations/top factors
```

The UI explicitly states that probabilities are research forecasts, not recommendations.

## Smoke

```bash
python python_lab/phase2_forecast_smoke.py \
  --root . \
  --out-dir build/phase2_forecast_v67_v72 \
  --ui-sample tauri-app/src/phase2-forecast.sample.json \
  --out reports/ci_v67_v72_phase2_forecast.json
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
