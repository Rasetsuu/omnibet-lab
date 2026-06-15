# Reference Project Map for OmniBet Lab v1

This document records the ideas mined from external open-source sports-analytics projects and how they are being translated into OmniBet Lab. We do **not** vendor or copy those projects; instead we use them as architecture/model references and implement clean-room equivalents where useful.

## 1. penaltyblog

Repository: `martineastwood/penaltyblog`

Why it matters:

- Production-oriented football analytics package.
- Provides Poisson, Dixon-Coles, Bivariate Poisson, Bayesian, and other goal models.
- Has implied-odds/overround removal helpers.
- Has team ratings: Elo, Massey, Colley, Pi.
- Uses consistent model APIs so models can be benchmarked against each other.
- Uses time weighting so recent matches matter more than old matches.

What OmniBet should borrow conceptually:

- Consistent model interface:
  - `fit(matches)`
  - `predict(fixture)`
  - `predict_many(fixtures)`
  - `save/load model state`
  - `score/backtest`
- Goal model family:
  - v1: independent Poisson baseline.
  - v2: Dixon-Coles low-score correction.
  - v3: Bivariate Poisson / correlation term.
  - v4: Bayesian/shrinkage model for sparse international teams.
- Time-decay weighting:
  - Recent games should have stronger influence.
  - Old games should still inform priors but not dominate.
- Odds module:
  - Decimal odds parsing.
  - Implied probability conversion.
  - Overround/margin removal.
  - Market model probabilities vs bookmaker probabilities.

## 2. NBA_Betting

Repository: `NBA-Betting/NBA_Betting`

Why it matters:

- Excellent architecture even if NBA-specific.
- Separates data sources, database, ETL, feature store, modelling, betting decisions, and dashboard.
- Uses point-in-time joins to avoid leakage.
- Uses rolling stats, rest days, travel, streaks, and line movement ideas.
- Treats Vegas/market line as a benchmark and optionally as a feature.
- Tracks predictions and bets separately, enabling ROI and bankroll analytics.

What OmniBet should borrow conceptually:

- Cross-sport data model:
  - `games`
  - `market_lines`
  - `team_snapshots`
  - `features_json`
  - `predictions`
  - `bets`
  - `bankroll_events`
- ETL stages:
  - ingest raw source rows
  - normalize team/player names
  - calculate point-in-time rolling features
  - join features to games without future leakage
  - persist training rows
- Dashboard sections:
  - today's games
  - model pick vs market line
  - value edge
  - Kelly stake
  - ROI / bankroll chart
  - model diagnostics

## 3. Existing user package

Strengths:

- Already has international football data.
- Already thinks in match + prop markets: goals, BTTS, corners, shots, cards.
- Already has a bet-builder/MCP style UI concept.

Problems to replace:

- Earlier model was not portable due missing proprietary modules.
- In-sample tests looked much better than honest walk-forward tests.
- Prop models need more data and calibration before being trusted.

What OmniBet keeps:

- Data schema and first football adapter.
- Bet-builder concept.
- Multiple markets per fixture.
- Cross-platform local-first workflow.

## v1 implementation status

Implemented now:

- C++ core CLI.
- CSV loader + alias normalization.
- Poisson outcome baseline.
- Goals, BTTS, corners, shots, cards estimates.
- Implied probability conversion using multiplicative overround removal.
- Edge and quarter-Kelly calculation.
- Honest walk-forward backtest mode.
- Local browser GUI.
- Python lab script for walk-forward validation.

Not implemented yet:

- Real Dixon-Coles optimization.
- Bivariate Poisson fitting.
- Full SQLite feature store.
- Odds API ingestion.
- AutoML tabular model training.
- Tauri/Qt production desktop app.
