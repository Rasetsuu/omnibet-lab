# OmniBet Lab

Cross-sport prediction/value-betting research lab with a Rust-first runtime direction and a Python research/backfill layer.

Current merged milestone: **v28 — real-source acquisition catalog and local sync plan**.
Next target: **v29 — feature priority and live data contract**.

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
- `docs/` — milestone docs from v4 through v29.

## What works now

- Football warehouse and normalized match storage.
- Football-Data-style CSV results/odds adapter.
- StatsBomb public sample and scale pipeline.
- OpenFootball-style JSON adapter.
- Wyscout-style public match/event adapter.
- Multi-source identity candidate reports.
- Real-source acquisition catalog and local sync plan.
- Core feature-priority contract.
- Live data point-in-time snapshot contract.
- Compressed JSONL.GZ data packs and Python/Rust verification.
- Optional local Parquet+ZSTD warehouse-pack exporter for heavy data.
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

See [`docs/v26_local_backfill.md`](docs/v26_local_backfill.md).

## v27 Parquet+ZSTD storage path

v27 keeps JSONL.GZ as the CI/Rust baseline but adds an optional local heavy storage path:

```bash
python -m pip install -r requirements-storage.txt

cd python_lab
python export_parquet_zstd_pack.py \
  --db ../build/local_backfills/v26_run/omnibet_v26_backfill.sqlite \
  --out-dir ../build/local_backfills/v26_run/parquet_zstd_pack \
  --pack-name football_v27_local_parquet_zstd \
  --zstd-level 6
```

See [`docs/v27_parquet_zstd_storage.md`](docs/v27_parquet_zstd_storage.md).

## v28 real-source acquisition catalog

v28 records the real data-source plan in repo-owned, CI-checked form:

```bash
cd python_lab
python source_acquisition_catalog.py \
  --out ../reports/ci_v28_source_catalog.json \
  --write-example-config ../configs/source_acquisition.v28.example.json \
  --write-shell-plan ../build/v28_sync_sources_plan.sh
```

See [`docs/v28_source_acquisition.md`](docs/v28_source_acquisition.md).

## v29 feature priority and live data contract

v29 locks the core feature policy:

```text
core engine:
  must-have + high-value + refined medium-value

experimental only:
  travel / attendance / pitch condition until ablation proves value

postponed:
  weather / social media / vague sentiment / rumors
```

It also defines live data as append-only point-in-time snapshots:

```text
live_fixture_snapshots
live_event_snapshots
live_lineup_snapshots
live_stat_snapshots
live_odds_snapshots
```

CI-safe report:

```bash
cd python_lab
python feature_live_contract.py \
  --out ../reports/ci_v29_feature_live_contract.json \
  --write-config ../configs/feature_live_contract.v29.json
```

See [`docs/v29_feature_live_contract.md`](docs/v29_feature_live_contract.md).

## Storage direction

Current CI/local-smoke codec:

```text
JSONL.GZ + manifest.json
```

Preferred local heavy analytical codec:

```text
Parquet + ZSTD
DuckDB/Polars/PyArrow-compatible layout
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
