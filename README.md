# OmniBet Lab

Local-first football prediction and betting-evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**.

OmniBet is not a tipster bot. It is a paper-only research tool for building, testing, and reviewing football prediction/value workflows without future leakage.

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
```

## Status

```text
Desktop/release infrastructure: beta, actively stabilizing
Rust runtime: real but still early
Python research layer: broad, still too large, planned migration target
Prediction accuracy: not proven for real betting
Betting mode: PAPER_ONLY
```

Do not treat any output as a betting recommendation. No milestone should claim profit, staking confidence, or real edge without large out-of-sample validation, calibration, no-vig bookmaker baselines, and CLV evidence.

## Repository layout

- `rust-core/` — Rust runtime library and CLIs: `omnibet-pack`, `omnibet-infer`, `omnibet-value`, `omnibet-model`.
- `tauri-app/` — Tauri desktop shell and command bridge.
- `python_lab/` — research/backfill/smoke layer. This is intentionally being reduced over time as stable pieces migrate to Rust.
- `data_packs/` — tiny compressed CI/runtime packs.
- `data/` — deterministic samples only, not production-scale data.
- `configs/` — milestone and workflow contracts.
- `docs/` — architecture, milestone notes, migration plans, and release notes.
- `tools/` — local/CI helpers and diagnostics.
- `cpp-core/` — early portability experiment, not the main runtime.

## What works now

- Offline deterministic data samples and compressed JSONL.GZ data packs.
- Rust pack verification, typed readers, simple inference, odds/value reports, and model comparison commands.
- Python smoke pipeline for adapters, warehouse contracts, feature snapshots, walk-forward checks, dashboards, review queues, source-cache promotion, and beta workflows.
- Tauri desktop shell with command bridge to allowlisted Rust CLIs and local offline workflows.
- Manual Windows/Linux GitHub Actions desktop build workflow.
- Portable desktop artifact staging with the Rust runtime CLIs bundled beside the app.
- Desktop diagnostics workflow that has passed on Linux and Windows in the v7 diagnostics path.

## What is not done yet

- Model edge is not proven.
- Real provider/live-source ingestion is not production-ready.
- GUI needs human review and polish.
- Python-to-Rust migration is incomplete.
- Release artifacts are beta downloads, not signed production installers.
- The app remains local/offline-first and paper-only.

## Desktop beta builds

The manual workflow is:

```text
.github/workflows/desktop_beta_builds.yml
```

It builds on:

```text
windows-latest
ubuntu-latest
```

The artifact contains:

```text
build/desktop-downloads/package/
  OmniBet-Lab.exe or omnibet-lab
  omnibet-pack(.exe)
  omnibet-infer(.exe)
  omnibet-value(.exe)
  omnibet-model(.exe)
  bin/
  rust-core/target/debug/  # compatibility path for current Tauri bridge
  data/
  data_packs/football_core_v1/
  README_RUN.txt
DESKTOP_BUILD_MANIFEST.json
Tauri bundle outputs when produced by the runner
```

The current Tauri backend still expects the developer-style `rust-core/target/debug` runtime path unless `OMNIBET_CLI_DIR` is set, so the portable package stages the release-built CLIs into that compatibility path as well as beside the app and in `./bin`.

To build from GitHub:

1. Open **Actions**.
2. Choose **OmniBet Desktop Beta Builds**.
3. Click **Run workflow**.
4. Download the Windows/Linux artifact.
5. Unzip it and run the app from the `package` directory.

## Local tests

Python/smoke checks:

```bash
python python_lab/compile_python_sources.py
bash tools/run_all_local_tests.sh
```

Tauri/Rust checks require Rust, Node, and platform desktop dependencies:

```bash
cargo test --manifest-path rust-core/Cargo.toml
cargo test --manifest-path tauri-app/src-tauri/Cargo.toml
cd tauri-app
npm install --foreground-scripts --loglevel warn
npm run build
```

The chat sandbox used for this project can run Python/Node checks, but real Rust/Tauri validation is intentionally delegated to GitHub Actions when local Cargo is unavailable.

## Accuracy roadmap

The next accuracy work is not “make a prettier probability.” It is:

1. Import larger historical datasets with strict point-in-time boundaries.
2. Expand league-specific train/test coverage.
3. Compare baseline Poisson, gold-feature heuristic, and trained models on the same walk-forward windows.
4. Track log loss, Brier score, calibration, ROI-paper, CLV, and no-vig bookmaker baseline deltas.
5. Add event/xG/lineup/rest/travel/context features only when they are timestamp-safe.
6. Keep every candidate strategy paper-only until it survives enough history and market comparison.

## Python → Rust migration roadmap

Stable pieces should move from `python_lab/` to `rust-core/` in phases:

1. CSV/JSON/JSONL ingestion and typed row validation.
2. Data-pack creation, compression, hashing, and manifest verification.
3. Feature snapshot generation and leakage guards.
4. Walk-forward evaluation and calibration metrics.
5. Odds normalization, no-vig baseline, CLV, and paper ledger.
6. Provider/cache contracts once the schema is stable.
7. Desktop command workflows currently shelling out to Python.

Python should remain for fast experiments, notebooks, one-off data exploration, and provider prototypes until their contracts are stable.

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
