# Desktop release data-batch packaging follow-up

This follow-up fixes the gap found when testing the extracted desktop package directly.

## Problem

The release archive is not a full repository checkout. The previous package included the app and legacy runtime files, but not the new data-batch scripts and Python helpers.

Running this inside an extracted package failed:

```bash
bash scripts/download_football_data_batch_002.sh
bash scripts/run_football_data_batch_002.sh
bash scripts/download_football_data_batch_003.sh
bash scripts/run_football_data_batch_003.sh
```

because `scripts/` was absent.

Also, the repo scripts originally used `cargo run`, which is correct for development but not ideal inside a portable release package.

## Fix

The package now includes:

- `scripts/download_football_data_batch_002.sh`
- `scripts/run_football_data_batch_002.sh`
- `scripts/download_football_data_batch_003.sh`
- `scripts/run_football_data_batch_003.sh`
- needed Football-Data batch configs
- needed Python batch checks/runners
- `omnibet-football-data-importer`
- `omnibet-feature-count-gate`
- `omnibet-baseline-eval`

The Batch 002 shell runner and Batch 003 Python runner now prefer bundled binaries under `./bin` and fall back to `cargo run` only in a development checkout.

## Expected extracted-package usage

```bash
cd package
bash scripts/download_football_data_batch_002.sh
bash scripts/run_football_data_batch_002.sh

# or the 30k path
bash scripts/download_football_data_batch_003.sh
bash scripts/run_football_data_batch_003.sh
```

Generated reports stay local:

```text
reports/feature_counts.json
reports/model_eval.json
```

The Matches GUI can read those reports.
