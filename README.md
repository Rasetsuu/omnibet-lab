# OmniBet Lab

Local-first football prediction and evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, **v240 silver promotion preview**, **v241 review queue report**, **v242 sample market review patch**, **v243 silver fact preview bundle**, **v244 silver preview cache**, **v245 historical import contracts**, **v246 historical import plan preview**, **v247 historical source manifest validation**, **v248 local historical source verification**, **v249 bronze candidate preview**, **v250 bronze preview classification**, **v251 bronze preview field-schema checks**, **v252 bronze validation batch**, **v253 provider/data beta slice**, **v254 offline adapter contracts**, **v255 provider normalization preview**, **v256 source terminal report**, **v257 desktop source view**, **v258 source report generation**, **v259 source generate-refresh flow**, **v260 source terminal filters and row details**, **v261 upcoming/live fixture source contract**, **v262-v265 source-to-context bridge**, and **v266-v270 storage v2 compression foundation**.

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
- Rust offline provider normalization preview rows for odds, fixture-result, and event-context candidates.
- Rust source-terminal report combining adapter health, normalized preview counts, readiness badges, blockers, and locked desktop actions.
- Rust-facing Storage V2 compression contract validation for JSONL.Zstd, Parquet.Zstd, provider cache manifests, writer migration, and walk-forward loader shape.
- Offline upcoming/live fixture source contract for date-range and live-state rows.
- Offline source-to-context bridge for odds snapshots, live snapshots, retention policy, and prediction-ready context bundles.
- Tauri desktop source view for loading and rendering the source-terminal report.
- Tauri desktop workflow for generating the local source-terminal report file.
- Tauri desktop source view button flow for generating and refreshing the local source report.
- Tauri desktop source filters, adapter details, and normalized row sample inspection.
- Tauri desktop live-source bridge sample panel for live/upcoming matches, odds preview, and context readiness.
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
```

## Storage V2 compression foundation

The v266-v270 bridge turns the earlier Storage V2 roadmap into stricter Rust-facing contracts and samples.

```text
v266 JSONL.Zstd raw snapshot contract
v267 Parquet.Zstd Silver/Gold metadata contract
v268 Rust provider cache manifest direction
v269 Silver/Gold writer migration plan
v270 walk-forward dataset loader shape
```

Contract, sample, docs, Rust module, and smoke:

```text
configs/storage_v2_compression.v266_v270.json
data/storage_v2/v266_v270/storage_v2_compression.sample.json
docs/storage_v2_compression_v266_v270.md
rust-core/src/storage_v2_compression_v266.rs
python_lab/storage_v2_compression_smoke.py
```

This foundation preserves JSONL.GZ compatibility for small CI/runtime packs while moving large historical/training paths toward temporary JSONL.Zstd Bronze and long-term Parquet.Zstd Silver/Gold. It does not ingest large real datasets or train models yet.

## Source-to-context bridge

The v262-v265 bridge batches the remaining live-source phase into one coherent offline-safe slice.

```text
v262 odds snapshot source contract
v263 desktop upcoming/live matches sample panel
v264 live snapshot storage and retention contract
v265 prediction-ready match context bundle
```

Contract, sample, docs, desktop panel, and smoke:

```text
configs/source_to_context_bridge.v262_v265.json
data/provider_fixtures/v262_v265/source_to_context_bridge.sample.json
tauri-app/src/live-source.sample.json
tauri-app/src/live_source.js
docs/source_to_context_bridge_v262_v265.md
python_lab/source_to_context_bridge_smoke.py
```

This bridge is still paper-only and sample-first. It does not enable live provider calls, real prediction confidence, model fitting, Bronze/Silver/Gold writes, or real-money recommendations.

## Upcoming/live fixture source contract

The v261 direction defines how OmniBet asks what matches exist now and soon before the later odds, live-snapshot, and prediction-context phases.

```text
fixture date-range request contract
live fixture-state request contract
normalized scheduled/live fixture rows
status/phase/freshness metadata
lineup/event/stat availability flags
prediction-readiness and blocker reasons
read-only, paper-only, no CI live provider calls
```

Contract and docs:

```text
configs/upcoming_live_fixture_source.v261.json
data/provider_fixtures/v261/upcoming_live_fixture_source.sample.json
docs/upcoming_live_fixture_source_v261.md
python_lab/upcoming_live_fixture_source_smoke.py
```

## Source Terminal filters and row details

The v260 direction extends the desktop source view with local row filters and sample inspection.

```text
provider/type/readiness/blocker filters
adapter health details
normalized preview row samples
next-action hints
read-only, paper-only, no live provider calls
```

Contract and docs:

```text
configs/source_terminal_filters_details.v260.json
docs/source_terminal_filters_details_v260.md
python_lab/source_terminal_filters_details_smoke.py
```

## Source generate-refresh flow

The v259 direction lets the desktop source view generate and refresh its local report.

Workflow id:

```text
generate_source_terminal_report
```

Frontend helper:

```text
generateAndRenderSourceTerminal
```

Buttons:

```text
generate-source-terminal-report
generate-source-terminal-report-topbar
```

Flow:

```text
click Generate source report
run the allowlisted local workflow
write .omnibet-local/reports/local_v256_source_terminal_report.json
reload the source view
```

The flow is local-only and paper-only. It writes a report for inspection and then refreshes the desktop source view.

## Next phase: v271-v280 historical dataset foundation

The next larger phase should move from storage shape into historical dataset build planning:

```text
v271 historical source coverage matrix
v272 league/tournament import window targets
v273 historical source manifest bundle
v274 settlement and closing-odds target contract
v275 coverage/readiness report
v276-v280 first leak-safe dataset build plan
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
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml source_terminal_v256
cargo test --manifest-path rust-core/Cargo.toml storage_v2_compression
```
