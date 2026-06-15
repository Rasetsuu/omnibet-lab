# v4 Commands

## Initialize warehouse

```bash
cd python_lab
python warehouse_manager.py init --db ../build/omnibet.sqlite
python warehouse_manager.py status --db ../build/omnibet.sqlite
```

## Football-Data.co.uk CSV import

```bash
python -m adapters.football_data_uk_adapter \
  --db ../build/omnibet.sqlite \
  --input ../data/unified_intl_matches.csv \
  --competition unified_international
```

You can also pass a URL.

## StatsBomb Open Data import

```bash
git clone https://github.com/statsbomb/open-data ~/data/statsbomb-open-data

python -m adapters.statsbomb_open_adapter import \
  --db ../build/omnibet.sqlite \
  --root ~/data/statsbomb-open-data/data \
  --limit-matches 50
```

## TheStatsAPI

```bash
export THESTATSAPI_KEY="your_key"

python -m adapters.thestatsapi_adapter status --db ../build/omnibet.sqlite
python -m adapters.thestatsapi_adapter sync-competitions --db ../build/omnibet.sqlite --limit-pages 1
```
