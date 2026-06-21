# OmniBet Lab

Local-first football prediction and betting-evaluation research lab.

Current merged baseline: **v181-v228 beta release train** plus **v229 desktop release stabilization**, **v230 portable runtime lookup hardening**, **v231 release/source foundation**, **v232 final GUI market terminal contract**, **v233 storage v2 big-data foundation**, **v234 Rust provider runtime foundation**, **v235 offline provider sample parsers**, **v236 bronze snapshot cache**, **v237 canonical market registry**, **v238 silver market mapping preview**, **v239 identity mapping preview**, and **v240 silver promotion preview**.

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

## What works now

- Offline deterministic data samples and compressed JSONL.GZ data packs.
- Rust pack verification, typed readers, simple inference, odds/value reports, and model comparison commands.
- Rust storage-v2 metadata contract for the big-data warehouse direction.
- Rust provider metadata/status/snapshot contracts with credential-status-only reporting.
- Rust offline provider sample parsers for The Odds API-style odds/markets and API-Football-style fixtures/live state.
- Rust bronze snapshot cache writer/verifier for materializing provider parser outputs into JSONL.GZ tables.
- Rust canonical market registry for safe provider alias resolution before bronze-to-silver promotion.
- Rust silver market mapping preview for resolved market rows and blocked review rows.
- Rust fixture/team/player identity preview for safe provider entity resolution before silver fact promotion.
- Rust combined silver promotion preview gate for market + identity readiness.
- Rust review queue report for unresolved market/entity rows.
- Tauri desktop shell with command bridge to allowlisted Rust CLIs and local offline workflows.
- Manual Windows/Linux GitHub Actions desktop build workflow.
- Final GUI market-terminal target is documented as a bilet-builder quality Windows/Linux app, not a dashboard-only predictor.

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
```

The current sample is intentionally not silver-ready because `special_combo_unknown` remains unresolved in the market review queue.

## Review queue report

The v241 direction turns silver-promotion blockers into explicit human-review rows.

Expected offline report:

```text
total review rows: 1
market review rows: 1
identity review rows: 0
review required: true
silver ready after review: false
blocked provider key: special_combo_unknown
blocked kind: market_mapping
```

A market review row must require:

```text
canonical_market_id
market_family
settlement_rule
selection_scope
line_required
player_required
lineup_required
correlation_group
```

Safety policy:

```text
auto approval is forbidden
review rows block silver readiness
promotion before review is forbidden
training dataset promotion is forbidden
```

## Silver promotion preview

The v240 direction combines market and identity readiness before any silver fact promotion.

Expected offline preview:

```text
market review count: 1
identity review count: 0
blocked count: 1
silver ready: false
blocked reason: unresolved_market_mappings
blocked market: special_combo_unknown
```

This means all fixture/team/player identities resolve, but silver readiness is still blocked because one provider market has no approved canonical alias and settlement rule.

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
python python_lab/provider_runtime_smoke.py --root . --out reports/local_v234_provider_runtime.json
python python_lab/provider_offline_samples_smoke.py --root . --out reports/local_v235_provider_offline_samples.json
python python_lab/bronze_snapshot_cache_smoke.py --root . --out reports/local_v236_bronze_snapshot_cache_static.json
python python_lab/market_registry_smoke.py --root . --out reports/local_v237_market_registry.json
python python_lab/silver_market_mapping_preview_smoke.py --root . --out reports/local_v238_silver_market_mapping_preview.json
python python_lab/identity_mapping_preview_smoke.py --root . --out reports/local_v239_identity_mapping_preview.json
python python_lab/silver_promotion_preview_smoke.py --root . --out reports/local_v240_silver_promotion_preview.json
python python_lab/review_queue_report_smoke.py --root . --out reports/local_v241_review_queue_report.json
```

Rust checks:

```bash
cargo test --manifest-path rust-core/Cargo.toml bronze_cache
cargo test --manifest-path rust-core/Cargo.toml market_registry
cargo test --manifest-path rust-core/Cargo.toml silver_market
cargo test --manifest-path rust-core/Cargo.toml idmap_v239
cargo test --manifest-path rust-core/Cargo.toml silver_promote_v240
cargo test --manifest-path rust-core/Cargo.toml review_queue_v241
cargo run --manifest-path rust-core/Cargo.toml --bin omnibet-bronze-cache -- \
  --out build/bronze_cache/v236_offline_samples
```

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
