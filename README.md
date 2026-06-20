# OmniBet Lab

Local-first football prediction and betting-evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, and **v237 canonical market registry**.

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
→ GitHub Releases desktop beta assets
→ final market-terminal/bilet-builder GUI
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

- `rust-core/` — Rust runtime library and CLIs: `omnibet-pack`, `omnibet-infer`, `omnibet-value`, `omnibet-model`, `omnibet-bronze-cache`.
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
- Rust storage-v2 metadata contract for the big-data warehouse direction.
- Rust provider metadata/status/snapshot contracts with credential-status-only reporting.
- Rust offline provider sample parsers for The Odds API-style odds/markets and API-Football-style fixtures/live state.
- Rust bronze snapshot cache writer/verifier for materializing provider parser outputs into JSONL.GZ tables.
- Rust canonical market registry for safe provider alias resolution before bronze-to-silver promotion.
- Rust silver market mapping preview direction for resolved market rows and blocked review rows.
- Python smoke pipeline for adapters, warehouse contracts, feature snapshots, walk-forward checks, dashboards, review queues, source-cache promotion, and beta workflows.
- Tauri desktop shell with command bridge to allowlisted Rust CLIs and local offline workflows.
- Manual Windows/Linux GitHub Actions desktop build workflow.
- Portable desktop artifact staging with the Rust runtime CLIs bundled beside the app.
- Desktop diagnostics workflow that has passed on Linux and Windows in the v7 diagnostics path.
- Temporary PR validation has proven Windows/Linux downloadable desktop artifacts can be built and uploaded by GitHub Actions.
- Final GUI market-terminal target is documented as a bilet-builder quality Windows/Linux app, not a dashboard-only predictor.

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

The Tauri backend can resolve packaged runtime CLIs from `OMNIBET_CLI_DIR`, the app/package root, `./bin`, and developer fallback paths.

To build from GitHub:

1. Open **Actions**.
2. Choose **OmniBet Desktop Beta Builds**.
3. Click **Run workflow**.
4. Download the Windows/Linux artifact.
5. Unzip it and run the app from the `package` directory.

## GitHub Releases

The planned user-facing release workflow is:

```text
.github/workflows/desktop_release.yml
```

It is manual-only and creates draft/prerelease GitHub Release assets:

```text
OmniBet-Lab-Windows-<tag>.zip
OmniBet-Lab-Linux-<tag>.tar.gz
```

Users should be able to open **Releases**, download the archive for their platform, extract it, and run:

```text
Windows: OmniBet-Lab.exe
Linux:   ./omnibet-lab
```

Release builds remain PAPER_ONLY until the model is validated at scale.

## Storage v2 big-data direction

The current runtime pack format remains useful for small deterministic packs:

```text
jsonl.gzip tables
manifest.json
row counts
compressed byte counts
compression ratios
SHA-256 hashes
Rust verification/readback
```

For large historical and training data, the v233 direction is:

```text
Bronze raw provider snapshots  -> json.zstd / jsonl.zstd, temporary
Silver canonical football facts -> parquet.zstd, long-term
Gold training features          -> parquet.zstd, long-term
Model artifacts                 -> model binary + JSON manifest
Recent runtime cache            -> SQLite or small local JSONL.GZ
```

This preserves current JSONL.GZ compatibility while moving the real warehouse toward Parquet+Zstd for columnar scans, partition pruning, and large feature tables.

## Provider runtime foundation

The v234 provider runtime direction moves source ingestion contracts into Rust before adding any live HTTP fetchers.

Initial providers:

```text
The Odds API      odds snapshots, market discovery, historical odds
API-Football      fixtures, live state, lineups, events, statistics, players
Sportmonks        secondary fixtures, livescores, events, lineups, players, odds
Betfair Exchange  exchange market reference and historical backtest
```

Provider runtime rules:

```text
providers disabled by default
manual enable required
credential status only: present/missing
credential values never stored or displayed
no live provider calls in CI
all snapshots require observed_at + payload_sha256
```

The first Rust module for this is `rust-core/src/provider.rs`.

## Offline provider sample parsers

The v235 direction parses saved provider payloads into typed Rust snapshots without network calls:

```text
The Odds API-style event markets
→ fixture snapshot
→ odds snapshots
→ market discovery snapshots
→ unknown-market review flags

API-Football-style live state
→ fixture snapshot
→ event snapshots
→ lineup player snapshots
→ team statistic snapshots
```

This gives the provider layer real typed rows before live fetching exists, and keeps CI fully offline and credential-free.

## Bronze snapshot cache

The v236 direction materializes parsed provider sample rows into a verifiable bronze cache:

```text
build/bronze_cache/v236_offline_samples/
  manifest.json
  tables/
    source_manifests.jsonl.gz
    fixtures.jsonl.gz
    odds.jsonl.gz
    market_discovery.jsonl.gz
    events.jsonl.gz
    lineups.jsonl.gz
    statistics.jsonl.gz
```

Expected offline demo row counts:

```text
source_manifests: 2
fixtures: 2
odds: 17
market_discovery: 8
events: 4
lineups: 8
statistics: 12
TOTAL: 53
```

The cache manifest records row counts, uncompressed/compressed byte counts, table SHA-256 hashes, source payload manifests, and safety flags. Unknown markets such as `special_combo_unknown` must remain `needs_mapping_review=true`.

CLI:

```bash
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-bronze-cache -- \
  --out build/bronze_cache/v236_offline_samples \
  --cache-id v236_offline_provider_samples \
  --created-at 2026-06-20T00:00:00Z
```

## Canonical market registry

The v237 direction adds safe provider-market alias resolution before bronze rows can become silver facts.

Initial canonical markets:

```text
match_result_1x2
handicap
total_goals
total_corners
team_shots_on_target
player_shots_on_target
```

Initial The Odds API aliases:

```text
h2h                    -> match_result_1x2
spreads                -> handicap
totals                 -> total_goals
corners                -> total_corners
shots_on_target        -> team_shots_on_target
player_shots_on_target -> player_shots_on_target
```

Unknown markets cannot be auto-promoted. The sample market `special_combo_unknown` must stay review-only with promotion blocked.

Player prop markets such as `player_shots_on_target` require player context and lineup/expected-minutes context before confident modeling.

## Silver market mapping preview

The v238 direction previews safe market mapping before final silver promotion.

Expected offline preview from the saved market sample:

```text
raw bronze market rows: 8
unique provider market groups: 7
resolved groups: 6
review groups: 1
blocked promotions: 1
```

Resolved groups are preview-only rows with canonical market id, family, settlement rule, line/player/lineup requirements, bookmaker count, event count, and outcome count.

Review rows are not promoted. The sample `special_combo_unknown` remains blocked until a human-approved registry alias and settlement rule exist.

## World Cup live capture foundation

The v231 direction is a World Cup 2026 capture campaign:

```text
provider status
→ fixture discovery
→ odds snapshots
→ live state snapshots
→ lineups/events
→ paper prediction snapshot
→ post-match settlement
→ CLV/outcome report
→ leak-safe training dataset promotion
```

Initial planned providers are The Odds API, API-Football, Sportmonks, and Betfair Exchange. They are disabled by default, credential values are never stored/displayed, and CI performs no live provider calls.

Training is allowed only after matches are final and only for future predictions. Random train/test splits are not allowed; walk-forward validation and bookmaker no-vig baselines are required.

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

Every market must show model trust, required data coverage, fair odds, bookmaker odds when available, and correlation/contradiction warnings for same-game tickets.

## Local tests

Python/smoke checks:

```bash
python python_lab/compile_python_sources.py
bash tools/run_all_local_tests.sh
python python_lab/world_cup_live_capture_smoke.py --root . --out reports/local_v231_world_cup_live_capture.json
python python_lab/storage_v2_smoke.py --root . --out reports/local_v233_storage_v2.json
python python_lab/provider_runtime_smoke.py --root . --out reports/local_v234_provider_runtime.json
python python_lab/provider_offline_samples_smoke.py --root . --out reports/local_v235_provider_offline_samples.json
python python_lab/bronze_snapshot_cache_smoke.py --root . --out reports/local_v236_bronze_snapshot_cache_static.json
python python_lab/market_registry_smoke.py --root . --out reports/local_v237_market_registry.json
python python_lab/silver_market_mapping_preview_smoke.py --root . --out reports/local_v238_silver_market_mapping_preview.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml bronze_cache
cargo test --manifest-path rust-core/Cargo.toml market_registry
cargo test --manifest-path rust-core/Cargo.toml silver_market
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-bronze-cache -- \
  --out build/bronze_cache/v236_offline_samples
python python_lab/bronze_snapshot_cache_smoke.py \
  --root . \
  --cache-dir build/bronze_cache/v236_offline_samples \
  --out reports/local_v236_bronze_snapshot_cache.json
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
