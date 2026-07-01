# v941-v960 Football-Data Batch 001

This milestone prepares the first controlled real historical batch for the Rust data spine.

## Why this exists

The current clean v1 path has only a tiny sample. Batch 001 is the first controlled step toward moving from:

```text
3 / 200 eligible rows
```

to:

```text
>= 200 / 200 eligible rows
```

Batch 001 is deliberately source-manifested and local-first. The repository does not pretend the data is present until the raw CSV is actually downloaded/provided locally.

## Source

Batch 001 target source:

```text
Provider: Football-Data.co.uk
Country: England
Division: E0
Competition: england_premier_league
Season: 2024_2025
URL: https://www.football-data.co.uk/mmz4281/2425/E0.csv
```

## Local raw path

```text
data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv
```

Raw CSV is not committed by default. This keeps the repository lightweight and avoids accidentally committing large/private/local datasets.

## Manual download

```bash
mkdir -p data/local_historical/football_data/raw/england_premier_league/2024_2025
curl -L https://www.football-data.co.uk/mmz4281/2425/E0.csv \
  -o data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv
```

## Run Batch 001

```bash
bash scripts/run_football_data_batch_001.sh
```

The runner uses the Rust importer and Rust feature-count gate:

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-football-data-importer -- \
  --input data/local_historical/football_data/raw/england_premier_league/2024_2025/E0.csv \
  --competition england_premier_league \
  --season 2024_2025 \
  --out data/local_historical/football_data/normalized/england_premier_league/2024_2025

cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-feature-count-gate -- \
  --matches data/local_historical/football_data/normalized/england_premier_league/2024_2025/matches.jsonl \
  --out reports/feature_counts.json \
  --min-rows 200 \
  --source-label football_data_england_premier_league_2024_2025
```

## Generated outputs

```text
data/local_historical/football_data/normalized/england_premier_league/2024_2025/matches.jsonl
data/local_historical/football_data/normalized/england_premier_league/2024_2025/odds.jsonl
data/local_historical/football_data/normalized/england_premier_league/2024_2025/import_report.json
reports/feature_counts.json
reports/ci_v941_v960_football_data_batch_001.json
```

## CI behavior

The PR workflow runs a manifest check only:

```bash
python python_lab/v941_football_data_batch_001_check.py
```

It does not download external data in CI and does not require the raw CSV to be committed.

The full data gate is local/manual:

```bash
python python_lab/v941_football_data_batch_001_check.py --require-data
```

## Product rule

Passing the count gate can allow a baseline training run to start, but it does not make the model good.

After Batch 001:

```text
baseline_training_allowed: may become true
real_model_ready: still false
next required gate: walk-forward evaluation + calibration
```

No profit claims, no staking output, and no live provider calls are introduced by this milestone.
