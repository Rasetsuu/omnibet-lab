# OmniBet Lab

Local-first football prediction and evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, **v240 silver promotion preview**, **v241 review queue report**, **v242 sample market review patch**, **v243 silver fact preview bundle**, **v244 silver preview cache**, **v245 historical import contracts**, **v246 historical import plan preview**, **v247 historical source manifest validation**, **v248 local historical source verification**, **v249 bronze candidate preview**, **v250 bronze preview classification**, **v251 bronze preview field-schema checks**, **v252 bronze validation batch**, **v253 provider/data beta slice**, **v254 offline adapter contracts**, **v255 provider normalization preview**, **v256 source terminal report**, **v257 desktop source view**, **v258 source report generation**, **v259 source generate-refresh flow**, **v260 source terminal filters and row details**, **v261 upcoming/live fixture source contract**, **v262-v265 source-to-context bridge**, **v266-v270 storage v2 compression foundation**, **v271-v280 historical dataset foundation**, **v281-v290 baseline training and evaluation**, **v291-v300 market terminal MVP**, **v301-v310 local dataset materialization preview**, **v311-v320 Rust Storage V2 writers**, **v321-v330 Rust walk-forward evaluator**, **v331-v340 baseline training reports**, and **v341-v350 calibration, CLV, and no-vig reports**.

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
- Rust bronze/silver/provider/historical/storage/model/market-terminal/materialization/evaluation/report contract validation gates.
- Rust Storage V2 preview writers for JSONL.Zstd, JSON.Zstd, and JSONL.Gzip with manifests, hashes, row counts, verification, and retention gates.
- Rust no-leak walk-forward evaluator for prediction-time boundaries, feature timestamp checks, settlement/label ordering, market-family splits, no-random-split enforcement, and coverage gates.
- Rust baseline report runner that blocks reports when walk-forward evaluator gates fail, plus no-vig preview, artifact manifest, and trust gate.
- Rust calibration/CLV report helper layer for calibration gaps, Brier score, no-vig deltas, CLV, blocked reports, and trust gate updates.
- Rust-facing Storage V2 compression contract validation for JSONL.Zstd, Parquet.Zstd, provider cache manifests, writer migration, and walk-forward loader shape.
- Offline upcoming/live fixture source contract for date-range and live-state rows.
- Offline source-to-context bridge for odds snapshots, live snapshots, retention policy, and prediction-ready context bundles.
- Baseline/evaluation foundation for no-vig baselines, calibration, walk-forward reports, paper CLV, trust gates, and market-terminal table shape.
- Local dataset materialization preview for manifests, fixture/odds/settlement/CLV previews, Bronze/Silver/Gold candidates, and readiness blockers.
- Tauri desktop source view, live-source bridge sample panel, market-terminal MVP panel, dataset-materialization preview panel, storage-writer status panel, walk-forward evaluator panel, baseline-report status panel, and calibration/CLV status panel.
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
→ v255 provider normalization preview
→ v256 source terminal report
→ v257 desktop source view
→ v258 source report generation
→ v259 source generate-refresh flow
→ v260 source terminal filters and row details
→ v261 upcoming/live fixture source contract
→ v262-v265 source-to-context bridge
→ v266-v270 storage v2 compression foundation
→ v271-v280 historical dataset foundation
→ v281-v290 baseline training and evaluation
→ v291-v300 market terminal MVP
→ v301-v310 local dataset materialization preview
→ v311-v320 Rust Storage V2 writers
→ v321-v330 Rust walk-forward evaluator
→ v331-v340 baseline training reports
→ v341-v350 calibration, CLV, and no-vig reports
```

## Execution roadmap

The v301+ execution roadmap is locked in [`docs/execution_roadmap_v301_plus.md`](docs/execution_roadmap_v301_plus.md).

It defines when to move stable logic from Python to Rust, when to implement the chosen compression path, when training starts, when prediction improvements begin, and how the UI evolves from bundled samples to generated local reports.

## Calibration, CLV, and no-vig reports

The v341-v350 bridge adds calibration, no-vig delta, and paper CLV report shapes after baseline report gates.

```text
v341 calibration report contract
v342 reliability table preview
v343 Brier/log-loss report shape
v344 no-vig baseline delta report
v345 paper CLV report shape
v346 closing-line value summary
v347 model trust gate update
v348 desktop calibration/CLV panel
v349 blocked report when baseline gates fail
v350 calibration/CLV smoke
```

Contract, sample, docs, Rust module, desktop renderer, and smoke:

```text
configs/calibration_clv_reports.v341_v350.json
data/modeling/v341_v350/calibration_clv_reports.sample.json
docs/calibration_clv_reports_v341_v350.md
rust-core/src/calibration_clv_v341.rs
tauri-app/src/calibration-clv.sample.json
tauri-app/src/calibration_clv.js
python_lab/calibration_clv_reports_smoke.py
```

The bundled sample is intentionally blocked because baseline reports are not ready. Calibration, Brier/log-loss, no-vig delta, and paper CLV values stay null until evaluator and baseline gates pass.

## Baseline training reports

The v331-v340 bridge adds the first baseline report runner shape after the Rust walk-forward evaluator.

```text
v331 1X2 no-vig baseline report runner
v332 totals no-vig baseline report runner
v333 BTTS no-vig baseline report runner
v334 simple Poisson/Elo/team-strength candidate report
v335 blocked report when evaluator gates fail
v336 model artifact manifest
v337 baseline metrics report writer
v338 desktop model report status panel
v339 trust gate integration
v340 baseline training smoke
```

The bundled sample is intentionally blocked because the v321-v330 walk-forward sample is not ready. Metric fields stay null and trust remains `blocked_sample`.

## Rust walk-forward evaluator

The v321-v330 bridge starts the no-leak Rust evaluator spine.

```text
v321 dataset window loader
v322 prediction_time boundary checks
v323 feature_observed_at <= prediction_time checks
v324 label_created_after_settlement checks
v325 market-family split checks
v326 no-random-split enforcement
v327 evaluation-window report writer
v328 coverage/readiness gate integration
v329 desktop evaluator status panel
v330 walk-forward evaluator smoke
```

The bundled sample intentionally fails one feature timestamp check and coverage gates. That is expected: the evaluator must block unsafe training rather than produce fake readiness.

## Rust Storage V2 writers

The v311-v320 bridge starts concrete Rust implementation for stable storage/compression paths.

```text
v311 JSONL.Zstd raw snapshot writer
v312 JSON.Zstd raw payload writer
v313 provider cache manifest writer
v314 Bronze manifest verification
v315 Silver table manifest writer
v316 Gold feature manifest writer
v317 row counts and content hashes
v318 retention/delete-after-promotion gates
v319 local storage writer smoke
v320 desktop storage writer status panel
```

Implemented now in Rust:

```text
jsonl.zstd
json.zstd
jsonl.gzip
```

Manifest-only now:

```text
parquet.zstd
```

## Local dataset materialization preview

The v301-v310 bridge starts turning contracts into generated local preview reports without live calls or real storage writes.

```text
v301 local source manifest bundle UI/report
v302 fixture/result local import preview
v303 odds local import preview
v304 settlement label preview
v305 closing-odds/CLV preview
v306 Bronze→Silver candidate materialization preview
v307 Gold feature candidate preview
v308 coverage readiness desktop panel
v309 local-only dataset build smoke
v310 market-terminal data reload from generated local preview
```

## Market terminal MVP

The v291-v300 bridge creates the first desktop-facing market terminal MVP surface.

```text
v291 market terminal data contract
v292 fixture/market selection state
v293 prediction table renderer
v294 trust/blocker display
v295 paper-only watchlist action
v296 market movement preview
v297 paper ledger preview
v298 source freshness badges
v299 disabled bilet-builder placeholder
v300 desktop market terminal MVP smoke
```

## Baseline training and evaluation foundation

The v281-v290 bridge defines baseline model/evaluation contracts before any model can be trusted in the market terminal.

```text
v281 1X2 baseline contract
v282 totals/BTTS baseline contract
v283 no-vig market baseline comparison
v284 calibration report contract
v285 walk-forward evaluation report
v286 paper CLV report contract
v287 model trust gate
v288-v290 market terminal prediction table preparation
```

## Historical dataset foundation

The v271-v280 bridge moves from storage shape into historical dataset build planning.

```text
v271 historical source coverage matrix
v272 league/tournament import window targets
v273 historical source manifest bundle
v274 settlement and closing-odds target contract
v275 coverage/readiness report
v276-v280 first leak-safe dataset build plan
```

## Next phase: v351-v360 real local data import hardening and first green evaluator sample

The next larger phase should prepare a tiny but internally consistent local sample that can pass evaluator gates without fake metrics:

```text
v351 local fixture/odds/settlement mini-pack contract
v352 source manifest hash checks for the mini-pack
v353 eligible walk-forward window sample
v354 baseline report sample with non-null metrics
v355 calibration sample with non-null bins
v356 paper CLV sample with closing odds
v357 desktop reload from green sample
v358 trust gate stays sample_only, not validated_paper
v359 no recommendation output enforcement
v360 green evaluator/baseline/calibration smoke
```

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

## Local tests

Python/smoke checks:

```bash
python python_lab/compile_python_sources.py
python python_lab/source_terminal_generate.py --root . --out reports/local_v258_generated_source_terminal_report.json
python python_lab/source_terminal_generation_smoke.py --root . --out reports/local_v258_source_terminal_generation.json
python python_lab/source_generate_refresh_smoke.py --root . --out reports/local_v259_source_generate_refresh.json
python python_lab/source_terminal_filters_details_smoke.py --root . --out reports/local_v260_source_terminal_filters_details.json
python python_lab/upcoming_live_fixture_source_smoke.py --root . --out reports/local_v261_upcoming_live_fixture_source.json
python python_lab/source_to_context_bridge_smoke.py --root . --out reports/local_v262_v265_source_to_context_bridge.json
python python_lab/storage_v2_compression_smoke.py --root . --out reports/local_v266_v270_storage_v2_compression.json
python python_lab/historical_dataset_foundation_smoke.py --root . --out reports/local_v271_v280_historical_dataset_foundation.json
python python_lab/baseline_training_evaluation_smoke.py --root . --out reports/local_v281_v290_baseline_training_evaluation.json
python python_lab/market_terminal_mvp_smoke.py --root . --out reports/local_v291_v300_market_terminal_mvp.json
python python_lab/local_dataset_materialization_preview.py --root . --out reports/local_v301_v310_dataset_materialization.json --market-terminal-out reports/local_v301_v310_market_terminal_preview.json
python python_lab/local_dataset_materialization_smoke.py --root . --out reports/local_v301_v310_local_dataset_materialization.json
python python_lab/storage_v2_writers_smoke.py --root . --out reports/local_v311_v320_storage_v2_writers.json
python python_lab/walk_forward_evaluator_smoke.py --root . --out reports/local_v321_v330_walk_forward_evaluator.json
python python_lab/baseline_training_reports_smoke.py --root . --out reports/local_v331_v340_baseline_training_reports.json
python python_lab/calibration_clv_reports_smoke.py --root . --out reports/local_v341_v350_calibration_clv_reports.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml source_terminal_v256
cargo test --manifest-path rust-core/Cargo.toml storage_v2_compression
cargo test --manifest-path rust-core/Cargo.toml historical_dataset_foundation
cargo test --manifest-path rust-core/Cargo.toml baseline_training_evaluation
cargo test --manifest-path rust-core/Cargo.toml market_terminal_mvp
cargo test --manifest-path rust-core/Cargo.toml local_dataset_materialization
cargo test --manifest-path rust-core/Cargo.toml storage_v2_writers
cargo test --manifest-path rust-core/Cargo.toml walk_forward_evaluator
cargo test --manifest-path rust-core/Cargo.toml baseline_reports
cargo test --manifest-path rust-core/Cargo.toml calibration_clv
```
