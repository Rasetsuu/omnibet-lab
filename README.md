# OmniBet Lab

Local-first football prediction and evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, **v240 silver promotion preview**, **v241 review queue report**, **v242 sample market review patch**, **v243 silver fact preview bundle**, **v244 silver preview cache**, **v245 historical import contracts**, **v246 historical import plan preview**, **v247 historical source manifest validation**, **v248 local historical source verification**, **v249 bronze candidate preview**, **v250 bronze preview classification**, **v251 bronze preview field-schema checks**, **v252 bronze validation batch**, **v253 provider/data beta slice**, **v254 offline adapter contracts**, and **v255 provider normalization preview**.

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
```

## Source terminal report

The v256 direction combines provider-side beta pieces into one desktop-facing source terminal report.

Inputs:

```text
omnibet.provider_adapter_validation_report.v254
omnibet.provider_normalization_preview_bundle.v255
```

Report contents:

```text
adapter count
adapter OK count
normalized total rows
normalized row counts by type
readiness badges
blocker summary
locked desktop actions
```

Expected sample status:

```text
adapter count: 2
adapter OK count: 2
normalized total rows: 5
odds snapshot candidates: 3
fixture result candidates: 1
event context candidates: 1
source terminal visible: true
```

Allowed desktop actions:

```text
inspect adapters
inspect rows
export report
```

Locked desktop actions:

```text
live provider calls
bronze write
model evaluation
model training
real-money execution
```

This makes the source panel useful for inspection while keeping downstream use locked.

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
python python_lab/provider_runtime_smoke.py --root . --out reports/local_v234_provider_runtime.json
python python_lab/provider_offline_samples_smoke.py --root . --out reports/local_v235_provider_offline_samples.json
python python_lab/bronze_snapshot_cache_smoke.py --root . --out reports/local_v236_bronze_snapshot_cache_static.json
python python_lab/provider_data_beta_smoke.py --root . --out reports/local_v253_provider_data_beta.json
python python_lab/provider_adapter_contracts_smoke.py --root . --out reports/local_v254_provider_adapter_contracts.json
python python_lab/provider_normalization_preview_smoke.py --root . --out reports/local_v255_provider_normalization_preview.json
python python_lab/source_terminal_report_smoke.py --root . --out reports/local_v256_source_terminal_report.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml provider_beta_v253
cargo test --manifest-path rust-core/Cargo.toml provider_adapter_v254
cargo test --manifest-path rust-core/Cargo.toml provider_normalize_v255
cargo test --manifest-path rust-core/Cargo.toml source_terminal_v256
```
