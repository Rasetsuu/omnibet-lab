# OmniBet Lab v1 Architecture

## Core principle

Do not treat a sports prediction tool as one script. Treat it as a pipeline:

```text
raw data sources
  -> normalized game registry
  -> point-in-time feature store
  -> model training/inference
  -> market odds comparison
  -> value / staking decision
  -> bet ledger / ROI / CLV tracking
  -> GUI/dashboard
```

## Cross-sport schema

The same schema should support football, NBA, NFL, tennis, etc.

### games

```text
game_id
sport
competition
season
datetime_utc
home_team
away_team
neutral
home_score
away_score
completed
```

### market_lines

```text
game_id
bookmaker
market
selection
line
odds_decimal
timestamp_utc
is_opening
is_closing
```

### team_snapshots

```text
team
sport
date
features_json
```

### features_json

```text
game_id
model_context_date
features_json
```

### predictions

```text
game_id
model_name
market
selection
model_prob
fair_odds
predicted_at
```

### bets

```text
game_id
market
selection
odds_decimal
stake
result
profit_loss
closing_odds_decimal
clv
```

## Engine layers

### Research layer: Python

Use Python for heavy experiments:

- pandas data cleaning;
- football Poisson / Dixon-Coles / Bivariate Poisson fitting;
- LightGBM/XGBoost/AutoGluon-style model tests;
- calibration curves;
- walk-forward backtesting;
- CLV / ROI analysis.

### Production core: Rust or C++

Use Rust/C++ only after the research code stabilizes:

- CSV/SQLite/parquet loading;
- alias normalization;
- fitted model inference;
- implied probability / overround removal;
- edge and Kelly stake calculation;
- batch prediction for GUI.

### GUI layer

Two realistic options:

- **Tauri**: best if we want modern web UI and small desktop bundle. Rust backend + HTML/CSS/JS frontend.
- **Qt**: best if we want mature native widgets and C++/Python integration.

Recommendation for this project: **Tauri** long-term, because the GUI can reuse the current browser prototype and the Rust backend can own the inference engine.
