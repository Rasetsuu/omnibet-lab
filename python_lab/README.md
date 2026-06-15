# OmniBet Python Lab

This folder is for fast proof-of-concept research before we port stable pieces into Rust/C++.

## Scripts

```bash
python audit_dataset.py --data ../data/unified_intl_matches.csv
python quick_backtest.py --data ../data/unified_intl_matches.csv
python walk_forward_backtest.py --data ../data/unified_intl_matches.csv --min-train 80
```

## Purpose

- Verify data integrity.
- Prototype models quickly.
- Run honest temporal validation.
- Compare model families before porting inference into the production core.

## Important

The C++ core is faster and dependency-free for inference. Python is where we should experiment with heavier models first: Dixon-Coles optimizer, Bivariate Poisson, LightGBM/XGBoost/AutoGluon-style tabular models, calibration, and CLV/ROI analysis.

## v2: SQLite feature store + Dixon-Coles lab

Build leakage-safe SQLite feature store:

```bash
python feature_store.py init --data ../data/unified_intl_matches.csv --db ../build/omnibet.sqlite --rolling 10
python feature_store.py inspect --db ../build/omnibet.sqlite
```

Run Dixon-Coles backtests:

```bash
python dixon_coles_lab.py --data ../data/unified_intl_matches.csv --mode holdout --test-frac 0.25 --l2 0.1
python dixon_coles_lab.py --data ../data/unified_intl_matches.csv --mode walk-forward --min-train 80 --refit-every 75 --l2 0.1
```

Single-match prediction:

```bash
python dixon_coles_lab.py --data ../data/unified_intl_matches.csv --mode predict --home Spain --away "Cape Verde" --l2 0.1
```
