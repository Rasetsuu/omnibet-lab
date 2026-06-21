# OmniBet Lab

Local-first football prediction and evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, **v240 silver promotion preview**, **v241 review queue report**, **v242 sample market review patch**, **v243 silver fact preview bundle**, **v244 silver preview cache**, **v245 historical import contracts**, **v246 historical import plan preview**, **v247 historical source manifest validation**, **v248 local historical source verification**, **v249 bronze candidate preview**, **v250 bronze preview classification**, **v251 bronze preview field-schema checks**, **v252 bronze validation batch**, and **v253 provider/data beta slice**.

OmniBet is a paper-only research tool for building, testing, and reviewing football prediction/value workflows without future leakage.

```text
raw/source samples
→ normalized warehouse/contracts
→ identity + market mapping
→ compressed data packs
→ feature snapshots
→ no-future-leak walk-forward evaluation
→ odds/CLV paper-only analysis
→ Rust runtime CLIs
→ Tauri desktop UI
→ downloadable Windows/Linux beta artifacts
→ final market-terminal GUI
```

## Status

```text
Desktop/release infrastructure: beta, actively stabilizing
Rust runtime: real but still early
Python research layer: broad, still too large, planned migration target
Prediction accuracy: not proven
Mode: PAPER_ONLY
```

## What works now

- Offline deterministic data samples and compressed JSONL.GZ data packs.
- Rust provider metadata/status/snapshot contracts with credential-status-only reporting.
- Rust offline provider sample parsers for The Odds API-style odds/markets and API-Football-style fixtures/live state.
- Rust bronze snapshot cache writer/verifier for materializing provider parser outputs into JSONL.GZ tables.
- Rust canonical market registry for safe provider alias resolution before bronze-to-silver promotion.
- Rust identity, market, silver-readiness, review-queue, and silver-preview cache gates.
- Rust historical import contract validation for point-in-time leakage gates.
- Rust historical import plan preview for offline source/window task planning.
- Rust historical source manifest validation for declared local candidate sources.
- Rust historical source verification for local existence, SHA-256, and row-count checks.
- Rust quarantined bronze-candidate preview rows from verified local source files.
- Rust bronze preview row classification for fixture/result, odds, and lineup/event-context rows.
- Rust bronze preview field-schema checks for classified rows.
- Rust batched bronze value validation, review-reason summary, readiness summary, and read-only desktop surface contract.
- Rust provider/data beta readiness matrix for priority provider adapters and historical coverage targets.
- Rust offline provider adapter request/response contracts with local fixture validation.
- Tauri desktop shell with command bridge to allowlisted Rust CLIs and local offline workflows.

## Provider / storage chain

```text
v234 provider runtime contracts
→ v235 offline provider parsers
→ v236 bronze snapshot cache
→ v237 market registry
→ v238 silver market mapping preview
→ v239 identity mapping preview
→ v240 combined silver promotion preview
→ v241 review queue report
→ v242 sample market review patch
→ v243 silver fact preview bundle
→ v244 silver preview cache
→ v245 historical import contracts
→ v246 historical import plan preview
→ v247 historical source manifest validation
→ v248 local historical source verification
→ v249 bronze candidate preview
→ v250 bronze preview classification
→ v251 bronze preview field-schema checks
→ v252 bronze validation batch
→ v253 provider/data beta slice
→ v254 offline adapter contracts
```

## Offline provider adapter contracts

The v254 direction defines offline request/response contracts for priority beta provider adapters.

Priority adapter contracts:

```text
odds_provider_snapshot_v1 -> the_odds_api
football_fixture_event_provider_v1 -> api_football
```

Local fixtures:

```text
data/provider_fixtures/v254/odds_provider_snapshot.sample.json
data/provider_fixtures/v254/football_fixture_event.sample.json
```

Health rows report:

```text
adapter id
provider id
fixture loaded
contract ok
normalization targets
blockers
```

CI safety remains locked:

```text
paper only: true
network calls allowed in CI: false
credentials stored in repo: false
live fetch enabled: false
fixture only in CI: true
```

The desktop can show adapter contracts, fixture status, missing fields, and normalization targets, but live fetch remains disabled until safe credential handling and non-CI adapter smokes are added.

## Actual beta direction

The target beta is a real prediction/betting research app, not only infrastructure.

The beta must support:

```text
larger historical data
provider adapters
walk-forward evaluation
calibration
CLV and no-vig comparisons
paper ledger
usable market terminal
```

The project is moving to batched PRs so each merged unit advances multiple related product/backend pieces.

## Bigger-picture plan

```text
1. Desktop/runtime stability
2. Provider ingestion contracts
3. Bronze raw snapshot storage
4. Canonical market + identity mapping
5. Silver fact preview and review safety
6. Larger historical import
7. Gold feature generation
8. Walk-forward evaluation and calibration
9. Odds/no-vig/CLV/paper ledger
10. Market-terminal GUI and bilet builder
```

We are now in layer 6.

## Final GUI target

The final desktop GUI is a market terminal and bilet-builder quality app, not a simple dashboard.

It should support:

```text
upcoming matches
live matches
match prediction terminal
bilet builder / same-game ticket builder
player props and scorer markets
corners/cards/offsides/shots/goals/period/qualification markets
market mapping review
paper ledger
source health
model lab
```

## Local tests

Python/smoke checks:

```bash
python python_lab/compile_python_sources.py
bash tools/run_all_local_tests.sh
python python_lab/provider_runtime_smoke.py --root . --out reports/local_v234_provider_runtime.json
python python_lab/provider_offline_samples_smoke.py --root . --out reports/local_v235_provider_offline_samples.json
python python_lab/bronze_snapshot_cache_smoke.py --root . --out reports/local_v236_bronze_snapshot_cache_static.json
python python_lab/market_registry_smoke.py --root . --out reports/local_v237_market_registry.json
python python_lab/silver_market_mapping_preview_smoke.py --root . --out reports/local_v238_silver_market_mapping_preview.json
python python_lab/identity_mapping_preview_smoke.py --root . --out reports/local_v239_identity_mapping_preview.json
python python_lab/silver_promotion_preview_smoke.py --root . --out reports/local_v240_silver_promotion_preview.json
python python_lab/review_queue_report_smoke.py --root . --out reports/local_v241_review_queue_report.json
python python_lab/market_review_patch_smoke.py --root . --out reports/local_v242_market_review_patch.json
python python_lab/silver_fact_preview_bundle_smoke.py --root . --out reports/local_v243_silver_fact_preview_bundle.json
python python_lab/silver_preview_cache_smoke.py --root . --out reports/local_v244_silver_preview_cache.json
python python_lab/historical_import_contract_smoke.py --root . --out reports/local_v245_historical_import_contract.json
python python_lab/historical_import_plan_smoke.py --root . --out reports/local_v246_historical_import_plan.json
python python_lab/historical_source_files_smoke.py --root . --out reports/local_v247_historical_source_files.json
python python_lab/historical_source_verification_smoke.py --root . --out reports/local_v248_historical_source_verification.json
python python_lab/bronze_candidate_preview_smoke.py --root . --out reports/local_v249_bronze_candidate_preview.json
python python_lab/bronze_preview_classification_smoke.py --root . --out reports/local_v250_bronze_preview_classification.json
python python_lab/bronze_preview_field_schema_smoke.py --root . --out reports/local_v251_bronze_preview_field_schema.json
python python_lab/bronze_validation_batch_smoke.py --root . --out reports/local_v252_bronze_validation_batch.json
python python_lab/provider_data_beta_smoke.py --root . --out reports/local_v253_provider_data_beta.json
python python_lab/provider_adapter_contracts_smoke.py --root . --out reports/local_v254_provider_adapter_contracts.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml bronze_cache
cargo test --manifest-path rust-core/Cargo.toml bronze_candidate_v249
cargo test --manifest-path rust-core/Cargo.toml bronze_classify_v250
cargo test --manifest-path rust-core/Cargo.toml bronze_field_schema_v251
cargo test --manifest-path rust-core/Cargo.toml bronze_validation_v252
cargo test --manifest-path rust-core/Cargo.toml provider_beta_v253
cargo test --manifest-path rust-core/Cargo.toml provider_adapter_v254
cargo test --manifest-path rust-core/Cargo.toml market_registry
cargo test --manifest-path rust-core/Cargo.toml silver_market
cargo test --manifest-path rust-core/Cargo.toml idmap_v239
cargo test --manifest-path rust-core/Cargo.toml silver_promote_v240
cargo test --manifest-path rust-core/Cargo.toml review_queue_v241
cargo test --manifest-path rust-core/Cargo.toml market_patch_v242
cargo test --manifest-path rust-core/Cargo.toml silver_fact_v243
cargo test --manifest-path rust-core/Cargo.toml silver_cache_v244
cargo test --manifest-path rust-core/Cargo.toml historical_import_v245
cargo test --manifest-path rust-core/Cargo.toml historical_plan_v246
cargo test --manifest-path rust-core/Cargo.toml historical_sources_v247
cargo test --manifest-path rust-core/Cargo.toml historical_verify_v248
```

## Accuracy roadmap

The next accuracy work is:

1. Import larger historical datasets with strict point-in-time boundaries.
2. Expand league-specific train/test coverage.
3. Compare baseline Poisson, gold-feature heuristic, and trained models on the same walk-forward windows.
4. Track log loss, Brier score, calibration, paper ROI, CLV, and no-vig baseline deltas.
5. Add event/xG/lineup/rest/travel/context features only when they are timestamp-safe.
6. Keep every candidate strategy paper-only until it survives enough history and market comparison.
