# OmniBet Lab

Cross-sport prediction/value-betting research lab with a Rust-first runtime direction and a Python research/backfill layer.

Current merged milestone: **v37 — offline provider event timeline join**.
Next target: **v38 — settlement and outcome truth skeleton**.

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
- `docs/` — milestone docs from v4 through v38.

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
- Bookmaker odds / Bet Builder market contract.
- Provider candidate matrix and dynamic market discovery schema.
- Raw market snapshot warehouse tables and unknown market queue.
- Canonical resolver tables and alias-mapping smoke.
- Safe market alias application to raw snapshots.
- The Odds API-style offline event-market adapter skeleton.
- API-Football-style offline live-state adapter skeleton.
- Offline provider event timeline join.
- Settlement and outcome truth skeleton.
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

```bash
cd python_lab
python local_backfill_runner.py \
  --preset tiny-smoke \
  --out ../build/v26_smoke \
  --pack-name football_v26_tiny_smoke
```

See [`docs/v26_local_backfill.md`](docs/v26_local_backfill.md).

## v27 Parquet+ZSTD storage path

v27 keeps JSONL.GZ as the CI/Rust baseline but adds an optional local heavy storage path.

See [`docs/v27_parquet_zstd_storage.md`](docs/v27_parquet_zstd_storage.md).

## v28 real-source acquisition catalog

v28 records the real data-source plan in repo-owned, CI-checked form.

See [`docs/v28_source_acquisition.md`](docs/v28_source_acquisition.md).

## v29 feature priority and live data contract

v29 locks the core feature policy and defines live data as append-only point-in-time snapshots.

See [`docs/v29_feature_live_contract.md`](docs/v29_feature_live_contract.md).

## v30 bookmaker odds and Bet Builder market contract

v30 normalizes Romanian `cota/cote` as decimal odds and defines sportsbook market rows, Bet Builder legs, and same-game correlation warnings.

See [`docs/v30_bookmaker_market_contract.md`](docs/v30_bookmaker_market_contract.md).

## v31 provider matrix and market discovery schema

v31 separates manual/reference sportsbooks from official automation sources and defines dynamic market discovery.

See [`docs/v31_provider_market_discovery.md`](docs/v31_provider_market_discovery.md).

## v32 raw market snapshot warehouse

v32 makes market discovery real SQLite storage:

```text
raw_market_snapshots
market_mapping_rules
unknown_market_queue
```

See [`docs/v32_market_snapshot_warehouse.md`](docs/v32_market_snapshot_warehouse.md).

## v33 canonical resolver

v33 adds canonical storage and alias resolution for teams, players, markets, and selections.

See [`docs/v33_canonical_resolver.md`](docs/v33_canonical_resolver.md).

## v34 safe market alias apply

v34 applies exact high-confidence market aliases onto raw market snapshots while preserving unknown markets.

See [`docs/v34_market_alias_apply.md`](docs/v34_market_alias_apply.md).

## v35 The Odds API offline adapter

v35 adds the first provider-style offline adapter skeleton for event odds/markets.

See [`docs/v35_the_odds_api_offline_adapter.md`](docs/v35_the_odds_api_offline_adapter.md).

## v36 API-Football offline adapter

v36 adds the first provider-style offline adapter skeleton for fixture state, lineups, events, and statistics.

See [`docs/v36_api_football_offline_adapter.md`](docs/v36_api_football_offline_adapter.md).

## v37 provider event timeline

v37 joins the v35 odds sample and v36 match-state sample into one canonical event timeline.

See [`docs/v37_provider_event_timeline.md`](docs/v37_provider_event_timeline.md).

## v38 settlement and outcome truth

v38 adds the first deterministic market-grading skeleton over the v37 timeline.

```bash
cd python_lab
python settlement_truth_smoke.py \
  --db ../build/omnibet_v38_settlement_truth.sqlite \
  --odds-input ../data/samples/the_odds_api_event_markets_sample.json \
  --state-input ../data/samples/api_football_live_state_sample.json \
  --link-input ../data/samples/provider_event_link_sample.v37.json \
  --out ../reports/ci_v38_settlement_truth.json
```

It proves:

```text
v37 timeline builds
settlement_rules are written
outcome_truth rows are written
1X2 / totals / corners / shots-on-target / handicap examples are evaluated
player prop without player truth is unsupported
unknown combo market remains unmapped
```

See [`docs/v38_settlement_truth.md`](docs/v38_settlement_truth.md).

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
