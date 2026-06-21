# OmniBet Lab

Local-first football prediction and evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, **v240 silver promotion preview**, **v241 review queue report**, **v242 sample market review patch**, **v243 silver fact preview bundle**, **v244 silver preview cache**, **v245 historical import contracts**, **v246 historical import plan preview**, **v247 historical source manifest validation**, **v248 local historical source verification**, **v249 bronze candidate preview**, **v250 bronze preview classification**, **v251 bronze preview field-schema checks**, **v252 bronze validation batch**, **v253 provider/data beta slice**, **v254 offline adapter contracts**, **v255 provider normalization preview**, and **v256 source terminal report**.

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
- Tauri desktop source view for loading and rendering the source-terminal report.
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
```

## Desktop source view

The v257 direction wires the source-terminal report into the Tauri desktop UI.

Added desktop pieces:

```text
Tauri command: load_source_terminal_report
Frontend API: loadSourceTerminalReport
Renderer: tauri-app/src/source_terminal.js
Bundled sample: tauri-app/src/source-terminal.sample.json
Page: source-terminal
```

Desktop panels:

```text
source-terminal-summary
source-terminal-readiness
source-terminal-actions
source-terminal-blockers
```

Expected sample status:

```text
adapter count: 2
adapter OK count: 2
normalized total rows: 5
odds snapshot candidates: 3
fixture result candidates: 1
event context candidates: 1
```

The page is read-only and paper-only. It shows local report status and bundled sample data for inspection.

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
python python_lab/source_terminal_report_smoke.py --root . --out reports/local_v256_source_terminal_report.json
python python_lab/source_terminal_desktop_smoke.py --root . --out reports/local_v257_source_terminal_desktop.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml source_terminal_v256
```
