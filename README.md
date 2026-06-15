# OmniBet Lab v13

Cross-sport prediction/value-betting research tool.

v13 makes two important changes:

1. **Value trust gate**
   - `omnibet-value` no longer allows strong staking labels from an untrusted/simple model.
   - Default `model_trust = 0.25`.
   - Low trust outputs `PAPER ONLY - model trust too low`.

2. **Synthetic event-data demo**
   - Adds a separate demo DB and pack that finally activate:
     - `match_events`
     - `lineups`
     - `players`
     - `gold_goal_timing_features`
     - `gold_player_snapshots`

This is the first package where the detailed-data pipeline is non-empty.

## v13 commands

```bash
cd python_lab

python synthetic_event_demo.py \
  --base-db ../build/omnibet.sqlite \
  --demo-db ../build/omnibet_v13_event_demo.sqlite \
  --pack-dir ../data_packs/football_event_demo_v1 \
  --reports-dir ../reports

python verify_data_pack.py --pack-dir ../data_packs/football_event_demo_v1
```

```bash
cd ../rust-core

cargo test

cargo run --bin omnibet-value -- report \
  ../data_packs/football_core_v1 \
  Spain \
  "Cape Verde" \
  ../data/sample_odds_spain_cape_verde.csv \
  0.25
```

The synthetic event data is public-safe and not predictive real-world data.

## Layers

1. **C++ core** (`cpp-core/`) — std-only CLI that compiles without third-party libraries.
2. **Rust core skeleton** (`rust-core/`) — intended future memory-safe production core. Cargo is required to compile.
3. **Python lab** (`python_lab/`) — fast research/audit/backtest scripts.
4. **Browser GUI** (`web_gui/index.html`) — local, cross-platform prototype GUI. Open it in Chrome/Firefox and load `data/unified_intl_matches.csv`.
5. **Docs** (`docs/`) — reference-project map and architecture notes.

## What works now

- Load football match CSV.
- Canonicalise team aliases.
- Estimate team attack/defence from historical data.
- Generate Poisson scoreline matrix.
- Estimate 1X2, O/U 2.5, BTTS, corners, shots and yellow-card baselines.
- Convert bookmaker decimal odds into implied true probabilities using multiplicative overround removal.
- Compute value edge and Kelly / quarter-Kelly stakes.
- Run both in-sample and **walk-forward** backtests.
- Use a browser GUI without installing a GUI framework.

## Quick start: C++ core

```bash
cd cpp-core
g++ -std=c++17 -O2 -Wall -Wextra omnibet.cpp -o omnibet

# Match prediction
./omnibet predict --data ../data/unified_intl_matches.csv --home Spain --away "Cape Verde"

# Implied probabilities / overround removal
./omnibet implied --odds "2.70,2.30,4.40"

# Value / Kelly
./omnibet value --prob 0.55 --odds 2.10

# In-sample sanity check (inflated, not proof)
./omnibet backtest --data ../data/unified_intl_matches.csv

# Honest temporal test
./omnibet backtest --data ../data/unified_intl_matches.csv --walk-forward 1 --min-train 80
```

Expected smoke-test style output on the bundled dataset:

```text
mode walk_forward
matches 221
1x2_accuracy ~0.475
over25_accuracy ~0.520
log_loss ~1.071
brier_1x2 ~0.638
```

Those numbers are intentionally honest. The old in-sample number looked much better, but in-sample testing is not proof of betting edge.

## Quick start: Python research lab

```bash
cd python_lab
python audit_dataset.py --data ../data/unified_intl_matches.csv
python walk_forward_backtest.py --data ../data/unified_intl_matches.csv --min-train 80
```

## Quick start: GUI

Open:

```text
web_gui/index.html
```

Then load:

```text
data/unified_intl_matches.csv
```

## Why v1 is better than v0

v0 gave us a running architecture. v1 adds the missing betting-engine pieces:

- overround-aware implied probabilities;
- explicit expected-value calculations;
- full and quarter Kelly;
- walk-forward validation;
- documented migration path from football-only to cross-sport;
- clear separation between research Python and future Rust/C++ production core.

## Betting honesty

This is not a profit guarantee. Even a good model can lose money if it is worse than the market or if the overround is ignored. Real edge requires:

- walk-forward validation;
- bookmaker odds history;
- overround removal;
- calibration curves / Brier score / log loss;
- closing-line-value tracking;
- market-specific models for corners/cards/props;
- bankroll risk limits;
- careful treatment of injuries, lineups, travel, fatigue and tactical context.

## Next upgrade path

1. Add SQLite database with tables: `games`, `market_lines`, `team_snapshots`, `features_json`, `predictions`, `bets`, `bankroll_events`.
2. Add point-in-time feature generation to prevent data leakage.
3. Add proper Dixon-Coles optimizer with low-score correction.
4. Add bivariate Poisson/correlation model.
5. Add market odds ingestion and CLV tracking.
6. Add calibrated ML in Python lab: LightGBM/XGBoost/AutoGluon style experiments.
7. Port stable inference and value logic to Rust.
8. Build Tauri desktop app if we want web-tech UI, or Qt if we want native widget tooling.
9. Add NBA adapter using the same games/lines/features/predictions/bets schema.


## v2 additions

This version adds the first serious modelling/data infrastructure pass:

- `python_lab/feature_store.py` builds a SQLite feature store with canonical games, aliases, rolling team snapshots, JSON features, model runs, predictions, bets, and bankroll events.
- `python_lab/dixon_coles_lab.py` implements a transparent Dixon-Coles optimizer with holdout, walk-forward, and single-match prediction modes.
- `docs/sqlite_feature_store_v2.md` explains the database structure.
- `docs/dixon_coles_v2.md` explains the new model and smoke-test results.
- `docs/topic_scan_notes.md` records the extra GitHub topic scan findings.

Quick smoke test:

```bash
cd python_lab
python feature_store.py init --data ../data/unified_intl_matches.csv --db ../build/omnibet.sqlite --rolling 10
python dixon_coles_lab.py --data ../data/unified_intl_matches.csv --mode walk-forward --min-train 80 --refit-every 75 --l2 0.1
python dixon_coles_lab.py --data ../data/unified_intl_matches.csv --mode predict --home Spain --away "Cape Verde" --l2 0.1
```
