# OmniBet Lab

Cross-sport prediction/value-betting research lab with a Rust-first runtime direction and a Python research/backfill layer.

Current merged milestone: **v25 — odds/CLV walk-forward paper backtest**.
Next target: **v26 — local-scale historical data backfill runner**.

OmniBet is not meant to be a simple score predictor. The project is building a local-first sports intelligence pipeline:

```text
raw data sources
→ normalized warehouse
→ identity resolution
→ compressed data packs
→ event/player/rules/market features
→ walk-forward model validation
→ odds/CLV paper-only evaluation
→ Rust runtime
→ Tauri desktop UI
```

## Current architecture

- `python_lab/` — research scripts, adapters, backfill, training/export, walk-forward tests.
- `rust-core/` — memory-safe runtime for pack verification, model loading/inference, odds/value reports.
- `tauri-app/` — desktop app skeleton and command bridge direction.
- `cpp-core/` — early std-only proof core kept for portability experiments.
- `data/` — tiny deterministic samples only.
- `data_packs/` — compressed JSONL.GZ packs used by CI/Rust readers.
- `docs/` — milestone docs from v4 through v26.

## What works now

- Football warehouse and normalized match storage.
- Football-Data-style CSV results/odds adapter.
- StatsBomb public sample and scale pipeline.
- OpenFootball-style JSON adapter.
- Wyscout-style public match/event adapter.
- Multi-source identity candidate reports.
- Compressed JSONL.GZ data packs and Python/Rust verification.
- Phase-aware football market registry.
- Extra-time / penalties / qualification modeling contract.
- `gold_match_phase_features`.
- Python model training/export to compact JSON artifacts.
- Rust runtime loading Python-exported models.
- No-future-leak walk-forward backtest.
- Odds/CLV walk-forward paper backtest.
- Paper-only ledger and CLV skeleton.
- Tauri UI command bridge to Rust CLIs.
- CI verifies major Python/Rust/data-pack gates.

## v25 odds/CLV smoke

`python_lab/odds_walk_forward_backtest.py` reads v23 multi-source odds snapshots, uses only past matches for probability priors, computes no-vig implied probabilities, selects positive-edge paper candidates, settles future match results, compares placed odds to closing odds for CLV, and writes `paper_backtest_bets`.

The bundled CI sample is intentionally tiny and not a model-quality claim:

```text
matches seen: 8
matches with odds: 3
paper bets: 3
wins/losses: 0 / 3
profit units: -3.0
ROI: -100%
avg CLV: negative in the smoke sample
all_paper_only: true
```

The value is structural: the market-evaluation loop exists.

## v26 local backfill

v26 adds a local-only historical backfill runner while keeping CI deterministic.

Tiny CI smoke:

```bash
cd python_lab
python local_backfill_runner.py \
  --preset tiny-smoke \
  --out ../build/v26_smoke \
  --pack-name football_v26_tiny_smoke

python verify_data_pack.py \
  --pack-dir ../build/v26_smoke/packs/football_v26_tiny_smoke
```

Local-scale shape:

```bash
cd python_lab
python local_backfill_runner.py \
  --out ../build/local_backfills/v26_run \
  --pack-name football_v26_local_backfill \
  --football-data-dir ../data/external/football-data \
  --statsbomb-dir ../data/external/statsbomb-open-data/data \
  --openfootball-dir ../data/external/openfootball \
  --wyscout-dir ../data/external/wyscout-style
```

See [`docs/v26_local_backfill.md`](docs/v26_local_backfill.md).

## Storage direction

Current CI/local-smoke codec:

```text
JSONL.GZ + manifest.json
```

This is deterministic, easy to verify, and already used by Rust pack readers.

For large future event/player/odds history, the next storage milestone should add:

```text
Parquet + ZSTD
DuckDB/Polars-compatible partitioned layout
source manifests + hashes + license metadata
```

The runtime app should not ship all historical raw data. It should ship compact model artifacts, identity maps, feature normalization metadata, market registry, and a live/recent cache.

## Betting honesty

OmniBet outputs are **PAPER_ONLY** until proven otherwise.

No milestone should claim profit or staking confidence without:

- large historical imports;
- no-future-leak walk-forward validation;
- calibration metrics: Brier/log loss/calibration curves;
- no-vig bookmaker baseline comparison;
- CLV validation at scale;
- market-specific settlement rules;
- player/lineup/injury/fatigue/event context.

## Local full test harness

```bash
bash tools/run_all_local_tests.sh
```

CI runs this harness on Ubuntu with Python and Rust installed.
