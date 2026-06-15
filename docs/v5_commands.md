# v5 Commands

## Initialize warehouse and import CSV

```bash
cd python_lab
python warehouse_manager.py init --db ../build/omnibet.sqlite
python -m adapters.football_data_uk_adapter --db ../build/omnibet.sqlite --input ../data/unified_intl_matches.csv --competition unified_international
```

## Build gold features

```bash
python gold_feature_builder.py build --db ../build/omnibet.sqlite --rolling 10
python gold_feature_builder.py inspect --db ../build/omnibet.sqlite
```

## Analyze goal timing

```bash
python goal_timing_lab.py --db ../build/omnibet.sqlite
```

## Build player scores

```bash
python player_score_lab.py --db ../build/omnibet.sqlite
```

## Full local smoke

```bash
python warehouse_manager.py init --db ../build/omnibet.sqlite
python -m adapters.football_data_uk_adapter --db ../build/omnibet.sqlite --input ../data/unified_intl_matches.csv --competition unified_international
python gold_feature_builder.py build --db ../build/omnibet.sqlite --rolling 10
python gold_feature_builder.py inspect --db ../build/omnibet.sqlite
```
