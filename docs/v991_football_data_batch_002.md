# v991-v1030 Football-Data Batch 002

This milestone starts the larger historical data phase after the GUI learned to read both `feature_counts.json` and `model_eval.json`.

## Goal

Scale from the single-league Batch 001 contract to a top-five-league, one-season pack:

```text
Batch 001: one league, 200-500 row smoke path
Batch 002: top-five leagues, roughly 1k-3k completed rows
Batch 003: multi-season pack, 10k-30k+ completed rows
```

## Source family

Football-Data.co.uk CSV files.

Batch 002 targets the 2024/25 season for:

| Country | League | Code | URL |
|---|---|---:|---|
| England | Premier League | E0 | https://www.football-data.co.uk/mmz4281/2425/E0.csv |
| Spain | La Liga | SP1 | https://www.football-data.co.uk/mmz4281/2425/SP1.csv |
| Italy | Serie A | I1 | https://www.football-data.co.uk/mmz4281/2425/I1.csv |
| Germany | Bundesliga | D1 | https://www.football-data.co.uk/mmz4281/2425/D1.csv |
| France | Ligue 1 | F1 | https://www.football-data.co.uk/mmz4281/2425/F1.csv |

## Download raw CSVs locally

```bash
bash scripts/download_football_data_batch_002.sh
```

Raw files are written under:

```text
data/local_historical/football_data/raw/<competition>/2024_2025/*.csv
```

Raw CSVs are ignored by git by default.

## Run Batch 002

```bash
bash scripts/run_football_data_batch_002.sh
```

The runner:

1. Verifies all five raw CSVs exist.
2. Runs the Rust `omnibet-football-data-importer` per league.
3. Concatenates aggregate `matches.jsonl` and `odds.jsonl`.
4. Runs the Rust `omnibet-feature-count-gate`.
5. Runs the Rust `omnibet-baseline-eval`.
6. Runs the Batch 002 data check with `--require-data`.

## Aggregate outputs

```text
data/local_historical/football_data/normalized/batch_002_top5_2024_2025/matches.jsonl
data/local_historical/football_data/normalized/batch_002_top5_2024_2025/odds.jsonl
reports/feature_counts.json
reports/model_eval.json
reports/ci_v991_v1030_football_data_batch_002.json
```

The Matches GUI can read the two reports after PR #197:

```text
reports/feature_counts.json
reports/model_eval.json
```

## CI behavior

CI does not download external data and does not require raw CSVs.

It runs only the manifest/contract check:

```bash
python python_lab/v991_football_data_batch_002_check.py
```

The full data gate is local/manual:

```bash
python python_lab/v991_football_data_batch_002_check.py --require-data
```

## Product safety

This still does not create a strong betting model.

Expected after successful Batch 002:

```text
eligible rows: likely >= 1000
baseline eval: available
real_model_ready: false
next: stronger models and/or Batch 003 multi-season pack
```

No betting advice, staking output, live calls, or profit claims are introduced.
