# v1031-v1060 Football-Data Batch 003 — 30k+ pack

This milestone starts the 30k+ historical data phase.

## Goal

Batch 003 scales beyond Batch 002 into a multi-season, multi-league Football-Data pack:

```text
Batch 001: one league smoke path
Batch 002: top-five leagues, one season, ~1k-3k rows
Batch 003: multi-season grid, target >=30,000 eligible completed match rows
```

## Source grid

Batch 003 declares:

```text
10 seasons × 18 competitions = 180 possible CSV sources
```

Seasons:

```text
1516, 1617, 1718, 1819, 1920, 2021, 2122, 2223, 2324, 2425
```

Competition codes:

```text
E0, E1, E2,
D1, D2,
SP1, SP2,
I1, I2,
F1, F2,
N1, B1, P1, T1, G1,
SC0, SC1
```

Some Football-Data files may be missing or unavailable for specific season/code combinations. That is acceptable. The final local data gate is not source-count based; it is row-count based:

```text
aggregate eligible rows >= 30,000
```

## Download

```bash
bash scripts/download_football_data_batch_003.sh
```

The downloader skips already-present files and records failures. Missing sources are allowed as long as the final aggregate passes the 30k gate.

## Run

```bash
bash scripts/run_football_data_batch_003.sh
```

The runner:

1. Imports every present raw CSV with the Rust `omnibet-football-data-importer`.
2. Aggregates all generated `matches.jsonl` files.
3. Aggregates all generated `odds.jsonl` files.
4. Writes a source report.
5. Runs the Rust `omnibet-feature-count-gate`.
6. Runs the Rust `omnibet-baseline-eval`.
7. Runs the Batch 003 `--require-data` gate.

## Generated local outputs

```text
data/local_historical/football_data/normalized/batch_003_multi_season_30k/matches.jsonl
data/local_historical/football_data/normalized/batch_003_multi_season_30k/odds.jsonl
data/local_historical/football_data/normalized/batch_003_multi_season_30k/source_report.json
reports/feature_counts.json
reports/model_eval.json
reports/ci_v1031_v1060_football_data_batch_003.json
```

The Matches GUI reads:

```text
reports/feature_counts.json
reports/model_eval.json
```

so Batch 003 immediately surfaces in the normal UI.

## CI behavior

CI does not download external data and does not require raw CSVs.

It validates only the manifest/runner/docs contract:

```bash
python python_lab/v1031_football_data_batch_003_check.py
```

The full data gate is local/manual:

```bash
python python_lab/v1031_football_data_batch_003_check.py --require-data
```

## Product safety

Even after 30k+ rows, this is still not a real-money betting model.

Expected after successful Batch 003:

```text
eligible rows: >=30,000
feature counts: useful
baseline eval: useful benchmark
real_model_ready: false
next: feature builder v2, stronger baseline models, calibration and CLV gates
```

No staking output, live calls, betting advice, or profit claims are introduced.
