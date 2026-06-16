# v21 Phase-Aware Football Training Foundation

v21 makes football markets phase-aware before the serious training/export pipeline grows further.

## Why this matters

A football match can have different valid settlement scopes:

- 90-minute regulation time
- first-half / second-half regulation stoppage time
- extra time first half: 90-105 and 105+
- extra time second half: 105-120 and 120+
- penalty shootout
- qualification / advance / lift-trophy markets

These labels must not be mixed. A 90-minute 1X2 market is not the same as a to-qualify market after extra time and penalties.

## New/updated files

```text
python_lab/football_phase_lab.py
python_lab/market_registry.py
python_lab/export_data_pack.py
docs/v21_phase_aware_training.md
```

## Phase features

`football_phase_lab.py` builds:

```text
gold_match_phase_features
```

with:

- regulation event count
- regulation stoppage event count
- extra-time event count
- extra-time stoppage event count
- penalty shootout event count
- max minute seen
- has extra time
- has penalties
- per-phase counts JSON
- settlement-scope availability JSON

## Built-in extra-time selftest

The CI dataset may not contain an extra-time match, so v21 includes a selftest covering:

- 45+
- 90+
- 90-105
- 105+
- 105-120
- 120+
- penalty shootout after 120

This ensures the phase classifier understands the cases even when the smoke dataset is league-only.

## Market registry changes

Football markets now declare:

```text
settlement_scope
phase_scope
```

Examples:

- `football.1x2` -> `regulation_time`
- `football.after_extra_time_winner` -> `after_extra_time`
- `football.to_qualify` -> `qualification`
- `football.penalty_shootout_winner` -> `penalty_shootout`
- `football.extra_time_total_goals` -> `extra_time_only`

## Pack changes

`gold_match_phase_features` is now included in compressed data packs.

CI exports and verifies:

```text
data_packs/football_phase_training_v1
```

with both Python and Rust.

## Honesty

This is not a trained extra-time model yet. It is the correct data/model contract so future training does not mix incompatible market labels.
