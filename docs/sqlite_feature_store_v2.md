# SQLite feature store v2

`python_lab/feature_store.py` creates a small, leakage-safe SQLite feature store.

## Tables

- `games`: canonical fixture/result spine.
- `team_aliases`: raw-name to canonical-name mapping.
- `team_snapshots`: rolling point-in-time team form before each match.
- `features_json`: one JSON feature blob per match.
- `model_runs`: model/backtest metadata and metrics.
- `predictions`: future prediction rows.
- `bets`: optional bet tracking.
- `bankroll_events`: optional bankroll ledger.

## Why this matters

The old package had direct CSV/model calls everywhere. That makes it easy to leak future information or mix incompatible data sources. A feature store makes the pipeline explicit:

```text
data sources -> canonical games -> point-in-time snapshots -> feature blobs -> models -> predictions -> bets
```

The rolling snapshots are constructed **before** adding the current match to team history, so the features avoid same-match leakage.

## Usage

```bash
cd python_lab
python feature_store.py init --data ../data/unified_intl_matches.csv --db ../build/omnibet.sqlite --rolling 10
python feature_store.py inspect --db ../build/omnibet.sqlite
```

Expected count with the bundled data:

```text
games: 301
team_snapshots: 602
features_json: 301
```
