# v921-v940 Rust feature-count gate

This milestone starts replacing the Python/static row-readiness path with a Rust-generated feature count report.

## Purpose

The gate reads canonical completed match JSONL, such as the `matches.jsonl` emitted by the v891 Football-Data importer, and writes a compact status report that the GUI and later training pipeline can consume.

Default output:

```text
reports/feature_counts.json
```

## Why this exists

The app must distinguish:

- generic sample rows
- completed match rows
- training-eligible completed match feature rows
- model/evaluation readiness

The current product truth remains data-starved until enough eligible rows exist. A row count alone does not make the model good.

## CLI

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-feature-count-gate -- \
  --matches data/local_historical/football_data/normalized/england_premier_league/2024_2025/matches.jsonl \
  --out reports/feature_counts.json \
  --min-rows 200 \
  --source-label football_data_england_premier_league_2024_2025
```

## Report semantics

The report includes:

- `input_rows`
- `parsed_rows`
- `completed_match_rows`
- `eligible_feature_rows`
- `duplicate_match_rows`
- `skipped_rows`
- `min_required_rows`
- `ready`
- `status`
- `baseline_training_allowed`
- `real_model_ready`
- `model_status`

Important distinction:

```text
baseline_training_allowed may become true after the count gate passes.
real_model_ready stays false until later walk-forward evaluation and calibration pass.
```

## Eligibility v921

A row is counted as eligible when it has:

- match id
- final/completed status
- match date
- home team
- away team
- final home goals
- final away goals

Duplicates are skipped by match id.

## GUI behavior

The Matches data-pipeline card now keeps the existing safe fallback but can upgrade itself when a generated Rust count report is available.

Fallback when no report is found:

```text
Completed row count: 3 / 200 required for v1
V1 readiness: Needs more rows
Real model: Locked until enough settled rows
```

Generated-report path:

```text
reports/feature_counts.json
../reports/feature_counts.json
./reports/feature_counts.json
feature_counts.json
```

When a report is loaded, the GUI shows:

- feature-count source
- `eligible_feature_rows / min_required_rows`
- count-gate readiness
- real model lock/eval status

The GUI still hides training/import controls from the normal match screen.

## Expected current behavior

With the existing tiny clean path, the product should still show:

```text
3 / 200
ready: false
status: needs_more_rows
```

Once Batch 001 lands, this report becomes the source that can move the GUI from `needs_more_rows` to `count_gate_passed_eval_required`.

## Product constraint

This is still paper-only research plumbing. It does not make profit claims and does not unlock staking output.
